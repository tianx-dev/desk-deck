import ipaddress
import json
import secrets
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

DEFAULT_LAUNCHERS = [
    dict(
        id="browser",
        label="Browser",
        subtitle="Bring browser forward",
        icon="chrome",
        kind="app",
        target="Google Chrome",
    ),
    dict(
        id="terminal",
        label="Terminal",
        subtitle="Bring terminal forward",
        icon="terminal",
        kind="app",
        target="Terminal",
    ),
    dict(
        id="editor",
        label="Editor",
        subtitle="Bring your project forward",
        icon="code",
        kind="app",
        target="Visual Studio Code",
    ),
    dict(
        id="chat",
        label="Chat",
        subtitle="Bring conversations forward",
        icon="slack",
        kind="app",
        target="Slack",
    ),
    dict(
        id="mail",
        label="Mail",
        subtitle="Bring inbox forward",
        icon="mail",
        kind="app",
        target="Microsoft Outlook",
    ),
]
ICONS = {"code", "chrome", "terminal", "slack", "mail", "work", "grid", "bell", "open"}


@dataclass
class Config:
    host: str = "127.0.0.1"
    port: int = 8765
    public_url: str = "http://127.0.0.1:8765"
    pairing_key: str = ""
    allowed_clients: list[str] = field(default_factory=lambda: ["127.0.0.1"])
    mode: str = "demo"
    enable_actions: bool = False
    device_host: str = ""
    device_name: str = ""
    machine_name: str = "My Mac"
    machines: list[dict] = field(default_factory=list)
    data_file: str = ".runtime/tasks.json"
    codex_home: str = "~/.codex"
    codex_db: str = "state_5.sqlite"
    task_ids: list[str] = field(default_factory=list)
    expose_summaries: bool = False
    launchers: list[dict] = field(
        default_factory=lambda: [dict(x) for x in DEFAULT_LAUNCHERS]
    )

    def validate(self):
        ipaddress.ip_address(self.host)
        if not 1024 <= self.port <= 65535:
            raise ValueError("Choose a port from 1024 through 65535")
        u = urlsplit(self.public_url)
        if (
            u.scheme != "http"
            or not u.hostname
            or u.username
            or u.password
            or u.query
            or u.fragment
            or u.path not in ("", "/")
            or u.port != self.port
        ):
            raise ValueError(
                "public_url must be an http origin with the configured port"
            )
        if u.hostname != "localhost":
            ipaddress.ip_address(u.hostname)
        for address in self.allowed_clients:
            ipaddress.ip_address(address)
        if (
            not isinstance(self.machine_name, str)
            or not 1 <= len(self.machine_name.strip()) <= 60
        ):
            raise ValueError("Choose a machine name of 1 to 60 characters")
        if not isinstance(self.machines, list) or len(self.machines) > 8:
            raise ValueError("Configure up to eight other machines")
        machine_ids, machine_urls = set(), {self.public_url.rstrip("/")}
        for machine in self.machines:
            if not isinstance(machine, dict) or any(
                not isinstance(machine.get(k), str)
                for k in ("id", "name", "url", "pairing_key")
            ):
                raise ValueError(
                    "Each machine needs id, name, url, and pairing_key strings"
                )
            target = urlsplit(machine["url"])
            if (
                target.scheme != "http"
                or not target.hostname
                or target.username
                or target.password
                or target.path not in ("", "/")
                or target.query
                or target.fragment
                or target.port is None
                or not 1024 <= target.port <= 65535
            ):
                raise ValueError(
                    "Machine URLs must be http origins with explicit ports"
                )
            ipaddress.IPv4Address(target.hostname)
            if (
                not machine["id"].replace("_", "").isalnum()
                or len(machine["id"]) > 60
                or machine["id"] in machine_ids
                or machine["url"].rstrip("/") in machine_urls
                or not 1 <= len(machine["name"].strip()) <= 60
                or len(machine["pairing_key"]) < 32
            ):
                raise ValueError(
                    "Use unique machine ids and URLs, short names, and generated pairing keys"
                )
            machine_ids.add(machine["id"])
            machine_urls.add(machine["url"].rstrip("/"))
        if self.host not in ("127.0.0.1", "::1") and not self.pairing_key:
            raise ValueError("LAN serving requires a generated pairing key")
        if self.mode not in ("demo", "file", "codex"):
            raise ValueError("mode must be file, demo, or codex")
        if (self.mode != "demo" or self.enable_actions) and not self.pairing_key:
            raise ValueError("Real data or actions require a generated pairing key")
        if self.pairing_key and len(self.pairing_key) < 32:
            raise ValueError("pairing_key must contain at least 32 characters")
        if (
            not isinstance(self.task_ids, list)
            or len(self.task_ids) > 16
            or any(not isinstance(x, str) for x in self.task_ids)
        ):
            raise ValueError(
                "task_ids must be an explicit list of up to 16 identifiers"
            )
        if not 1 <= len(self.launchers) <= 5:
            raise ValueError("Configure one to five launchers; the sixth tile is Focus")
        ids = set()
        for item in self.launchers:
            if any(
                not isinstance(item.get(k), str)
                for k in ("id", "label", "subtitle", "icon", "kind", "target")
            ):
                raise ValueError(
                    "Each launcher needs string id, label, subtitle, icon, kind, and target"
                )
            if item["id"] in ids or not item["id"].replace("_", "").isalnum():
                raise ValueError("Launcher ids must be unique simple names")
            ids.add(item["id"])
            if (
                item["icon"] not in ICONS
                or item["kind"] not in ("app", "url")
                or not item["target"]
            ):
                raise ValueError("Invalid launcher kind, icon, or target")
            if item["kind"] == "url" and urlsplit(item["target"]).scheme not in (
                "http",
                "https",
                "codex",
            ):
                raise ValueError("URL launchers support only http, https, and codex")
        return self

    @property
    def origins(self):
        return {
            self.public_url.rstrip("/"),
            f"http://127.0.0.1:{self.port}",
            f"http://localhost:{self.port}",
        }

    @property
    def peer_origins(self):
        return {m["url"].rstrip("/") for m in self.machines}


def load_config(path):
    with Path(path).open("rb") as f:
        raw = tomllib.load(f)
    allowed = set(Config.__dataclass_fields__)
    if set(raw) - allowed:
        raise ValueError(
            "Unknown configuration fields: " + ", ".join(sorted(set(raw) - allowed))
        )
    config = Config(**raw).validate()
    file_path = Path(config.data_file).expanduser()
    config.data_file = str(
        file_path
        if file_path.is_absolute()
        else Path(path).resolve().parent / file_path
    )
    return config


def add_machine(path, machine_id, name, pairing_link):
    config = load_config(path)
    link = urlsplit(pairing_link.strip())
    key = parse_qs(link.fragment).get("key", [""])[0]
    machine = dict(
        id=machine_id,
        name=name,
        url=link._replace(fragment="").geturl().rstrip("/"),
        pairing_key=key,
    )
    config.machines.append(machine)
    config.validate()
    with Path(path).open("a") as f:
        f.write("\n[[machines]]\n")
        for key, value in machine.items():
            f.write(key + " = " + json.dumps(value) + "\n")


def write_local_config(
    path,
    lan_host="",
    device_host="",
    device_name="",
    enable_actions=False,
    machine_name="My Mac",
):
    c = Config(
        mode="file",
        enable_actions=enable_actions,
        pairing_key=secrets.token_urlsafe(32),
        machine_name=machine_name,
    )
    if lan_host:
        ipaddress.ip_address(lan_host)
        if not device_host:
            raise ValueError("Supply --device-host when configuring LAN access")
        ipaddress.ip_address(device_host)
        c.host = "0.0.0.0"
        c.public_url = f"http://{lan_host}:{c.port}"
        c.allowed_clients = list(dict.fromkeys(["127.0.0.1", lan_host, device_host]))
        c.device_host, c.device_name = device_host, device_name
    c.validate()
    lines = ["# Private configuration. Never commit or share this file."]
    for key, value in vars(c).items():
        if key in ("launchers", "machines"):
            continue
        lines.append(key + " = " + json.dumps(value, ensure_ascii=False))
    for launcher in c.launchers:
        lines.append("\n[[launchers]]")
        lines.extend(key + " = " + json.dumps(value) for key, value in launcher.items())
    p = Path(path)
    # Exclusive creation prevents replacing an existing setup accidentally.
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")
