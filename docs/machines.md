# Choose a Mac from the display

Every Mac runs its own Desk Deck server. The Hub's **Connected to…** button opens a touch-friendly machine picker. A selection checks the destination and then loads its page, so both actions and task data belong to that Mac.

## Pair two Macs

1. Follow the README setup on both Macs, using each Mac's LAN IP and the same Hub IP. Give each a recognizable `--machine-name`, such as `Studio MacBook` and `Travel MacBook`. For existing configs, add `machine_name = "Studio MacBook"` at the top, before any `[[launchers]]` tables.
2. On Mac B, run `python3 -m deskdeck pair-url`. This prints a **private** pairing link. Transfer it to Mac A privately; do not share it in a chat, issue, screenshot, or repository.
3. On Mac A, run:

   ```sh
   python3 -m deskdeck pair-machine --id travel --name 'Travel MacBook'
   ```

   Paste B's private link into the hidden prompt. The command adds B to A's ignored config without placing the secret in shell history.
4. Repeat in the other direction: obtain A's private link, then run `pair-machine` on B with A's id and display name. This reciprocal pairing lets both servers recognize the other page's origin and provides the return option.
5. Restart both servers. Cast once, then use the display picker to switch. You do not need to cast again for each selection. Keep both server processes available; opening the companion on another Mac will cast immediately and take over the display, so use `serve` alone on additional Macs when you only want them available in the picker.

Each server's `allowed_clients` must include the Hub's current IP. Browser testing from a different computer also requires that browser computer's IP on both servers. Use each server's configured LAN URL; switching from a loopback preview to LAN origins is not the same pairing context.

## What happens when you tap

The current server resolves a configured machine id and provides that destination's pairing information. The browser performs a six-second authenticated check against the selected server. Only the dedicated identity-check route permits cross-origin access, and only from explicitly paired origins. General state/action routes retain their original origin checks.

On success, the browser navigates to the destination with its key in the URL fragment. The destination removes the fragment and keeps the key in session storage. On failure, the popup keeps you on the original machine and shows a retryable error. Closing the popup cancels an in-flight connection check.

The picker needs the current server to resolve a selection. If that server is already offline, reopen its app or cast from another Mac. A successful check cannot guarantee the destination remains awake during navigation. Focus/Quiet preferences are stored per server origin and do not migrate between Macs.

## Trust and configuration

Only explicitly paired machines appear. There is no network scanner. Each Mac stores its peers' keys in private configuration, so pair only computers you trust to share display access. Keep these configs out of Git. Changing a machine's address or key requires updating its peer entries and restarting the servers.

Up to eight other machines may be configured. `pair-machine` writes `[[machines]]` entries containing `id`, `name`, `url`, and `pairing_key`. Ordinary state responses include only the first three; the selected key is returned only by an authenticated selection action. See [SECURITY.md](../SECURITY.md) for the trusted-LAN and unencrypted HTTP limits.
