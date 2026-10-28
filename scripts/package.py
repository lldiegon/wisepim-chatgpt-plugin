#!/usr/bin/env python3
"""Allowlisted, reproducible public plugin packages with pinned skill provenance."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/lldiegon/wisepim-skills"
EXPECTED_SKILLS = {"catalog-quality-audit", "prepare-product-translations", "channel-readiness-review"}
FIXED_FILES = ("plugin.json", "mcp.json", "assets/icon.png", "assets/logo.png", "skills.lock.json", "LICENSE")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def skill_files(root):
    directory = root / "skills"
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("skills/ must be a real directory")
    files = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Skill symlinks are not allowed")
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        parts = Path(rel).parts
        if len(parts) < 3 or parts[1] not in EXPECTED_SKILLS:
            raise ValueError(f"Unexpected skill path: {rel}")
        if path.suffix != ".md" and not (len(parts) == 4 and parts[2:] == ("agents", "openai.yaml")):
            raise ValueError(f"Only Markdown and agents/openai.yaml are distributable: {rel}")
        data = path.read_bytes()
        if len(data) > 256_000:
            raise ValueError(f"Oversized skill file: {rel}")
        data.decode("utf-8")
        files[rel] = data
    for name in EXPECTED_SKILLS:
        text = files.get(f"skills/{name}/SKILL.md", b"").decode()
        if not text.startswith("---\n") or not re.search(rf"(?m)^name: {re.escape(name)}$", text):
            raise ValueError(f"Missing skill or frontmatter name: {name}")
    return files


def source_state(source):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    try:
        commit = git("rev-parse", "HEAD")
        dirty = bool(git("status", "--porcelain", "--untracked-files=all"))
        # The source checkout must be its own repository, not a parent repository.
        if Path(git("rev-parse", "--show-toplevel")).resolve() != source.resolve():
            raise ValueError("Source must be a standalone Git repository")
        return commit, dirty
    except subprocess.CalledProcessError:
        return None, True


def sync(source, allow_uncommitted=False, root=ROOT):
    files = skill_files(source)
    commit, dirty = source_state(source)
    if (dirty or not commit) and not allow_uncommitted:
        raise ValueError("Release sync requires a clean committed skills repository")
    if not dirty and commit:
        for rel, data in files.items():
            try:
                committed = subprocess.check_output(["git", "-C", str(source), "show", f"{commit}:{rel}"])
            except subprocess.CalledProcessError as exc:
                raise ValueError(f"Skill is not tracked at the pinned commit: {rel}") from exc
            if committed != data:
                raise ValueError(f"Skill differs from the pinned commit: {rel}")
    target = root / "skills"
    if target.is_symlink():
        raise ValueError("Refusing to replace symlinked skills directory")
    if target.exists():
        shutil.rmtree(target)
    for rel, data in files.items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    lock = {"formatVersion": 1, "repository": REPOSITORY, "commit": commit,
            "sourceDirty": dirty, "files": {rel: digest(data) for rel, data in files.items()}}
    (root / "skills.lock.json").write_text(json.dumps(lock, indent=2) + "\n")


def check(root=ROOT, preview=False):
    p = json.loads((root / "plugin.json").read_text())
    if p.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json" or p.get("name") != "wisepim":
        raise ValueError("Invalid portable plugin identity")
    if not re.fullmatch(r"\d+\.\d+\.\d+", p.get("version", "")):
        raise ValueError("Use a semantic release version")
    ext = p["extensions"]["com.openai"]
    if any(key in ext for key in ("apps", "hooks")):
        raise ValueError("Public submission cannot include app references or lifecycle hooks")
    for kind, count in (("positive", 5), ("negative", 3)):
        cases = ext["review"]["test_cases"][kind]
        if len(cases) != count or any(not case.get("description") or not case.get("prompt") for case in cases):
            raise ValueError(f"Review requires exactly {count} complete {kind} cases")
        if kind == "positive" and any(not case.get("tools_triggered") for case in cases):
            raise ValueError("Positive review cases require actual tool names")
    interface = ext["interface"]
    for key in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
        if not interface.get(key, "").startswith("https://wisepim.com/") and interface.get(key) != "https://wisepim.com":
            raise ValueError(f"Publisher HTTPS URL required: {key}")
    mcp = json.loads((root / "mcp.json").read_text())
    servers = mcp.get("mcpServers", {})
    if set(servers) != {"wisepim"}:
        raise ValueError("Exactly one WisePIM remote server is required")
    server = servers["wisepim"]
    if server.get("type") != "streamable-http" or server.get("url") != "https://wisepim.com/mcp":
        raise ValueError("MCP target must match the frontend service and OAuth audience")
    auth = server["extensions"]["com.openai"]["auth"]
    if auth.get("resource") != server["url"] or auth.get("type") != "oauth":
        raise ValueError("OAuth audience must match MCP URL")
    if auth.get("client", {}).get("mode") != "provided" or not auth["client"].get("clientId"):
        raise ValueError("This service requires a registered provided OAuth client")
    if any(key in json.dumps(mcp).lower() for key in ("clientsecret", "authorization\"", "bearer ")):
        raise ValueError("Credentials must not be packaged")
    lock = json.loads((root / "skills.lock.json").read_text())
    if lock.get("formatVersion") != 1 or lock.get("repository") != REPOSITORY:
        raise ValueError("Invalid skills provenance repository")
    if not preview and (lock.get("sourceDirty") or not re.fullmatch(r"[0-9a-f]{40}", lock.get("commit") or "")):
        raise ValueError("Release requires clean committed skill provenance")
    files = skill_files(root)
    if lock.get("files") != {rel: digest(data) for rel, data in files.items()}:
        raise ValueError("Vendored skills differ from the pinned source hashes")
    for rel in FIXED_FILES:
        path = root / rel
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Missing or unsafe package file: {rel}")
    return p, sorted((*FIXED_FILES, *files))


def build(root=ROOT, preview=False):
    manifest, files = check(root, preview)
    out = root / "dist"
    out.mkdir(exist_ok=True)
    suffix = "-preview" if preview else ""
    archive = out / f"wisepim-chatgpt-{manifest['version']}{suffix}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for rel in files:
            info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipf.writestr(info, (root / rel).read_bytes())
    (archive.with_suffix(".zip.sha256")).write_text(digest(archive.read_bytes()) + "  " + archive.name + "\n")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("sync", "check", "build", "configure-client"))
    parser.add_argument("--source", type=Path, default=ROOT.parent / "wisepim-skills")
    parser.add_argument("--allow-uncommitted", action="store_true", help="Preview sync only")
    parser.add_argument("--preview", action="store_true", help="Allow preview provenance for check/build")
    parser.add_argument("--client-id", help="Non-secret public OAuth client ID actually registered with WisePIM")
    args = parser.parse_args()
    try:
        if args.command == "configure-client":
            if not args.client_id or not re.fullmatch(r"[A-Za-z0-9._~:/-]{1,512}", args.client_id):
                raise ValueError("Supply the registered public --client-id")
            path = ROOT / "mcp.json"
            mcp = json.loads(path.read_text())
            mcp["mcpServers"]["wisepim"]["extensions"]["com.openai"]["auth"]["client"]["clientId"] = args.client_id
            path.write_text(json.dumps(mcp, indent=2) + "\n")
            print("Updated public client ID. Register its actual callback server-side before connecting.")
        elif args.command == "sync":
            sync(args.source, args.allow_uncommitted)
            print("Skills synchronized; run check/build (use --preview for uncommitted source).")
        elif args.command == "check":
            _, files = check(preview=args.preview)
            print(f"Validated {len(files)} public package files; deployment and portal review remain separate.")
        else:
            print(build(preview=args.preview))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Package error: {exc}\n")


if __name__ == "__main__":
    main()
