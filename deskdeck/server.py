import hmac
import json
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from socketserver import TCPServer
from urllib.parse import urlsplit

from .actions import Actions
from .providers import CodexProvider, DemoProvider, FileProvider, Feed


class LocalHTTPServer(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer performs reverse DNS here; LAN resolvers can stall startup.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def make_server(config, bind_port=None):
    provider = (
        DemoProvider()
        if config.mode == "demo"
        else CodexProvider(config)
        if config.mode == "codex"
        else FileProvider(config)
    )
    feed = Feed(provider)
    feed.read()  # Establish the baseline before the display makes its first request.
    actions = Actions(config, feed)
    receipts = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log pairing links, headers, task messages, or request bodies.

        def reply(self, status, value, content_type="application/json"):
            body = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            if (
                self.path == "/api/pair-check"
                and self.headers.get("Origin") in config.peer_origins
            ):
                self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET")
                self.send_header("Access-Control-Allow-Headers", "Authorization")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' "
                + " ".join(sorted(config.peer_origins))
                + "; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def trusted_client(self):
            return (
                self.client_address[0] in config.allowed_clients
                and "http://" + self.headers.get("Host", "") in config.origins
            )

        def authenticated(self):
            if (
                not self.trusted_client()
                or self.headers.get("Sec-Fetch-Site") == "cross-site"
            ):
                return False
            supplied_origin = self.headers.get("Origin")
            if supplied_origin is not None and supplied_origin not in config.origins:
                return False
            if not config.pairing_key:
                return config.mode == "demo" and not config.enable_actions
            supplied = self.headers.get("Authorization", "")
            return hmac.compare_digest(
                supplied.encode(), ("Bearer " + config.pairing_key).encode()
            )

        def do_OPTIONS(self):
            if (
                self.path != "/api/pair-check"
                or not self.trusted_client()
                or self.headers.get("Origin") not in config.peer_origins
                or self.headers.get("Access-Control-Request-Method") != "GET"
                or self.headers.get("Access-Control-Request-Headers", "").lower()
                != "authorization"
            ):
                return self.reply(403, {"error": "Peer check not allowed"})
            self.reply(204, b"")

        def do_GET(self):
            if not self.trusted_client():
                return self.reply(403, {"error": "Unpaired client or invalid host"})
            path = urlsplit(self.path).path
            if path == "/api/pair-check":
                # Cross-origin access is limited to an authenticated identity check.
                if (
                    self.headers.get("Origin") not in config.peer_origins
                    or not config.pairing_key
                    or not hmac.compare_digest(
                        self.headers.get("Authorization", "").encode(),
                        ("Bearer " + config.pairing_key).encode(),
                    )
                ):
                    return self.reply(403, {"error": "Machine pairing check failed"})
                return self.reply(
                    200, {"ok": True, "machine_name": config.machine_name}
                )
            if path in ("/", "/index.html"):
                return self.reply(
                    200,
                    files("deskdeck").joinpath("web/index.html").read_bytes(),
                    "text/html; charset=utf-8",
                )
            assets = {
                "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/static/style.css": ("style.css", "text/css; charset=utf-8"),
            }
            if path in assets:
                name, kind = assets[path]
                return self.reply(
                    200, files("deskdeck").joinpath("web", name).read_bytes(), kind
                )
            if not self.authenticated():
                return self.reply(
                    401,
                    {"error": "Pair this screen using the private link from your Mac"},
                )
            if path == "/api/state":
                state = feed.read()
                state.update(
                    machine={"name": config.machine_name, "url": config.public_url},
                    machines=[
                        {k: m[k] for k in ("id", "name", "url")}
                        for m in config.machines
                    ],
                    mode=config.mode,
                    actions_enabled=config.enable_actions and config.mode != "demo",
                    launchers=[
                        {k: item[k] for k in ("id", "label", "subtitle", "icon")}
                        for item in config.launchers
                    ],
                    coverage="Fictional demo tasks"
                    if config.mode == "demo"
                    else "Selected Codex tasks"
                    if config.mode == "codex"
                    else "Your connected tasks",
                    version="public-1",
                )
                return self.reply(200, state)
            if path == "/api/health":
                return self.reply(
                    200,
                    {
                        "ok": True,
                        "mode": config.mode,
                        "display_receipts": dict(receipts),
                    },
                )
            self.reply(404, {"error": "Not found"})

        def do_POST(self):
            if (
                not self.authenticated()
                or self.headers.get("Origin") not in config.origins
            ):
                return self.reply(403, {"error": "Pairing or origin check failed"})
            if self.path != "/api/action":
                return self.reply(404, {"error": "Not found"})
            if self.headers.get_content_type() != "application/json":
                return self.reply(415, {"error": "Expected JSON"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict) or not isinstance(
                    data.get("action"), str
                ):
                    raise ValueError("Invalid action")
                action, target = data["action"], data.get("target")
                if action == "select_machine":
                    machine = next(
                        (m for m in config.machines if m["id"] == target), None
                    )
                    if machine is None:
                        raise ValueError("Unknown machine")
                    return self.reply(
                        200,
                        {
                            "ok": True,
                            "url": machine["url"].rstrip("/"),
                            "pairing_key": machine["pairing_key"],
                        },
                    )
                if action in ("open_app", "open_task"):
                    return self.reply(200, actions.run(action, target))
                if action == "acknowledge":
                    if not isinstance(target, str):
                        raise ValueError("Invalid notification id")
                    feed.acknowledge(target)
                elif action == "heartbeat":
                    extra = data.get("extra", {})
                    if not isinstance(extra, dict):
                        raise ValueError("Invalid display receipt")
                    receipts[self.client_address[0]] = {
                        "at": time.time(),
                        "width": extra.get("width"),
                        "height": extra.get("height"),
                        "touch": extra.get("touch"),
                        "version": extra.get("version"),
                    }
                elif action not in ("touch", "focus", "ping"):
                    raise ValueError("Unknown action")
                self.reply(200, {"ok": True, "version": "public-1"})
            except (ValueError, TypeError, subprocess.TimeoutExpired) as e:
                self.reply(400, {"error": str(e)})

    server = LocalHTTPServer(
        (config.host, config.port if bind_port is None else bind_port), Handler
    )
    server.daemon_threads = True
    server.feed = feed
    return server


def serve(config):
    with make_server(config) as server:
        print(
            f"Desk Deck: {config.public_url} ({config.mode}; actions {'enabled' if config.enable_actions and config.mode != 'demo' else 'simulated'})",
            flush=True,
        )
        if config.pairing_key:
            print(
                "Use the pair-url command locally to obtain the private pairing link.",
                flush=True,
            )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
