# Connect real task data

The core integration is a local JSON file, not Codex. Start the server in `mode = "file"` using your generated private config.

## Publish from a script

Use a stable id throughout one job:

```sh
python3 -m deskdeck task --id docs-build --title 'Documentation build' \
  --state active --message 'Rendering documentation.' \
  --open-url 'https://example.org/docs'

# Replace this with your real command.
if your-build-command; then
  python3 -m deskdeck task --id docs-build --title 'Documentation build' \
    --state ready --message 'Documentation is ready to review.'
else
  python3 -m deskdeck task --id docs-build --title 'Documentation build' \
    --state stopped --message 'The build stopped. Open the logs for details.'
fi
```

`examples/build-task.sh` is a runnable synthetic five-second job. It never claims to run a real build.

The command writes locally, under `.runtime/` by default. It does not contact an AI service or send a message to another person. Run it from the project folder, or pass `--config /path/to/config.local.toml` explicitly. Relative task-file paths resolve against the config's directory.

## Task contract

`examples/tasks.json` shows the shape. Important fields:

| Field | Meaning |
|---|---|
| `id` | Stable identity for one displayed work item |
| `title` | Short, human-readable title |
| `state` | `active`, `ready`, `quiet`, `stopped`, or `unknown` |
| `updated` | Unix timestamp for the latest producer observation |
| `summary` | A short user-visible update, never a raw log dump |
| `completion` | A new unique string when a new result becomes ready |
| `open_url` | Optional `http`, `https`, or `codex` destination |
| `quiet` | Suppress notification for an intentionally non-actionable update |

Publish periodically while work is active. After 180 seconds without an update, the UI shows Quiet rather than implying continuous progress. A ready result keeps its timestamp; it does not become “currently healthy” just because the display is connected.

The current notification inbox surfaces new ready results from already-observed tasks. Publish an active update before the ready update. Interrupted/stopped work is visible on task cards, but does not yet create a separate failure notification. “Needs your answer” is not inferred from message text.

If you write the JSON yourself, write a temporary file and atomically replace the destination. The CLI already handles locking, timestamps, completion ids, and atomic replacement. The source file is capped at 1 MB and 32 tasks are displayed.

## Optional Codex adapter

This is optional and version-sensitive. It is not required for Nest Hub, launcher actions, the generic task feed, notifications, or focus timers.

Edit only your private config:

```toml
mode = "codex"
codex_home = "~/.codex"
codex_db = "state_5.sqlite"
task_ids = ["REPLACE_WITH_A_TASK_ID_YOU_CHOSE"]
expose_summaries = false
```

Select task ids from the Codex task links available in your app. The prototype's link format is `codex://threads/<task-id>`; desktop routing can change between versions. No tasks are exposed if the list is empty.

The adapter expects a local `threads` table with `id`, `name`, `rollout_path`, `archived`, and `updated_at`, and session events for started/completed turns and visible assistant messages. It was derived from a working local installation; these are **not stable public storage APIs**. If incompatible, the feed reports unavailable. Do not modify the database or copy it into this repository.

The reader checks that session paths remain under the configured Codex home, uses SQLite read-only mode, bounds reads to 2 MB per selected session, and omits reasoning/tool output. `expose_summaries = true` additionally displays user-visible message text; inspect your tasks before enabling it on a shared display.

For a deeper integration, consider a new adapter using the [documented app-server interface](https://learn.chatgpt.com/docs/app-server). Connecting to the same live desktop execution engine and remote hosts is separate work; this adapter does not claim to do that.
