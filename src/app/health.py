"""Utilities for exposing lightweight health endpoints.

This module provides a minimal HTTP server that responds to Cloud Run's
health checks when the bot operates in long-polling mode. Cloud Run expects
the container to accept connections on ``PORT`` even if the application does
not expose an HTTP interface by default. The health server keeps the port
open, reports readiness, and can be shut down gracefully once polling stops.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

logger = logging.getLogger(__name__)

_SUCCESS_PATHS: tuple[str, ...] = ("/healthz", "/_ah/health", "/")


class _HealthRequestHandler(BaseHTTPRequestHandler):
    server_version = "TransmiBotHealthServer/1.0"

    def do_GET(self) -> None:  # noqa: N802 - API requires camelCase
        if self.path in _SUCCESS_PATHS:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"not found")

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D401
        """Route BaseHTTPRequestHandler logs through the standard logger."""

        logger.debug("Health probe: %s", fmt % args)


class HealthServer:
    """Threaded HTTP server reporting container readiness."""

    def __init__(self, host: str, port: int) -> None:
        self._server = ThreadingHTTPServer((host, port), _HealthRequestHandler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._shutdown_event = Event()

    def start(self) -> None:
        logger.info(
            "Starting health server",
            extra={"host": self._server.server_address[0], "port": self._server.server_address[1]},
        )
        self._thread.start()

    def stop(self) -> None:
        if self._shutdown_event.is_set():
            return

        self._shutdown_event.set()
        logger.info("Stopping health server")
        with suppress(Exception):
            self._server.shutdown()
        with suppress(Exception):
            self._server.server_close()
        self._thread.join(timeout=5)


def start_health_server(host: str, port: int) -> HealthServer:
    """Instantiate and run a threaded health server."""

    health_server = HealthServer(host, port)
    health_server.start()
    return health_server


