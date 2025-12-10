"""Lightweight HTTP sidecar for liveness checks."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time
from typing import Callable


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/health", "/health/"):
            self.send_response(404)
            self.end_headers()
            return

        now = time.time()
        last = getattr(self.server, "last_beat", 0.0)
        stale_after = getattr(self.server, "stale_after", 15.0)

        if now - last < stale_after:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"STALE")

    # Silence default logging
    def log_message(self, format, *args):
        return


def start_sidecar(port: int = 8080, stale_after: float = 10.0) -> Callable[[], None]:
    """
    Start the sidecar server.

    Returns
    -------
    Callable[[], None]
        beat() function to update liveness timestamp from the main logic.
    """
    server = HTTPServer(("localhost", port), _HealthHandler)
    server.last_beat = time.time()
    server.stale_after = stale_after

    def beat():
        server.last_beat = time.time()

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return beat
