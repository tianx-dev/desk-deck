# Verification for the initial public version

These are checks performed on the extracted package, separate from the earlier personal prototype. The screenshot uses only the synthetic browser preview.

## Automated and installation checks

- A fresh virtual environment installed the package with its Cast extra (PyChromecast 14.0.10).
- 20 unit/integration tests passed locally using Python 3.14.2 on macOS. Coverage includes authentication, action origins, static-file allowlisting, configured action dispatch, demo isolation, atomic task publication, source failure, notification baseline/deduplication, hidden-content exclusion, and startup without reverse DNS.
- CI runs the same suite and public-file check on Python 3.11, 3.12, and 3.13. Refer to the repository Actions result for the current status.
- The public-file scan found no matches; the synthetic screenshot was reviewed visually. This is bounded verification, not a guarantee that a scanner can detect every secret.

## Browser checks

At 1024 × 600, the demo rendered its five app tiles, Focus, task rail, and navigation. A simulated launcher returned visible preview feedback. A paused focus timer remained paused after reload. Going offline disabled app launchers; reconnecting restored them. An additional 800 × 480 check found no horizontal page overflow.

With a separate private configuration, pairing removed the key from the visible address bar. CLI-published active and ready states appeared in the UI, and a new ready transition created an Activity notification. This exercised the ordinary local task-file integration without Codex.

## Physical device and Mac action checks

The public package was cast to a Google Nest Hub. Its authenticated heartbeat reported **1024 × 600** and **2 touch points**, proving that the Hub loaded and executed the paired local page. An authenticated HTTP launcher request successfully opened the configured application on macOS.

Physical taps were verified during the original prototype. This public-package check did **not** include a new manually observed tap on the Hub; a page heartbeat and a desktop HTTP action are separate evidence. Follow the README's physical-tap step when reproducing on your own device.

Not covered: every Hub generation/firmware, all-day reliability, wake-from-sleep recovery, arbitrary application window selection, Windows/Linux action backends, or compatibility with every Codex database version.

## Machine picker, larger controls, and Mac companion

- 25 tests now pass, adding machine configuration, duplicate/invalid destination rejection, selected-key disclosure boundaries, peer identity checks, cross-origin task denial, and combined server/Cast cleanup.
- Two isolated local servers exercised real browser navigation in both directions. An unavailable third destination kept the original page open with an error. Escape closed the native dialog and returned focus to its connection button.
- The enlarged controls were checked at 1024 × 600 and 800 × 480. At the smaller size, launcher content fits and the machine list scrolls inside its dialog.
- The native AppKit launcher compiled for Apple Silicon with a macOS 13 deployment target and passed ad-hoc signature verification. The combined desktop command received the physical Hub's 1024 × 600, two-touch-point heartbeat. After the macOS folder permission prompt was handled, the app-owned server also received the physical Hub heartbeat. Quitting the app stopped its web server; reopening automatically restarted the server and received a fresh Hub heartbeat. A new installation may first require macOS permission for its configured folder/network; respond to the OS prompt to complete startup.
