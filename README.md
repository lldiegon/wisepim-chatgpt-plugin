# WisePIM for ChatGPT and Codex

Connect WISEPIM, your product information management (PIM) workspace, to ChatGPT
and Codex. Search your product catalog, inspect product data quality, and prepare
native AI product data enrichment and product translation for approval in WISEPIM.

Use the plugin to find missing descriptions, review catalog quality evidence,
prepare translations into configured languages, and track native jobs through to
saved results. Channel-readiness reviews identify gaps and unknown requirements;
they do not certify, export, or publish products.

This repository contains public plugin packaging. The hosted MCP service belongs
to the WisePIM frontend repository; no backend code or credentials are included here.

The intended endpoint is `https://wisepim.com/mcp`. It is a deployment target,
not a claim that the service is enabled, tested in ChatGPT, approved or published.
The package is version `0.1.3` and connects to one explicitly authorized project.

## Build

Python 3.11+ and Git are sufficient; no dependency installation is required.

```sh
git clone https://github.com/lldiegon/wisepim-skills ../wisepim-skills
python3 scripts/package.py sync --source ../wisepim-skills
python3 -m unittest discover -s tests
python3 scripts/package.py check
python3 scripts/package.py build
```

The ZIP is written to `dist/`, along with its SHA-256 checksum. It contains root
`plugin.json`, `mcp.json`, assets and vendored skills. Only an explicit public
file allowlist is packaged. `.git`, scripts, private reviewer credentials and
unrelated files are never included. Skills are copied as ordinary files and
pinned by source commit plus individual content hashes in `skills.lock.json`.
Synchronization rejects overlapping source/destination repositories before reading
or replacing files. Package inputs, lock files and output paths cannot use symlinks.

For local drafts use `sync --allow-uncommitted`, `check --preview`, and
`build --preview`. Preview ZIPs must not be submitted as releases. To change a
skill, edit [wisepim-skills](https://github.com/lldiegon/wisepim-skills), commit it,
then synchronize here. Do not edit the vendored copies independently.

## Connection and approval

OAuth uses the provided public client ID `wisepim-chatgpt`, PKCE, and the exact
MCP resource audience. Before connecting, the service operator must register
that client ID with the actual callback from OpenAI's connection flow. If the
registered ID differs, update `mcp.json` and its deployment registration together.
Use `python3 scripts/package.py configure-client --client-id ACTUAL_PUBLIC_CLIENT_ID`
to update the non-secret package setting after registration. The proposed default
client ID is not evidence that a client has been provisioned.
No callback URL, client secret, bearer token, or customer account belongs in this repo.

The package requests catalog, stored quality, task and settings reads plus native
enrichment execution. A translation preview requires approval in the ordinary
authenticated WisePIM review page. The assistant cannot approve its own work.
Queued work is not completed work. Read-only users and revoked connections must
remain constrained by current server-side permissions.

Channel-readiness reviews summarize available evidence and unverified requirements;
they do not certify marketplace acceptance, validate a feed, or publish products.

## Submission

Use the concrete [submission checklist](submission/README.md). Review prompts are
embedded in `plugin.json`: exactly five positive and three negative cases.
Reviewer credentials and a live demo recording are supplied privately in the
OpenAI dashboard. Automated local validation is not a replacement for platform review.
The [synthetic walkthrough](submission/synthetic-walkthrough.md) records independent
instruction checks without representing them as real host or provider execution.

Official references, checked 2026-10-28:

- [Plugin package format](https://developers.openai.com/plugins/build/plugins)
- [Submit and publish](https://developers.openai.com/plugins/deploy/submission)
- [Plugin guidelines](https://developers.openai.com/plugins/plugin-guidelines)
- [Remote MCP review requirements](https://developers.openai.com/plugins/deploy/app-review)
