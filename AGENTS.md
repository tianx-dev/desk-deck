# Working on Desk Deck

This is a Nest Hub touch interface served by a local computer. Keep the core independent of any AI or coding-agent product. The generic local task feed and Mac launchers are core features; the Codex log adapter is optional.

- Keep launcher positions stable. Preserve large touch targets, press feedback, keyboard access, reduced-motion support, and explicit offline state.
- Route actions through configured launcher ids or current task ids. Never add a shell-command endpoint or evaluate commands from task text.
- Use synthetic fixtures and screenshots. Never commit local configs, pairing URLs, credentials, session records, machine paths, device identifiers, or personal task titles.
- Do not treat a Cast launch acknowledgement as proof the page loaded. Check the display heartbeat, then test a physical tap.
- A ready result is a reported task state, not independently verified project success.
- Run `python3 -m unittest discover -s tests -v` and `python3 scripts/check_public.py` before committing.
- Verify UI changes at 1024 × 600. Keep ordinary-browser preview available for development, while documenting Nest Hub as the primary device.
- Keep documentation and replay prompts consistent with the final code. Prompts are edited reproduction examples, not a verbatim transcript.
