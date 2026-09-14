#!/usr/bin/env python3
"""llama-swap WebUI companion server (stdlib only, no dependencies).

Problem: browsers block cross-origin fetches to llama-swap's NATIVE endpoints
(/health, /running, /profiles, /metrics, /logs, ...) because they send no
`Access-Control-Allow-Origin` header. Opening index.html as file:// (or from any
other origin) therefore breaks the System tab, while proxied /v1/* calls work.

Fix: serve this directory AND proxy API paths to llama-swap from the SAME
origin, so CORS is never involved.

Usage:
    python serve.py --upstream http://192.168.1.22:8080 --port 8000
Then open http://localhost:8000 and set the UI's API Base URL to
http://localhost:8000
"""
import argparse
import http.client
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Anything starting with one of these goes to llama-swap; the rest is static.
PROXY_PREFIXES = (
    "/v1/", "/infill", "/running", "/health", "/metrics", "/logs",
    "/api/", "/sdapi/", "/comfyui/", "/audioapi/", "/profiles",
)

HOP_HEADERS = {
    "host", "content-length", "connection", "transfer-encoding",
    "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "upgrade",
}


class Handler(SimpleHTTPRequestHandler):
    upstream = "http://127.0.0.1:8080"
    # HTTP/1.1 so proxied SSE/chunked bodies can stream progressively on a
    # persistent socket. Close-delimited (Connection: close) responses still
    # stream chunk-by-chunk because we flush after every write below.
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _is_proxy_path(self):
        return self.path.split("?", 1)[0] in ("/v1/models",) or \
            any(self.path == p or self.path.startswith(p) for p in PROXY_PREFIXES)

    def _proxy(self):
        upstream_path = self.path
        url = self.upstream.rstrip("/") + upstream_path
        data = None
        if self.command in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            data = self.rfile.read(n) if n else None
        req = urllib.request.Request(url, data=data, method=self.command)
        for k, v in self.headers.items():
            if k.lower() in HOP_HEADERS:
                continue
            try:
                req.add_header(k, v)
            except ValueError:
                pass
        # /logs/stream/* stays open forever by design — never time it out.
        # Everything else gets a generous cap for long generations.
        path_only = upstream_path.split("?", 1)[0]
        timeout = None if path_only.startswith("/logs/stream") else 600
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            status, headers, body = resp.status, resp.headers, resp
        except urllib.error.HTTPError as e:
            status, headers, body = e.code, e.headers, e
        except (urllib.error.URLError, http.client.HTTPException, OSError):
            return  # upstream unreachable / died — nothing to forward
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return
        self.send_response(status)
        ctype = headers.get("Content-Type")
        if ctype:
            self.send_header("Content-Type", ctype)
        length = headers.get("Content-Length")
        # Stream SSE / log tails / chunked bodies instead of buffering them.
        # NOTE: urllib de-chunks upstream bodies, so Transfer-Encoding may be
        # absent here — unknown length alone still means "stream it".
        is_sse = "text/event-stream" in (ctype or "")
        streamed = (
            self.command == "HEAD"
            or is_sse
            or headers.get("Transfer-Encoding", "").lower() == "chunked"
            or length is None
        )
        if not streamed and length:
            self.send_header("Content-Length", length)
        else:
            # No Content-Length => close-delimited framing. Tell HTTP/1.1
            # clients explicitly and drop keep-alive for this response.
            self.send_header("Connection", "close")
            self.close_connection = True
            if is_sse:
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        # Push headers immediately so the browser can start streaming.
        try:
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        if self.command != "HEAD" and body is not None:
            try:
                # Chunked read + flush per chunk: self.wfile is buffered, so
                # a single copyfileobj() without flush would hold SSE deltas
                # back until the upstream closes (the "all at once" bug).
                # Infinite tails (/logs/stream) would then never render.
                # Use read1(), NOT read(n): read(n) blocks until n bytes or
                # EOF, which also waits for upstream close on both
                # close-delimited and chunked bodies; read1() returns whatever
                # is available right away (and still de-chunks).
                read1 = getattr(body, "read1", None)
                while True:
                    try:
                        chunk = read1(16384) if read1 else body.read(16384)
                    except (http.client.HTTPException, OSError, ValueError):
                        break  # upstream died mid-stream — end ours cleanly
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        break
            finally:
                try:
                    body.close()
                except Exception:
                    pass

    def do_GET(self):
        if self._is_proxy_path():
            self._proxy()
        else:
            super().do_GET()

    def do_HEAD(self):
        if self._is_proxy_path():
            self._proxy()
        else:
            super().do_HEAD()

    def do_POST(self):
        self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_PATCH(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, fmt, *args):
        if self.path == "/health":
            return  # keep the console quiet
        super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description="Serve llama-swap WebUI + same-origin API proxy")
    ap.add_argument("--upstream", default="http://192.168.1.22:8080",
                    help="llama-swap base URL (default: %(default)s)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    Handler.upstream = args.upstream.rstrip("/")
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"WebUI  -> http://localhost:{args.port}")
    print(f"Proxy  -> {Handler.upstream}  ({', '.join(PROXY_PREFIXES)})")
    print("Open the WebUI address above; if a yellow CORS banner appears,")
    print('click "Switch API to this origin" (it verifies the proxy first).')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
