# Troubleshooting and compatibility

## What was verified

The original experiment ran on a Google Nest Hub reporting a 1024 × 600 Fuchsia/Chrome browser. The local page loaded, physical touches reached the Mac, and configured actions could be requested. The extracted project includes synthetic browser and automated tests; see [verification details](verification.md) for the checks performed on this version.

This is not a claim of support for every Nest Hub generation, every Cast device, or every firmware version. A normal Chromecast attached to a TV does not gain touch input from this project.

## The Cast app launches, but the page does not load

1. Confirm the server is running and open its public URL from another device on the same LAN.
2. Confirm `public_url` uses the Mac's LAN address, not `localhost` or the Hub's address.
3. Check the configured port, macOS incoming-connection permission, and guest/IoT network isolation. The Hub must initiate a connection back to the Mac.
4. Check the Cast command for an actual page receipt. A receiver launch acknowledgement is insufficient.
5. Stop and recast. Forced navigation replaces the receiver page, so an old receiver message channel may no longer accept a new URL.

The project uses the device's local `/setup/eureka_info` endpoint to obtain its Cast id. If your device disables that endpoint or omits `ssdp_udn`, the current launcher cannot identify it; add an alternate discovery adapter rather than guessing a device id.

## Pairing or origin errors

Generate a private config with `init`. Do not copy `config.example.toml` onto your LAN and add an empty key. Make sure allowed clients include the actual Hub IP and that the URL's host/port match `public_url`.

For a browser on your Mac, run `python3 -m deskdeck pair-url --config config.local.toml` and open the private link. Do not paste that link into issues, screenshots, or chat. The UI removes the key from its address bar after loading.

## A button says preview instead of opening an app

`mode = "demo"` always simulates. Use the generated setup with `mode = "file"` and `enable_actions = true` for real buttons. The README's `init --enable-actions` command does that. Restart the server after config changes.

## A configured application will not open

Check the exact installed application name in `[[launchers]]`. Defaults are examples; not every Mac has Chrome, Slack, Outlook, or Visual Studio Code installed. Replace them with your apps. The action runner currently uses macOS `/usr/bin/open`; Linux/Windows action backends are not implemented.

App activation is not arbitrary window selection. For a specific destination, use a supported URL/deep link. Opening a browser URL may create a new tab.

## Progress is Quiet or missing

Publish periodic updates for long jobs. After three minutes without updates, active work displays Quiet. The generic file source can be empty until you publish your first task; this is expected.

Notifications start from the server's baseline. Publish an active update, let the display observe it, then publish ready. Only a new ready completion currently adds an Activity notification. Restarting the server resets the inbox.

For Codex, confirm the selected task ids, database filename, schema, and record format. The adapter fails closed if it cannot parse the expected source. Do not repair this by making private files public or changing the source database.

## It stops working after sleep or an address change

Keep the host awake while using the deck. Reserve LAN addresses in your router or update the private config when addresses change. Relaunch the server and Cast session after wake if needed. Automatic restart, reconnection after sleep, and all-day Cast reliability are not yet guaranteed.

If desired, macOS can keep the computer awake while the server runs:

```sh
caffeinate -i python3 -m deskdeck serve --config config.local.toml
```

## Nothing should be installed on the Hub

Correct: the Hub loads a Cast browser page. The local server and Python Cast sender run on your computer. No custom firmware, root access, or factory reset is involved.
