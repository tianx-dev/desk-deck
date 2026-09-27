"""Build a small local companion. The generated bundle is machine-specific, not for Git."""

import argparse
import plistlib
import platform
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.local.toml"))
    parser.add_argument("--output", type=Path, default=Path("dist/Desk Deck.app"))
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("The companion app requires macOS and Xcode Command Line Tools")
    root = Path(__file__).resolve().parents[1]
    contents = args.output.resolve() / "Contents"
    binary = contents / "MacOS" / "DeskDeck"
    binary.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "xcrun",
            "swiftc",
            "-swift-version",
            "5",
            "-target",
            platform.machine() + "-apple-macosx13.0",
            str(root / "macos/DeskDeckApp.swift"),
            "-o",
            str(binary),
            "-framework",
            "Cocoa",
        ],
        check=True,
    )
    info = dict(
        CFBundleExecutable="DeskDeck",
        CFBundleIdentifier="org.deskdeck.local",
        CFBundleName="Desk Deck",
        CFBundleDisplayName="Desk Deck",
        CFBundlePackageType="APPL",
        CFBundleShortVersionString="0.2.0",
        CFBundleVersion="2",
        LSMinimumSystemVersion="13.0",
        NSLocalNetworkUsageDescription="Connect to your Nest Hub and serve your local touch deck.",
        DeskDeckPython=sys.executable,
        DeskDeckRoot=str(root),
        DeskDeckConfig=str(args.config.resolve()),
    )
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump(info, f)
    subprocess.run(
        ["codesign", "--force", "--deep", "--sign", "-", str(args.output.resolve())],
        check=True,
    )
    print(
        f"Built {args.output}. Keep the checkout and Python environment in place. Open it to start and cast."
    )


if __name__ == "__main__":
    main()
