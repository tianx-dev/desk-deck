import argparse
import getpass
import sys
from pathlib import Path

from .casting import cast, pairing_url
from .config import Config, load_config, write_local_config, add_machine
from .server import serve
from .publish import publish


def main():
    parser = argparse.ArgumentParser(
        description="Desk Deck: local touch launcher and task display"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("serve", help="Run the local display server")
    run.add_argument("--config", type=Path)
    run.add_argument(
        "--demo",
        action="store_true",
        help="Synthetic data and simulated actions; loopback only",
    )
    run.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Demo port; configured mode uses the config port",
    )
    init = sub.add_parser(
        "init", help="Create an ignored private configuration with a new pairing key"
    )
    init.add_argument("--output", type=Path, default=Path("config.local.toml"))
    init.add_argument("--lan-host", default="")
    init.add_argument("--device-host", default="")
    init.add_argument("--device-name", default="")
    init.add_argument("--machine-name", default="My Mac")
    pair = sub.add_parser("pair-machine", help="Add another Mac to the display picker")
    pair.add_argument("--config", type=Path, default=Path("config.local.toml"))
    pair.add_argument("--id", required=True)
    pair.add_argument("--name", required=True)
    init.add_argument(
        "--enable-actions",
        action="store_true",
        help="Enable the configured Mac launcher actions",
    )
    task = sub.add_parser("task", help="Publish a local task update for the display")
    task.add_argument("--config", type=Path, default=Path("config.local.toml"))
    task.add_argument("--id", required=True)
    task.add_argument("--title", required=True)
    task.add_argument(
        "--state",
        choices=["active", "ready", "quiet", "stopped", "unknown"],
        required=True,
    )
    task.add_argument("--message", default="")
    task.add_argument("--open-url", default=None)
    for name, help_text in [
        ("desktop", "Start the local server and cast together"),
        ("cast", "Launch on a configured Cast display"),
        ("pair-url", "Print a PRIVATE pairing link locally; never share it"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--config", type=Path, default=Path("config.local.toml"))
    args = parser.parse_args()
    try:
        if args.command == "init":
            write_local_config(
                args.output,
                args.lan_host,
                args.device_host,
                args.device_name,
                args.enable_actions,
                args.machine_name,
            )
            print(
                f"Created {args.output}. It contains a secret; keep it private and out of Git."
            )
        elif args.command == "pair-machine":
            link = getpass.getpass(
                "Paste the other Mac's private pairing link (hidden): "
            )
            add_machine(args.config, args.id, args.name, link)
            print(
                "Machine added. Pair this Mac on the other Mac too, then restart both servers."
            )
        elif args.command == "serve":
            if args.config and args.demo:
                raise ValueError("Choose --demo or --config, not both")
            config = (
                load_config(args.config)
                if args.config
                else Config(
                    port=args.port, public_url=f"http://127.0.0.1:{args.port}"
                ).validate()
            )
            serve(config)
        else:
            config = load_config(args.config)
            if args.command == "task":
                publish(
                    config, args.id, args.title, args.state, args.message, args.open_url
                )
                print("Task update saved locally.")
            elif args.command == "pair-url":
                print(pairing_url(config))
            elif args.command == "cast":
                cast(config)
            elif args.command == "desktop":
                from .desktop import desktop

                try:
                    desktop(config)
                except Exception:
                    print(
                        "Error: Could not start the server or connect to the Hub. Check configuration and network.",
                        file=sys.stderr,
                    )
                    raise SystemExit(2) from None
    except (ValueError, OSError, KeyError) as error:
        # Do not echo configuration values, URLs containing keys, or library request details.
        if isinstance(error, ValueError):
            print(f"Error: {error}", file=sys.stderr)
        else:
            print(
                f"Error: {type(error).__name__}. Check the local configuration and troubleshooting guide.",
                file=sys.stderr,
            )
        raise SystemExit(2)
