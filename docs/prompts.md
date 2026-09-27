# The prompts behind the build

This project grew from a simple question: could an unused Nest Hub become a useful part of a desk setup?

The prompts below are **edited reproduction prompts based on the actual build stages**. They are not a verbatim conversation export. Device addresses, personal tasks, account information, private context, and local paths have been removed. They are instructions to a coding assistant during development; the running deck is an ordinary local web app.

## 1. Establish what the hardware can do

> I have a Google Nest Hub on my local network. Can you help turn it into a useful desk display? Inspect only the device address I provide. Identify the model and available Cast services. Check whether a locally hosted interactive page can run on it. Distinguish network reachability, a Cast app launch, a loaded page, and verified touch input.

Supply your own device IP privately. Useful evidence: device self-identification, a successful request for the local page, a heartbeat identifying viewport/touch capability, and an actual tap reaching the host. Avoid broad network scans or claiming success from an app-launch acknowledgement.

## 2. Show a small end-to-end demo

> Show me a working demo on the physical Nest Hub first. Serve it from my computer. Include a clock, a focus timer, and one button that sends a harmless request back to the server. Display the acknowledgement and round-trip time. Use synthetic task data. Verify a physical touch, not only a desktop browser click.

This isolates the highest-risk question: can the device both display a local page and send touch input back? In the original prototype, the Hub loaded a 1024 × 600 page and the server received physical touch events. That made the later control deck feasible.

## 3. Give it a Stream Deck-style interaction

> Make the interface feel like a touch control deck for my Mac. Use large tactile buttons with fixed positions and visible press feedback. One tap should activate a configured app or open a configured destination. Keep changing task information in a separate panel so launcher buttons never move underneath my finger. Optimize for a 1024 × 600 Nest Hub.

The resulting design uses a fixed launcher grid, bottom navigation, and a compact activity rail. A dedicated task view provides more detail without turning the home screen into a wall of text.

## 4. Make the information worth glancing at

> Help me see what changed, which work is active, and what result is ready to review. Show the latest concrete update and its age. Never invent progress percentages. Do not equate a finished response with a successful project. Add a quiet activity inbox, deduplicate notifications, and mark stale or disconnected data visibly. Keep source truth and actions in deterministic code.

A generic task producer reports state; the display does not guess it. Newly ready results create notifications. Old history does not flood the inbox at startup. Quiet mode and the focus timer suppress banners while preserving the inbox.

## 5. Make the project reproducible and customizable

> Extract a standalone open-source version for Nest Hub and a local computer. Codex must not be required. Make app launchers configurable and let ordinary scripts publish progress through a simple local command. Include a browser preview with fictional data for development. Put real addresses, device identifiers, tokens, and selected task ids in ignored local configuration. Explain the setup from a fresh clone and include troubleshooting.

Core acceptance criteria:

- A fresh clone can run the synthetic preview without private data or AI accounts.
- A user can configure their own Hub, cast the page, and verify a physical tap.
- The main guide enables real configured app actions and demonstrates real task publishing.
- Optional integrations remain optional and document their failure modes.
- Screenshots, tests, examples, and history contain no private runtime captures.

## 6. Ask the assistant to validate its claims

> Test a fresh installation, request authentication, launcher allowlisting, source failure, notification baseline/deduplication, and task publication. Verify the UI at 1024 × 600, timer state after reload, offline recovery, and press/swipe behavior. Generate the README screenshot only from the synthetic demo. Scan the exact files to be published. Report what was tested on physical hardware separately from browser and fixture tests.

## Adaptation prompt

After cloning, give your coding assistant this prompt with your own preferences:

> Read README.md, AGENTS.md, and docs/how-it-works.md. Adapt Desk Deck for my Nest Hub. My five launcher targets are [apps or links]. The task data I care about is [specific sources]. Preserve the local-server architecture, configured action boundary, large touch targets, and visible timestamps. Keep my network details and task data in ignored local config. First propose the smallest useful integration, then implement and verify it with synthetic fixtures before I connect the real source.

Good iteration is concrete: “this tile is hard to hit,” “show the last event time,” or “open this specific destination.” A vague request for more intelligence adds less value than a reliable action and an honest update.

## Follow-up: several Macs and one-click startup

> Add a touch-friendly popup that lets me choose which Mac the Hub controls. Make the current machine obvious and check a destination before navigating, preserving the current screen on failure. Increase text sizes and polish the launcher buttons. Draw the architecture in the README. Build a tiny native Mac launcher that starts the local server and casts when opened, with visible connection state and a Stop action. Keep paired machine credentials private and preserve the local-server architecture.
