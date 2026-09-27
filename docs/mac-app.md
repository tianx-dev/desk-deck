# Small native Mac companion

The companion is an AppKit window compiled from `macos/DeskDeckApp.swift`. Build it with your installed Desk Deck Python environment:

```sh
python3 scripts/build_mac_app.py --config config.local.toml
open 'dist/Desk Deck.app'
```

The build requires macOS and Xcode Command Line Tools. The generated bundle is ignored by Git. It records paths to your checkout, Python executable, and config, but does not copy your key into the executable or plist. Rebuild if those paths move. This is a local launcher, not a portable Python distribution or notarized installer.

On open, it runs `python -m deskdeck desktop --config ...`. That single process starts the HTTP server in a thread, then launches the Cast sender. Connection status becomes ready only after the Hub's authenticated heartbeat. Start & Cast retries after a stopped/failed launch. Stop or Quit terminates the owned process and its server. Closing the window keeps the app running; clicking its Dock icon restores the window. Stop any separately running server on the same port before opening the app.

There is no login installation or background daemon. You can choose to add your local build through macOS Login Items if you want it on login. An unavailable Hub, changed addresses, a sleeping computer, or a port already in use can prevent startup. Correct the config and use Start & Cast again. Automatic recovery from every sleep/network change is not promised.

For a fleet of Macs, keep `serve` running on peers without casting from each. Opening any companion intentionally casts that Mac onto the Hub. The touch picker can then navigate between paired servers.

If the Python environment or config lives in Documents, macOS can ask the new app for Documents-folder access. Respond to that system prompt; startup may wait until you do. Local-network or firewall prompts may also appear. The app does not change macOS privacy permissions.
