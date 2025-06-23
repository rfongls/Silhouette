"""Placeholder web/local interface server."""

from http.server import BaseHTTPRequestHandler, HTTPServer


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run a minimal HTTP server that echoes requests."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Silhouette interface placeholder")

    HTTPServer((host, port), Handler).serve_forever()
