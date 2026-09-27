# Contributing

Start with README.md and docs/how-it-works.md. The primary user experience is a Nest Hub served by a local computer; the core must not depend on a particular coding agent.

## Development loop

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
python3 -m deskdeck serve --demo
python3 -m unittest discover -s tests -v
python3 scripts/check_public.py
```

Use `.[cast]` when testing on hardware. There is no required frontend build step. Keep Python changes readable and use ordinary browser APIs in the frontend.

For UI changes, check the 1024 × 600 viewport, large touch targets, keyboard focus, reduced motion, offline state, and actual hardware when available. Browser tests are useful, but do not label them physical touch verification.

For task providers, include synthetic fixtures for fresh, stale, ready, interrupted, and unavailable states. Never commit a real session/database capture. For action changes, test unknown ids, unsupported destinations, unauthenticated requests, and unsuccessful launches.

## Public artifacts

Use fictional task titles and documentation-only addresses. Keep machine-specific config, runtime files, and pairing links outside Git. Generate screenshots from the synthetic provider and review them visually. The public-file scan is a useful guard, not a complete security audit.

Explain what changed, how it was verified, and any remaining hardware or OS limits in a pull request. Avoid adding a cloud service, model dependency, arbitrary command endpoint, or unattended startup process without discussing the design first.
