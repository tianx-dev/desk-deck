"""Synthetic and local task sources, an optional Codex adapter, and notifications."""

import json
import math
import re
import sqlite3
import threading
import time
from urllib.parse import quote, urlsplit
from datetime import datetime
from pathlib import Path


def timestamp(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0


def clean_text(text):
    text = str(text or "")
    if "<heartbeat>" in text:
        found = re.search(r"<message>(.*?)</message>", text, re.S)
        text = found.group(1) if found else ""
    text = re.sub(r"<oai-mem-citation>.*", "", text, flags=re.S)
    text = re.sub(r"::[a-z-]+\{[^}]*\}", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[*`#]", "", text)
    return re.sub(r"\s+", " ", text).strip()[:1200]


def observe(rows, now):
    state, updated, started, summary, completed, quiet = "unknown", 0, 0, "", "", False
    for row in rows:
        at = timestamp(row.get("timestamp"))
        updated = max(updated, at)
        p = row.get("payload", {})
        if row.get("type") != "event_msg":
            continue
        typ = p.get("type")
        if typ == "task_started":
            state, started, summary, quiet = "active", at, "", False
        elif typ == "task_complete":
            state = "ready"
            raw = p.get("last_agent_message") or ""
            quiet = "<heartbeat>" in raw and "<decision>NOTIFY</decision>" not in raw
            summary = clean_text(raw) or summary
            completed = str(p.get("turn_id") or row.get("timestamp"))
        elif typ in ("turn_aborted", "task_aborted"):
            state, summary = "stopped", "The turn was interrupted."
        elif typ == "item_completed":
            item = p.get("item", {})
            if item.get("type") == "AgentMessage" and item.get("phase") in (
                "commentary",
                "final_answer",
                "final",
                None,
            ):
                text = " ".join(
                    part.get("text", "")
                    for part in item.get("content", [])
                    if isinstance(part, dict) and part.get("type") == "Text"
                )
                if text:
                    summary = clean_text(text)
    if state == "active" and now - updated > 180:
        state = "quiet"
    if quiet and state == "ready":
        state = "quiet"
    return dict(
        state=state,
        updated=updated,
        started=started,
        summary=summary,
        completion=completed,
        quiet=quiet,
    )


class DemoProvider:
    """Fictional, deterministic activity. One reply completes after 20 seconds."""

    mode = "demo"

    def __init__(self):
        self.started = time.time()

    def tasks(self):
        now = time.time()
        done = now - self.started >= 20
        return [
            dict(
                id="demo-reading",
                title="Build a reading app",
                state="ready" if done else "active",
                updated=self.started + 20 if done else now,
                started=self.started,
                summary="The reading list is ready to review. This is synthetic demo data."
                if done
                else "Checking the mobile layout and keyboard navigation. This is synthetic demo data.",
                completion="demo-reply-1" if done else "",
                quiet=False,
                open_url="https://example.org/reading",
            ),
            dict(
                id="demo-photos",
                title="Review the photo organizer",
                state="ready",
                updated=self.started - 120,
                started=self.started - 600,
                summary="Three layout options are ready. Open the project to compare them. Synthetic demo data.",
                completion="older-reply",
                quiet=False,
                open_url="https://example.org/photos",
            ),
            dict(
                id="demo-weekend",
                title="Plan a weekend project",
                state="quiet",
                updated=self.started - 1800,
                started=0,
                summary="No new update. Synthetic demo data.",
                completion="",
                quiet=True,
                open_url="",
            ),
        ]


class FileProvider:
    """Generic task snapshots published by local scripts. No agent dependency."""

    mode = "file"

    def __init__(self, config):
        self.path = Path(config.data_file)

    def tasks(self):
        if not self.path.exists():
            return []
        if self.path.stat().st_size > 1_000_000:
            raise ValueError("Task feed exceeds 1 MB")
        data = json.loads(self.path.read_text())
        if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
            raise ValueError("Expected a tasks array")
        result, seen = [], set()
        for task in data["tasks"][:32]:
            if (
                not isinstance(task, dict)
                or not isinstance(task.get("id"), str)
                or task["id"] in seen
            ):
                raise ValueError("Each task needs a unique string id")
            seen.add(task["id"])
            state = task.get("state", "unknown")
            if state not in ("active", "ready", "quiet", "stopped", "unknown"):
                raise ValueError("Unknown task state")
            updated = float(task.get("updated", 0))
            if not math.isfinite(updated):
                raise ValueError("Invalid task timestamp")
            if state == "active" and time.time() - updated > 180:
                state = "quiet"
            url = str(task.get("open_url", ""))
            if url and urlsplit(url).scheme not in ("https", "http", "codex"):
                raise ValueError("Unsupported task destination")
            result.append(
                dict(
                    id=task["id"][:120],
                    title=str(task.get("title", "Untitled task"))[:160],
                    summary=clean_text(task.get("summary", "")),
                    state=state,
                    updated=updated,
                    started=float(task.get("started", 0)),
                    completion=str(task.get("completion", "")),
                    quiet=bool(task.get("quiet", False)),
                    open_url=url,
                )
            )
        return sorted(result, key=lambda t: t["updated"], reverse=True)


class CodexProvider:
    """Opt-in adapter for local, version-sensitive Codex records. Never writes them."""

    mode = "codex"

    def __init__(self, config):
        self.config = config
        self.home = Path(config.codex_home).expanduser().resolve()
        self.cache = {}

    def tasks(self):
        if not self.config.task_ids:
            return []
        db = self.home / self.config.codex_db
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=1)
        con.row_factory = sqlite3.Row
        try:
            placeholders = ",".join("?" for _ in self.config.task_ids)
            records = con.execute(
                f"""SELECT id, name, rollout_path FROM threads
                WHERE archived=0 AND id IN ({placeholders}) ORDER BY updated_at DESC""",
                self.config.task_ids,
            ).fetchall()
        finally:
            con.close()
        now, tasks = time.time(), []
        for record in records:
            path = Path(record["rollout_path"]).expanduser().resolve()
            # Even corrupt database paths must not turn into arbitrary file reads.
            if (
                not any(
                    path.is_relative_to(self.home / d)
                    for d in ("sessions", "archived_sessions")
                )
                or not path.is_file()
            ):
                continue
            stat = path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
            cached = self.cache.get(record["id"])
            if not cached or cached[0] != signature:
                with path.open("rb") as f:
                    f.seek(max(0, stat.st_size - 2_000_000))
                    lines = f.read().splitlines()
                rows = []
                for line in lines:
                    try:
                        value = json.loads(line)
                        if isinstance(value, dict) and isinstance(
                            value.get("payload"), dict
                        ):
                            rows.append(value)
                    except (ValueError, UnicodeDecodeError):
                        pass
                result = observe(rows, now)
                self.cache[record["id"]] = (signature, result)
            else:
                result = dict(cached[1])
            result = dict(result)
            if result["state"] == "active" and now - result["updated"] > 180:
                result["state"] = "quiet"
            result.update(
                id=record["id"],
                title=record["name"] or "Untitled task",
                open_url="codex://threads/" + quote(record["id"], safe=""),
            )
            if not self.config.expose_summaries:
                result["summary"] = (
                    "Message text is hidden. Open the task on your Mac for details."
                )
            tasks.append(result)
        return tasks


class Feed:
    def __init__(self, provider):
        self.provider = provider
        self.lock = threading.RLock()
        self.previous, self.notifications = {}, []
        self.initialized = False

    def read(self):
        with self.lock:
            try:
                tasks = self.provider.tasks()
                for task in tasks:
                    completion = task["completion"]
                    previous = self.previous.get(task["id"])
                    if (
                        self.initialized
                        and previous is not None
                        and completion
                        and completion != previous
                        and task["state"] == "ready"
                        and not task["quiet"]
                    ):
                        self.notifications.insert(
                            0,
                            dict(
                                id=task["id"] + ":" + completion,
                                task=task["id"],
                                title=task["title"],
                                message=task["summary"],
                                at=task["updated"],
                                read=False,
                            ),
                        )
                    self.previous[task["id"]] = completion
                self.notifications = self.notifications[:30]
                self.initialized = True
                return dict(
                    ok=True,
                    checked=time.time(),
                    tasks=tasks,
                    notifications=[dict(n) for n in self.notifications],
                )
            except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
                return dict(
                    ok=False,
                    checked=0,
                    tasks=[],
                    notifications=[],
                    error="Task source unavailable or incompatible. Check local configuration.",
                )

    def acknowledge(self, notice_id):
        with self.lock:
            for item in self.notifications:
                if item["id"] == notice_id or notice_id == "all":
                    item["read"] = True
