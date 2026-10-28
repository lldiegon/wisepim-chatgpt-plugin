# Public plugin repository

This repository contains public packaging and instructions, never service code,
credentials, customer data, private reviewer accounts, or deployment configuration.
Preserve concurrent edits. Do not commit or publish unless requested.

Canonical skills live in `lldiegon/wisepim-skills`. Update them there, then run
`python3 scripts/package.py sync --source ../wisepim-skills`. Never hand-edit the
vendored `skills/` files. A release must pin clean committed source.

Run `python3 -m unittest discover -s tests`, `python3 scripts/package.py check`,
and `python3 scripts/package.py build` before handing off a release. These checks
do not establish deployed OAuth, live task execution, directory approval or publication.
