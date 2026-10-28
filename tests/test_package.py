import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package", ROOT / "scripts/package.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "plugin"
        self.root.mkdir()
        for name in ("plugin.json", "mcp.json", "assets"):
            src = ROOT / name
            if src.is_dir():
                shutil.copytree(src, self.root / name)
            else:
                shutil.copy2(src, self.root / name)
        (self.root / "LICENSE").write_text("Synthetic test license\n")
        self.source = Path(self.temp.name) / "source"
        self.source.mkdir()
        for name in package.EXPECTED_SKILLS:
            path = self.source / "skills" / name / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(f"---\nname: {name}\ndescription: Synthetic test workflow.\n---\nUse explicit project identity.\n")
        self.git("init", "-q")
        self.git("add", "skills")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
        package.sync(self.source, root=self.root)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], stderr=subprocess.DEVNULL)

    def test_build_is_reproducible_and_allowlisted(self):
        (self.root / ".env").write_text("PRIVATE=do-not-distribute")
        (self.root / "reviewer-credentials.json").write_text("private fixture")
        archive = package.build(self.root)
        first = archive.read_bytes()
        self.assertEqual(first, package.build(self.root).read_bytes())
        with zipfile.ZipFile(archive) as z:
            self.assertNotIn(".env", z.namelist())
            self.assertNotIn("reviewer-credentials.json", z.namelist())
            self.assertIn("skills/catalog-quality-audit/SKILL.md", z.namelist())
            self.assertIn("mcp.json", z.namelist())
            self.assertTrue(all(not name.startswith("/") for name in z.namelist()))

    def test_rejects_tampered_vendored_skill(self):
        path = self.root / "skills/catalog-quality-audit/SKILL.md"
        path.write_text(path.read_text() + "tamper")
        with self.assertRaisesRegex(ValueError, "differ"):
            package.check(self.root)

    def test_rejects_dirty_source_for_release(self):
        (self.source / "private.txt").write_text("uncommitted")
        with self.assertRaisesRegex(ValueError, "clean committed"):
            package.sync(self.source, root=self.root)

    def test_preview_cannot_be_a_release(self):
        (self.source / "draft.txt").write_text("uncommitted")
        package.sync(self.source, allow_uncommitted=True, root=self.root)
        package.check(self.root, preview=True)
        with self.assertRaisesRegex(ValueError, "clean committed"):
            package.build(self.root)

    def test_rejects_symlinked_source(self):
        (self.source / "skills/catalog-quality-audit/linked.md").symlink_to(self.source / "skills/catalog-quality-audit/SKILL.md")
        with self.assertRaisesRegex(ValueError, "symlinks"):
            package.sync(self.source, allow_uncommitted=True, root=self.root)

    def test_rejects_unexpected_executable_skill_content(self):
        (self.source / "skills/catalog-quality-audit/run.py").write_text("print('no')")
        with self.assertRaisesRegex(ValueError, "Only Markdown"):
            package.sync(self.source, allow_uncommitted=True, root=self.root)

    def test_rejects_audience_mismatch(self):
        path = self.root / "mcp.json"
        mcp = json.loads(path.read_text())
        mcp["mcpServers"]["wisepim"]["extensions"]["com.openai"]["auth"]["resource"] = "https://other.invalid/mcp"
        path.write_text(json.dumps(mcp))
        with self.assertRaisesRegex(ValueError, "audience"):
            package.check(self.root)

    def test_requires_five_positive_three_negative_cases(self):
        path = self.root / "plugin.json"
        p = json.loads(path.read_text())
        p["extensions"]["com.openai"]["review"]["test_cases"]["positive"].pop()
        path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError, "exactly 5"):
            package.check(self.root)

    def test_rejects_hooks_for_directory_submission(self):
        path = self.root / "plugin.json"
        p = json.loads(path.read_text())
        p["extensions"]["com.openai"]["hooks"] = "./hooks/hooks.json"
        path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError, "lifecycle hooks"):
            package.check(self.root)

    def test_skill_source_commit_matches_lock(self):
        lock = json.loads((self.root / "skills.lock.json").read_text())
        self.assertEqual(lock["commit"], self.git("rev-parse", "HEAD").decode().strip())
        self.assertFalse(lock["sourceDirty"])

    def test_rejects_identical_source_before_reads_or_mutation(self):
        before = (self.root / "skills.lock.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            package.sync(self.root, allow_uncommitted=True, root=self.root)
        self.assertEqual(before, (self.root / "skills.lock.json").read_bytes())

    def test_rejects_parent_source_before_reads_or_mutation(self):
        before = (self.root / "skills.lock.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            package.sync(self.root.parent, allow_uncommitted=True, root=self.root)
        self.assertEqual(before, (self.root / "skills.lock.json").read_bytes())

    def test_rejects_child_source_and_preserves_canonical_inputs(self):
        nested = self.root / "skills" / "canonical-repository"
        nested.mkdir()
        sentinel = nested / "source.md"
        sentinel.write_text("Canonical source must survive")
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            package.sync(nested, allow_uncommitted=True, root=self.root)
        self.assertEqual("Canonical source must survive", sentinel.read_text())

    def test_rejects_alias_of_identical_source(self):
        alias = self.root.parent / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            package.sync(alias, allow_uncommitted=True, root=self.root)

    def test_rejects_symlinked_lock_without_writing_target(self):
        lock = self.root / "skills.lock.json"
        original = lock.read_bytes()
        outside = self.root.parent / "outside-lock.json"
        outside.write_bytes(original)
        lock.unlink()
        lock.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlinked skills lock"):
            package.sync(self.source, root=self.root)
        self.assertEqual(original, outside.read_bytes())

    def test_rejects_symlinked_asset_parent_even_within_root(self):
        (self.root / "assets").rename(self.root / "asset-source")
        (self.root / "assets").symlink_to(self.root / "asset-source", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "unsafe package file"):
            package.check(self.root)

    def test_rejects_symlinked_output_directory(self):
        outside = self.root.parent / "outside-output"
        outside.mkdir()
        (self.root / "dist").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinked output directory"):
            package.build(self.root)
        self.assertEqual([], list(outside.iterdir()))

    def test_rejects_symlinked_output_archive(self):
        out = self.root / "dist"
        out.mkdir()
        outside = self.root.parent / "outside.txt"
        outside.write_text("Keep this content")
        version = json.loads((self.root / "plugin.json").read_text())["version"]
        (out / f"wisepim-chatgpt-{version}.zip").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlinked output files"):
            package.build(self.root)
        self.assertEqual("Keep this content", outside.read_text())

    def test_rejects_subtitle_over_portal_limit(self):
        path = self.root / "plugin.json"
        p = json.loads(path.read_text())
        p["extensions"]["com.openai"]["interface"]["shortDescription"] = "x" * 31
        path.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError, "30 characters or fewer"):
            package.check(self.root)

    def test_accepts_subtitle_at_portal_limit(self):
        path = self.root / "plugin.json"
        p = json.loads(path.read_text())
        p["extensions"]["com.openai"]["interface"]["shortDescription"] = "x" * 30
        path.write_text(json.dumps(p))
        package.check(self.root)


if __name__ == "__main__":
    unittest.main()
