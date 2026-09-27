import http.client
import json
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from deskdeck.actions import Actions
from deskdeck.config import Config, load_config, write_local_config
from deskdeck.providers import DemoProvider, Feed, FileProvider, observe
from deskdeck.publish import publish
from deskdeck.server import make_server


def event(kind, at, **kwargs):
    return {
        "timestamp": datetime.fromtimestamp(at, timezone.utc).isoformat(),
        "type": "event_msg",
        "payload": {"type": kind, **kwargs},
    }


class CoreTests(unittest.TestCase):
    def test_server_start_does_not_depend_on_reverse_dns(self):
        with patch(
            "socket.getfqdn", side_effect=AssertionError("Unexpected DNS lookup")
        ):
            with make_server(Config(), bind_port=0) as server:
                self.assertGreater(server.server_port, 0)

    def test_invalid_source_reports_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tasks.json"
            path.write_text('{"tasks": [')
            state = Feed(FileProvider(Config(data_file=str(path)))).read()
            self.assertFalse(state["ok"])
            self.assertEqual(state["tasks"], [])

    def test_stale_active_is_quiet(self):
        rows = [event("task_started", 100)]
        self.assertEqual(observe(rows, 110)["state"], "active")
        self.assertEqual(observe(rows, 500)["state"], "quiet")

    def test_ready_is_not_project_success(self):
        row = event(
            "task_complete", 100, last_agent_message="More work remains", turn_id="one"
        )
        self.assertEqual(observe([row], 110)["summary"], "More work remains")
        self.assertEqual(observe([row], 110)["state"], "ready")

    def test_null_completion(self):
        self.assertEqual(
            observe([event("task_complete", 100, last_agent_message=None)], 110)[
                "state"
            ],
            "ready",
        )

    def test_hidden_content_is_not_published(self):
        rows = [
            event(
                "item_completed",
                100,
                item={"type": "Reasoning", "raw_content": "hidden text"},
            ),
            event(
                "item_completed",
                101,
                item={"type": "CommandExecution", "stdout": "private output"},
            ),
            event(
                "item_completed",
                102,
                item={
                    "type": "AgentMessage",
                    "phase": "commentary",
                    "content": [{"type": "Text", "text": "Visible update"}],
                },
            ),
        ]
        self.assertEqual(observe(rows, 110)["summary"], "Visible update")

    def test_quiet_heartbeat(self):
        row = event(
            "task_complete",
            100,
            last_agent_message="<heartbeat><decision>QUIET</decision></heartbeat>",
        )
        self.assertEqual(observe([row], 110)["state"], "quiet")

    def test_private_configuration(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "config.local.toml"
            write_local_config(path, enable_actions=True)
            cfg = load_config(path)
            self.assertEqual(cfg.mode, "file")
            self.assertTrue(cfg.enable_actions)
            self.assertGreaterEqual(len(cfg.pairing_key), 32)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                write_local_config(path)

    def test_lan_requires_pairing(self):
        with self.assertRaises(ValueError):
            Config(host="0.0.0.0").validate()

    def test_generic_progress_and_notifications(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Config(mode="file", data_file=str(Path(td) / "tasks.json"))
            feed = Feed(FileProvider(cfg))
            self.assertEqual(feed.read()["tasks"], [])
            publish(
                cfg,
                "build",
                "Example build",
                "active",
                "Running",
                "https://example.org/project",
            )
            self.assertEqual(feed.read()["tasks"][0]["state"], "active")
            publish(cfg, "build", "Example build", "ready", "Finished")
            state = feed.read()
            self.assertEqual(len(state["notifications"]), 1)
            self.assertEqual(
                state["tasks"][0]["open_url"], "https://example.org/project"
            )
            self.assertEqual(len(feed.read()["notifications"]), 1)
            feed.acknowledge("all")
            self.assertTrue(feed.read()["notifications"][0]["read"])
            self.assertEqual(Feed(FileProvider(cfg)).read()["notifications"], [])

    def test_bad_task_destination(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Config(mode="file", data_file=str(Path(td) / "tasks.json"))
            with self.assertRaises(ValueError):
                publish(cfg, "x", "Task", "active", open_url="file:///etc/passwd")

    def test_unknown_launcher_never_executes(self):
        cfg = Config()
        actions = Actions(cfg, Feed(DemoProvider()))
        with patch("deskdeck.actions.subprocess.run") as run:
            with self.assertRaises(ValueError):
                actions.run("open_app", "/bin/sh")
            run.assert_not_called()

    def test_demo_always_simulates(self):
        cfg = Config(enable_actions=True)
        actions = Actions(cfg, Feed(DemoProvider()))
        with patch("deskdeck.actions.subprocess.run") as run:
            self.assertTrue(actions.run("open_app", "browser")["simulated"])
            run.assert_not_called()

    def test_real_launcher_uses_argument_array(self):
        cfg = Config(mode="file", enable_actions=True)
        actions = Actions(cfg, Feed(DemoProvider()))
        with (
            patch("deskdeck.actions.platform.system", return_value="Darwin"),
            patch("deskdeck.actions.subprocess.run") as run,
        ):
            run.return_value.returncode = 0
            actions.run("open_app", "browser")
            self.assertEqual(
                run.call_args.args[0], ["/usr/bin/open", "-a", "Google Chrome"]
            )


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.key = "test-only-" + "x" * 32
        self.cfg = Config(pairing_key=self.key)
        self.server = make_server(self.cfg, bind_port=0)
        self.cfg.port = self.server.server_address[1]
        self.cfg.public_url = f"http://127.0.0.1:{self.cfg.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, auth=True, origin=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.cfg.port, timeout=3)
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = "Bearer " + self.key
        if origin:
            headers["Origin"] = self.cfg.public_url
        conn.request(
            method, path, json.dumps(body) if body is not None else None, headers
        )
        response = conn.getresponse()
        data = response.read()
        status = response.status
        conn.close()
        return status, data

    def test_state_needs_key(self):
        self.assertEqual(self.request("GET", "/api/state", auth=False)[0], 401)
        status, data = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertNotIn(self.key.encode(), data)

    def test_action_needs_origin(self):
        self.assertEqual(
            self.request(
                "POST",
                "/api/action",
                {"action": "open_app", "target": "browser"},
                origin=False,
            )[0],
            403,
        )

    def test_invalid_action_type_is_rejected(self):
        self.assertEqual(
            self.request("POST", "/api/action", {"action": ["open_app"]})[0], 400
        )

    def test_static_allowlist_and_no_secret(self):
        status, data = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertNotIn(self.key.encode(), data)
        self.assertEqual(self.request("GET", "/static/app.js")[0], 200)
        self.assertEqual(self.request("GET", "/config.local.toml")[0], 404)
        self.assertEqual(self.request("GET", "/../config.local.toml")[0], 404)

    def test_paired_demo_action(self):
        status, data = self.request(
            "POST", "/api/action", {"action": "open_app", "target": "browser"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data)["simulated"])

    def test_unknown_target(self):
        self.assertEqual(
            self.request(
                "POST", "/api/action", {"action": "open_app", "target": "anything"}
            )[0],
            400,
        )


if __name__ == "__main__":
    unittest.main()
