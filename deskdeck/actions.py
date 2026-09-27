import platform
import subprocess
import threading
import time


class Actions:
    def __init__(self, config, feed):
        self.config, self.feed = config, feed
        self.lock, self.last_open = threading.Lock(), 0

    def run(self, kind, target):
        if not isinstance(target, str):
            raise ValueError("An action needs a named target")
        if kind == "open_app":
            item = next((x for x in self.config.launchers if x["id"] == target), None)
            if not item:
                raise ValueError("Unknown launcher")
            args = (
                ["/usr/bin/open", "-a", item["target"]]
                if item["kind"] == "app"
                else ["/usr/bin/open", item["target"]]
            )
        elif kind == "open_task":
            task = next(
                (t for t in self.feed.read().get("tasks", []) if t["id"] == target),
                None,
            )
            if not task:
                raise ValueError("Task is not in the selected feed")
            if not task.get("open_url"):
                raise ValueError("No destination is configured for this task")
            args = ["/usr/bin/open", task["open_url"]]
        else:
            raise ValueError("Unsupported action")
        if self.config.mode == "demo" or not self.config.enable_actions:
            return {
                "ok": True,
                "simulated": True,
                "message": "Preview: no application was opened",
            }
        if platform.system() != "Darwin":
            raise ValueError(
                "Mac actions require macOS; the browser demo works elsewhere"
            )
        with self.lock:
            if time.monotonic() - self.last_open < 0.65:
                raise ValueError("Please wait a moment before opening again")
            self.last_open = time.monotonic()
        result = subprocess.run(args, capture_output=True, timeout=5, check=False)
        if result.returncode:
            raise ValueError(
                "macOS could not open the target; check the configured application name"
            )
        return {"ok": True, "simulated": False}
