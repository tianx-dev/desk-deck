# Security and privacy

Desk Deck controls applications on a local computer. Use it only on a trusted private LAN. It is not a hardened remote-access product or a public Internet service.

## Boundaries

- Local setup generates a random pairing key in `config.local.toml`, which is ignored by Git and created with owner-only permissions.
- The default browser preview binds to loopback, uses fictional data, and simulates actions.
- LAN data requests require a configured client IP, an allowed Host, and a bearer key. Mutating requests also require the expected Origin.
- Requests select configured launcher ids or current task ids. They cannot supply a command line. The action runner uses argument arrays without a shell.
- Task destinations are limited to `http`, `https`, and `codex`. Their contents are not executed as instructions.
- Only the page, two static assets, and documented API paths are served. The server does not expose its working directory.
- No credentials, task files, browser captures, or runtime logs are included in the public source. Normal server logging does not record request bodies, Authorization headers, or pairing URLs.

## Limits that matter

**HTTP is unencrypted.** A peer capable of observing LAN traffic could see task data or the pairing key. Client IP and Origin checks do not replace transport encryption. Do not port-forward this service or expose it through a public tunnel. For a stronger environment, add a trusted HTTPS transport and revisit pairing and deployment together.

**DashCast is a third-party receiver.** The pairing URL is sent to that receiver as part of launching the page. Its URL fragment is not sent as part of ordinary HTTP page requests, but the receiver can see the launch URL. The Cast ecosystem and receiver host are trust dependencies. A registered receiver you control would reduce that dependency; this project does not provide one yet.

**The local configuration and task producers are trusted.** Someone who can edit them can alter app targets or destinations. Do not fill the task file with unreviewed URLs from an untrusted source. App/link activation is not an approval mechanism for higher-risk actions.

**The Codex adapter is opt-in.** It exposes only selected task ids and hides message text by default. Even task titles may be private. Do not point it at sessions you do not want on the display. The parser's omission of tool output/reasoning is not a general secret-redaction system for user-visible messages.

**Notifications are observations.** Task producers can report incorrect status. The display does not independently validate a build, deployment, or external service.

## Before sharing a fork

Run `python3 scripts/check_public.py`, inspect the diff, and generate screenshots in synthetic demo mode. Do not copy a live workspace or publish a raw conversation export. Check the exact staged files, not only `.gitignore`.

To revoke a pairing key, stop the server, remove the old private config, generate a new one, and pair the display again. Old browser session storage may retain the old key, but the server will no longer accept it.

## Reporting an issue

Do not put keys, private pairing links, personal task data, or raw session files in a public issue. Use GitHub's private vulnerability-reporting feature if enabled for this repository; otherwise open a minimal issue requesting a private reporting route without disclosing exploit details or private data.
