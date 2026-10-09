"""MiniCloud server: moto's AWS mock on :4566 + the Docker reconciler."""

import logging
import os
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("minicloud.server")

DEFAULT_PORT = 4566


def run(port: int = DEFAULT_PORT, foreground: bool = True):
    from moto.server import ThreadedMotoServer
    from . import state_db
    from .reconciler import reconciler
    from . import docker_manager

    state_db.init_db()

    if docker_manager.DOCKER_AVAILABLE:
        logger.info("Docker is available — EC2 instances will be real containers.")
    else:
        logger.warning(
            "Docker is NOT available — running in stub mode. The AWS API and "
            "Terraform apply/destroy cycle still work, but no real containers "
            "are created. See minicloud/DECISIONS.md."
        )

    server = ThreadedMotoServer(ip_address="0.0.0.0", port=port, verbose=False)
    server.start()
    logger.info(f"MiniCloud (moto-backed AWS API) listening on http://localhost:{port}")

    reconciler.start()

    if not foreground:
        return server

    def _shutdown(signum, frame):
        logger.info("Shutting down MiniCloud...")
        reconciler.stop()
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    try:
        signal.signal(signal.SIGTERM, _shutdown)
    except (AttributeError, ValueError):
        pass  # SIGTERM not available on this platform/thread

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown(None, None)


if __name__ == "__main__":
    port = int(os.environ.get("MINICLOUD_PORT", DEFAULT_PORT))
    run(port=port)
