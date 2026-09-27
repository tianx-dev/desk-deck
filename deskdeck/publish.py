"""Atomic local task publishing for build scripts, timers, or personal workflows."""

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit


def publish(config, task_id, title, state, message="", open_url=None):
    if config.mode != "file":
        raise ValueError('The task command requires mode = "file"')
    if not task_id or len(task_id) > 120 or not title or len(title) > 160:
        raise ValueError("Use a short task id and title")
    if open_url and urlsplit(open_url).scheme not in ("http", "https", "codex"):
        raise ValueError("Task destinations support http, https, and codex")
    path = Path(config.data_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    # macOS/Linux lock avoids losing updates from concurrent local build scripts.
    import fcntl

    with path.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(path.read_text()) if path.exists() else {"tasks": []}
        tasks = data["tasks"]
        previous = next((t for t in tasks if t["id"] == task_id), {})
        now = time.time()
        item = dict(
            id=task_id,
            title=title,
            state=state,
            summary=message[:1200],
            updated=now,
            started=previous.get("started", now)
            if state != "active" or previous.get("state") == "active"
            else now,
            completion=uuid.uuid4().hex
            if state == "ready"
            else previous.get("completion", ""),
            quiet=state == "quiet",
            open_url=previous.get("open_url", "") if open_url is None else open_url,
        )
        tasks = [item] + [t for t in tasks if t["id"] != task_id]
        fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".tasks-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"tasks": tasks[:32]}, f, indent=2)
                f.write("\n")
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
