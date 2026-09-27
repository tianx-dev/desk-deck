"""One foreground process owns the local server and Cast sender for the Mac app."""

import threading

from .casting import cast
from .server import make_server


def desktop(config):
    with make_server(config) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print("Local server ready. Connecting to your Nest Hub…", flush=True)
        try:
            cast(config)
        finally:
            server.shutdown()
            thread.join(timeout=3)
