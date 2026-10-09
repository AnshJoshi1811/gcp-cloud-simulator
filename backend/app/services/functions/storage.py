"""In-memory storage + deploy/invoke lifecycle for Cloud Functions."""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import logging
import threading

from .models import CloudFunction, FunctionState, SUPPORTED_RUNTIMES
from . import executor

logger = logging.getLogger(__name__)


class FunctionsStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.functions: Dict[str, Dict[str, CloudFunction]] = {}  # project_id -> name -> CloudFunction

    def deploy_function(
        self, project_id: str, location: str, name: str, entry_point: str,
        source_code: str, runtime: str = "python312",
        environment_variables: Optional[Dict[str, str]] = None,
    ) -> CloudFunction:
        if runtime not in SUPPORTED_RUNTIMES:
            raise ValueError(f"Unsupported runtime '{runtime}'. Supported: {', '.join(SUPPORTED_RUNTIMES)}")

        with self._lock:
            project_functions = self.functions.setdefault(project_id, {})
            existing = project_functions.get(name)
            if existing:
                executor.delete(existing.container_id)

            fn = CloudFunction(
                project_id=project_id, location=location, name=name,
                entry_point=entry_point, source_code=source_code, runtime=runtime,
                environment_variables=environment_variables or {},
            )
            project_functions[name] = fn

        container_id, host_port, error = executor.deploy(
            f"{project_id}-{name}", source_code, entry_point, fn.environment_variables
        )
        fn.container_id = container_id
        fn.host_port = host_port
        if error:
            fn.state = FunctionState.FAILED
            fn.last_error = error
        else:
            fn.state = FunctionState.ACTIVE
        return fn

    def get_function(self, project_id: str, name: str) -> Optional[CloudFunction]:
        return self.functions.get(project_id, {}).get(name)

    def list_functions(self, project_id: str) -> List[CloudFunction]:
        return list(self.functions.get(project_id, {}).values())

    def delete_function(self, project_id: str, name: str) -> bool:
        fn = self.get_function(project_id, name)
        if not fn:
            return False
        executor.delete(fn.container_id)
        with self._lock:
            del self.functions[project_id][name]
        return True

    def invoke_function(
        self, project_id: str, location: str, name: str, body: Optional[Dict[str, Any]]
    ) -> Tuple[Any, int, Optional[str]]:
        fn = self.get_function(project_id, name)
        if not fn:
            return None, 404, f"Function '{name}' not found"
        if fn.state != FunctionState.ACTIVE and not fn.host_port:
            # Still allow in-process fallback execution even if container failed,
            # since the stub-mode philosophy is "stay functionally alive".
            pass
        result, status, error = executor.invoke(fn, body)
        fn.invocation_count += 1
        fn.update_time = datetime.now(timezone.utc)
        if error:
            fn.last_error = error
        return result, status, error

    def get_stats(self) -> Dict[str, int]:
        return {"functions": sum(len(f) for f in self.functions.values())}


storage = FunctionsStorage()
