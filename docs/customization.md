# Make it yours

Start with the main README's Nest Hub setup. Keep changes to machine-specific settings in `config.local.toml`; restart the server after editing that file.

## Launcher buttons

Configure one to five launchers. Focus is added automatically. Use the exact application name installed on your Mac:

```toml
[[launchers]]
id = "browser"
label = "Research"
subtitle = "Bring Safari forward"
icon = "chrome"
kind = "app"
target = "Safari"
```

Or open a destination:

```toml
[[launchers]]
id = "project"
label = "Project"
subtitle = "Open the project board"
icon = "work"
kind = "url"
target = "https://example.org/project"
```

Supported icon names: `code`, `chrome`, `terminal`, `slack`, `mail`, `work`, `grid`, `bell`, and `open`. These are simple inline line drawings, not downloaded assets. Labels and icons are independent of the actual target.

Do not put credentials in a launcher URL. The config is trusted local input; someone able to edit it can change what a button opens. HTTP requests can only select configured ids, not introduce a new target.

## Task feeds

Start with the CLI in [integrations.md](integrations.md). You can connect builds, batch jobs, local scripts, or personal workflows without adding an agent. Use concrete messages such as “18 of 24 files processed” when your source actually measures that count.

Good messages answer one of these:

- What is happening now?
- What changed since the last check?
- What result is ready to inspect?
- Which destination should I open?

Avoid duplicating your full email inbox or every chat notification. The display has limited space; choose events that help you decide what to do next.

## Layout and style

- `web/style.css`: palette, typography, tile spacing, breakpoints, and motion.
- `web/index.html`: page structure, SVG symbols, and dialogs.
- `web/app.js`: data polling, launcher feedback, navigation, quiet mode, and timer state.

No Node tooling is required to run the project. Formatting the frontend with Prettier is optional.

The default grid is three columns by two rows. Preserve a stable launcher order and avoid content updates replacing a button while someone is pressing it. Test the real 1024 × 600 viewport and a physical tap, not just mouse clicks. Preserve native button semantics and reduced-motion behavior.

## Other data providers

A provider implements `tasks()` and returns normalized task dictionaries. See `DemoProvider` and `FileProvider`. The `Feed` owns notification deduplication; the provider owns truth and timestamps. Add deterministic fixture tests before connecting a new source.

Prefer a provider returning minimal normalized data over sending raw logs to the browser. Treat external text as data and render it with `textContent`, never HTML or executable instructions.

## What is deliberately not included

Arbitrary shell commands from the display, automatic approvals, desktop screen scraping, an unrestricted window controller, cloud accounts, and remote-machine polling. These require additional design and permissions. Existing app buttons and task links already work without macOS Accessibility permission.
