"""
Executes a deployed Cloud Function.

Two execution paths, mirroring docker_manager.py's existing stub-mode
philosophy of staying functionally alive even without Docker:

- Docker available: build a small on-the-fly image (python:3.12-slim + the
  user's source + a stdlib-only HTTP shim) and run it as a real container,
  reachable at a published host port. Each deploy builds once; invokes reuse
  the running container (warm, like a real Cloud Functions/Cloud Run
  instance) until the function is deleted or redeployed.
- Docker unavailable: exec the user's source in a fresh namespace in-process
  and call the entry point directly with a minimal Flask-like request object
  (`.get_json()`, `.args`). Less isolated than a real deployment, but keeps
  the emulator's HTTP trigger behaviorally correct without Docker.
"""

from typing import Any, Dict, Optional, Tuple
import io
import json
import logging
import tarfile
import textwrap
import time

from app.core import docker_manager as dm

logger = logging.getLogger(__name__)

SHIM_SOURCE = textwrap.dedent(
    """
    import json
    import sys
    from http.server import BaseHTTPRequestHandler, HTTPServer

    import main as user_module

    class FakeRequest:
        def __init__(self, body, args):
            self._body = body
            self.args = args

        def get_json(self, silent=True):
            try:
                return json.loads(self._body or b"{}")
            except Exception:
                return None

    class Handler(BaseHTTPRequestHandler):
        def _handle(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            req = FakeRequest(body, {})
            try:
                fn = getattr(user_module, sys.argv[1])
                result = fn(req)
                if isinstance(result, tuple):
                    payload, status = result
                else:
                    payload, status = result, 200
                if not isinstance(payload, (bytes, str)):
                    payload = json.dumps(payload)
                if isinstance(payload, str):
                    payload = payload.encode()
                self.send_response(status)
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        def do_GET(self):
            self._handle()

        def do_POST(self):
            self._handle()

        def log_message(self, format, *args):
            pass

    if __name__ == "__main__":
        HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
    """
)


def _build_and_run_container(function_name: str, source_code: str, entry_point: str, env: Dict[str, str]) -> Dict[str, Any]:
    if not dm._docker_available:
        return {"container_id": None, "host_port": None}

    tag = f"gcp-fn-{function_name}:latest"
    dockerfile = textwrap.dedent(
        f"""
        FROM python:3.12-slim
        WORKDIR /app
        COPY main.py /app/main.py
        COPY shim.py /app/shim.py
        ENTRYPOINT ["python", "shim.py", "{entry_point}"]
        """
    )

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for name, content in (
            ("Dockerfile", dockerfile),
            ("main.py", source_code),
            ("shim.py", SHIM_SOURCE),
        ):
            data = content.encode()
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    tar_buffer.seek(0)

    dm.client.images.build(fileobj=tar_buffer, custom_context=True, tag=tag, rm=True)

    container_name = f"gcp-fn-{function_name}"
    try:
        old = dm.client.containers.get(container_name)
        old.remove(force=True)
    except Exception:
        pass

    host_port = dm._find_free_run_port()
    container = dm.client.containers.run(
        tag,
        name=container_name,
        detach=True,
        environment=env,
        ports={"8080/tcp": host_port},
        labels={"gcs-stimulator": "true", "service": "cloud-functions", "function": function_name},
    )
    return {"container_id": container.id, "host_port": host_port}


def deploy(function_name: str, source_code: str, entry_point: str, env: Dict[str, str]) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Returns (container_id, host_port, error)."""
    try:
        result = _build_and_run_container(function_name, source_code, entry_point, env)
        return result["container_id"], result["host_port"], None
    except Exception as e:
        logger.error(f"Failed to deploy function {function_name}: {e}")
        return None, None, str(e)


def delete(container_id: Optional[str]):
    if container_id:
        dm.delete_data_service_container(container_id)


class _FakeRequest:
    """Minimal Flask-like request object for the in-process execution fallback."""

    def __init__(self, body: Optional[Dict[str, Any]]):
        self._body = body
        self.args: Dict[str, Any] = {}

    def get_json(self, silent: bool = True):
        return self._body


def invoke(
    function, body: Optional[Dict[str, Any]] = None
) -> Tuple[Any, int, Optional[str]]:
    """Invokes a deployed function. Returns (response_body, status_code, error)."""
    if function.host_port:
        import requests

        try:
            resp = requests.post(
                f"http://localhost:{function.host_port}/",
                json=body or {},
                timeout=10,
            )
            try:
                return resp.json(), resp.status_code, None
            except ValueError:
                return resp.text, resp.status_code, None
        except Exception as e:
            return None, 500, str(e)

    # In-process fallback (no Docker / build failed)
    namespace: Dict[str, Any] = {}
    try:
        exec(compile(function.source_code, function.name, "exec"), namespace)
        fn = namespace.get(function.entry_point)
        if not fn:
            return None, 500, f"entry point '{function.entry_point}' not found in source"
        result = fn(_FakeRequest(body or {}))
        if isinstance(result, tuple):
            payload, status = result
        else:
            payload, status = result, 200
        return payload, status, None
    except Exception as e:
        return None, 500, str(e)
