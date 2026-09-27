#!/usr/bin/env bash
# Run from the repository root, after configuring the local server.
# Replace the sleep with your actual build/test command.
set -eu
python3 -m deskdeck task --id example-build --title 'Example build' \
  --state active --message 'Running a small example job.' \
  --open-url 'https://example.org/project'
sleep 5
python3 -m deskdeck task --id example-build --title 'Example build' \
  --state ready --message 'The example job finished. This is sample data.'
