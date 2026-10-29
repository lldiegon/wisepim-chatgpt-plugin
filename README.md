# WISEPIM for ChatGPT and Codex

Bring your product catalog into the conversation with WISEPIM, the AI-powered
product information management (PIM) workspace. Get help creating an account and
setting up a first catalog, or connect an existing project. Research product facts,
enrich descriptions and attributes, translate content, and clean inconsistent data.

Inspect supplier evidence, images, taxonomy and channel issues. Use available
commerce and search analytics to prioritize improvements, then prepare native
catalog jobs using your WISEPIM settings and saved prompts. Use the configured approval policy and follow the actual task through to saved results.

This repository contains public plugin packaging. The hosted MCP service belongs
to the WISEPIM frontend repository; no backend code or credentials are included here.

The intended endpoint is `https://wisepim.com/mcp`. It is a deployment target,
not a claim that the service is enabled, tested in ChatGPT, approved or published.
The package is version `0.3.0` and connects to one explicitly authorized project.
It includes seventeen skills for the matching 53-tool MCP service contract.


## Catalog workflows

Seventeen bundled skills cover guided account setup, catalog quality, product web research, research-backed native enrichment, translation, bulk text cleanup, commerce analysis, selected-product SEO evidence and opportunity planning, supplier documents, images, taxonomy, prompts/settings, channel issues and native improvement jobs. The [canonical skill library](https://github.com/lldiegon/wisepim-skills) describes each workflow.

Research is evidence-only and requires its own execution permission. Findings do not automatically replace catalog fields or images. Stored supplier documents use supported bounded extraction; unsupported PDF/OCR and new file imports remain in their native workflows. Supplier jobs operate on already imported rows. Image workflows assess stored evidence and can retrieve existing images through supported native jobs; MCP does not generate images, video or audio. Analytics reads persisted source evidence and reports mapping/coverage limits; it does not refresh providers or establish causal uplift.

Choose the declared job tool family and get a planning-only estimate before preparing a job. Gap filling, missing-image retrieval, category mapping, ad preparation and supplier completion each have separate typed estimate, preview and start tools. A catalog-job budget is an admission estimate ceiling, not a hard final-spend cap. Native job field policies and review gates remain authoritative after launch; the plugin does not expose arbitrary automation, bypass a gate or publish products. Track actual task/run receipts and reread saved products before claiming completion.

Each durable preview identifies its matching `apply_tool` from twelve declared executors. Execution accepts only the frozen `change_id`; a receipt cannot select a different operation or introduce another tool. The expanded package uses explicit catalog, quality, task, settings, prompts and analytics reads; catalog/settings/prompt writes under the configured approval policy; and enrichment, research and catalog-job execution. Existing grants do not gain new scopes automatically. Reconnect and consent only to the operations needed for your account and workflows.

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

The package requests explicit permissions for its supported workflows. New connections default to approval off. Requested actions can proceed from a durable preview without an extra browser confirmation. The account owner can enable required approval in WISEPIM connected apps settings. Enabled approval requires authenticated review of the exact proposal; the assistant cannot satisfy or disable that gate on the owner’s behalf. Project permissions, source checks, estimates and native job/field policies remain enforced in either mode. Queued work is not completed work; task receipts and saved products provide the execution evidence.

Channel-readiness reviews summarize available evidence and unverified requirements;
they do not certify marketplace acceptance, validate a feed, or publish products.

## Public package boundary

Public manifests and normal ZIPs contain runtime metadata and skills only. Internal
planning, reviewer scenarios and credentials stay outside this repository.
Operators can optionally provide external private test-case JSON with
`python3 scripts/package.py build --review-metadata /absolute/private/review-metadata.json`.
The builder validates that overlay and writes an ignored `dist/*-review.zip`;
it never changes source metadata. Reviewer credentials belong in the secure
platform form and are not accepted in this overlay.
Private positive cases use the official `expected_behavior` field. The builder
also accepts legacy `expected_output` inputs and normalizes them in the review
ZIP. Public release notes live under `extensions.com.openai.publication`;
private cases remain outside source and normal archives. Listing metadata uses at
most three starter prompts; each must be a nonempty, single-line string of at
most 128 characters.

Official references, checked 2026-10-28:

- [Plugin package format](https://developers.openai.com/plugins/build/plugins)
- [Submit and publish](https://developers.openai.com/plugins/deploy/submission)
- [Plugin guidelines](https://developers.openai.com/plugins/plugin-guidelines)
- [Remote MCP review requirements](https://developers.openai.com/plugins/deploy/app-review)

## Get started

Use `start-with-wisepim` to create or resume an account and finish initial catalog setup. The package declares it as its onboarding skill, and it works before connecting tools. Signup uses the native [WISEPIM onboarding flow](https://wisepim.com/onboarding), with user-controlled sign-in, verification and permissions. Once connected, the setup-status tool gives project-scoped next steps.

A plugin is optional: standalone agents can read the public [onboarding guide](https://wisepim.com/onboarding.md), [agent index](https://wisepim.com/llms.txt) and [REST authentication guide](https://wisepim.com/auth.md). The public REST API uses project API keys and supports its documented catalog operations; MCP uses separate OAuth project consent. Neither package installation nor this guide proves the matching service is deployed. Always spell the product name WISEPIM.
