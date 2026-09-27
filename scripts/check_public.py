"""Guard against common private artifacts in public source. Not a full secret scanner."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    ".runtime",
    ".playwright-mcp",
    "dist",
    "build",
}
PATTERNS = {
    "personal absolute path": re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/"),
    "private LAN address": re.compile(
        r"\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
    ),
    "embedded private key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "literal credential": re.compile(
        r"""(?:pairing_key|api_key|access_token)\s*[:=]\s*["'][A-Za-z0-9_/-]{24,}["']""",
        re.I,
    ),
    "private pairing link": re.compile(r"#key=[A-Za-z0-9_-]{24,}"),
}


def candidates():
    tracked = set()
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True)
    if proc.returncode == 0:
        tracked = {ROOT / p.decode() for p in proc.stdout.split(b"\0") if p}
    paths = set(tracked)
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if not path.is_file() or any(
            p in EXCLUDED or p.endswith(".egg-info") for p in rel.parts
        ):
            continue
        if (
            path.name.endswith(".local.toml")
            or path.name.startswith(".env")
            or path.suffix in {".log", ".pid", ".jsonl", ".pyc", ".lock", ".tmp"}
        ):
            continue
        paths.add(path)
    return sorted(paths)


def main():
    findings = []
    for path in candidates():
        if not path.exists():
            continue
        relative = path.relative_to(ROOT)
        if (
            path.name.endswith(".local.toml")
            or path.suffix in {".sqlite", ".db", ".jsonl", ".log", ".pid"}
            or path.name == ".env"
        ):
            findings.append((relative, "runtime artifact is tracked"))
            continue
        if path.suffix in {".png", ".jpg", ".webp"}:
            continue  # Screenshots require visual review of synthetic content.
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            findings.append((relative, "unexpected binary artifact"))
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append((relative, label))
    for path, label in findings:
        print(f"{path}: {label}")
    print(
        f"Public-file scan: {len(findings)} finding(s). Screenshots require separate visual review."
    )
    return bool(findings)


if __name__ == "__main__":
    sys.exit(main())
