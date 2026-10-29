import io
import subprocess
import unittest
from unittest import mock

import validate_skill_metadata as validator


def skill(version="1.0.0", updated="2026-10-28T18:18:12Z"):
    return (
        '---\nname: example\ndescription: Example\nmetadata:\n'
        f'  version: "{version}"\n  updatedAt: "{updated}"\n---\n\n# Example\n'
    )


class FakeRepository:
    def __init__(self, changes, files):
        self._changes = changes
        self._files = files

    def changes(self, base, head):
        return self._changes

    def content(self, revision, path):
        return self._files.get((revision, path))


class SkillMetadataTest(unittest.TestCase):
    def test_new_skill_and_legacy_base(self):
        validator.validate(skill())
        validator.validate(skill(), "---\nname: old\ndescription: invalid: YAML\n---\n")

    def test_both_values_must_increase_for_existing_skill(self):
        base = skill()
        validator.validate(skill(version="1.0.1", updated="2026-10-28T19:18:12+00:00"), base)
        for current in (
            skill(updated="2026-10-29T00:00:00Z"),
            skill(version="1.0.1"),
            skill(version="0.9.9", updated="2026-10-29T00:00:00Z"),
            skill(version="1.0.1", updated="2026-10-28T14:18:12-04:00"),
        ):
            with self.subTest(current=current), self.assertRaises(validator.ValidationError):
                validator.validate(current, base)

    def test_semver_precedence(self):
        for current, previous in (
            ("1.0.0", "1.0.0-rc.1"),
            ("1.0.0-rc.10", "1.0.0-rc.2"),
            ("1.0.0-alpha.beta", "1.0.0-alpha.1"),
            ("1.0.0-alpha.1", "1.0.0-alpha"),
            ("2.0.0-rc.1", "1.99.99"),
        ):
            with self.subTest(current=current, previous=previous):
                self.assertTrue(validator.version_greater(current, previous))
        for current, previous in (
            ("1.0.0+new", "1.0.0+old"),
            ("1.0.0-alpha", "1.0.0"),
            ("1.0.0-alpha", "1.0.0-alpha.1"),
            ("1.0.0-alpha.1", "1.0.0-alpha.beta"),
        ):
            with self.subTest(current=current, previous=previous):
                self.assertFalse(validator.version_greater(current, previous))
        for invalid in ("1.0", "01.0.0", "1.0.0-01", "1.0.0+", 1.0):
            with self.subTest(invalid=invalid), self.assertRaises(validator.ValidationError):
                validator.version(invalid)
        self.assertTrue(validator.version_greater("9" * 5000 + ".0.0", "1.0.0"))
        self.assertTrue(validator.version_greater("1.0.0-" + "9" * 5000, "1.0.0-1"))

    def test_timestamp_precision_offsets_and_boundaries(self):
        self.assertGreater(validator.timestamp("2026-01-01T00:00:00.0000002Z"),
                           validator.timestamp("2026-01-01T00:00:00.0000001Z"))
        self.assertGreater(validator.timestamp("2026-01-01T00:00:00.0000000000000000000000000000000002Z"),
                           validator.timestamp("2026-01-01T00:00:00.0000000000000000000000000000000001Z"))
        self.assertEqual(validator.timestamp("2026-10-28T18:18:12Z"),
                         validator.timestamp("2026-10-28T14:18:12-04:00"))
        self.assertGreater(validator.timestamp("2027-01-01T00:00:00+01:00"),
                           validator.timestamp("2026-12-31T22:59:59Z"))
        self.assertGreater(validator.timestamp("0001-01-01T00:00:00Z"),
                           validator.timestamp("0000-12-31T23:59:59Z"))

    def test_invalid_frontmatter_or_metadata_fails(self):
        for content in (
            "", "---\nmetadata: [broken\n---\n", "---\nname: example\n---\n",
            skill(updated="2026-10-28"), skill(updated="bad"),
            skill(updated="2026-02-30T12:00:00Z"), skill(updated="2026-10-28T12:00:00+24:00"),
            skill().replace('"1.0.0"', '1.0'),
            skill().replace('"2026-10-28T18:18:12Z"', '2026-10-28T18:18:12Z'),
        ):
            with self.subTest(content=content), self.assertRaises(validator.ValidationError):
                validator.validate(content)
        with self.assertRaises(validator.ValidationError):
            validator.validate(skill(), "---\nmetadata:\n  version: broken\n---\n")

    def test_changed_skills_handles_renames_deletions_and_unrelated_paths(self):
        diff = "\0".join((
            "M", "skills/existing/SKILL.md",
            "A", "skills/new/SKILL.md",
            "R100", "skills/old/SKILL.md", "skills/renamed/SKILL.md",
            "D", "skills/deleted/SKILL.md",
            "M", "README.md",
            "M", "skills/existing/reference.md",
        )) + "\0"
        self.assertEqual(validator.changed_skills(diff), [
            ("skills/existing/SKILL.md", "skills/existing/SKILL.md"),
            ("skills/new/SKILL.md", "skills/new/SKILL.md"),
            ("skills/renamed/SKILL.md", "skills/old/SKILL.md"),
        ])
        self.assertEqual(validator.changed_skills(""), [])
        with self.assertRaises(validator.ValidationError):
            validator.changed_skills("R100\0old\0")

    def test_check_compares_renamed_skill_and_reports_all_failures(self):
        old_path = "skills/old/SKILL.md"
        new_path = "skills/new/SKILL.md"
        second_path = "skills/second/SKILL.md"
        repo = FakeRepository([(new_path, old_path), (second_path, second_path)], {
            ("base", old_path): skill(),
            ("head", new_path): skill(),
            ("head", second_path): "---\nname: missing\n---\n",
        })
        errors = io.StringIO()
        self.assertFalse(validator.check(repo, "base", "head", output=io.StringIO(), errors=errors))
        self.assertIn(f"{new_path}: version must increase", errors.getvalue())
        self.assertIn(f"{second_path}: metadata must be a mapping", errors.getvalue())

    def test_check_accepts_added_increased_and_no_changed_skills(self):
        path, added = "skills/one/SKILL.md", "skills/two/SKILL.md"
        repo = FakeRepository([(path, path), (added, added)], {
            ("base", path): skill(),
            ("head", path): skill(version="1.1.0", updated="2026-10-29T00:00:00Z"),
            ("head", added): skill(),
        })
        self.assertTrue(validator.check(repo, "base", "head", output=io.StringIO(), errors=io.StringIO()))
        self.assertTrue(validator.check(FakeRepository([], {}), "base", "head"))

    def test_repository_commands_are_used_to_find_and_read_changes(self):
        repository = validator.Repository()
        with mock.patch.object(repository, "run", side_effect=[
            "M\0skills/one/SKILL.md\0", "100644 blob abc\tskills/one/SKILL.md\0", "content",
        ]) as run:
            self.assertEqual(repository.changes("base", "head"), [("skills/one/SKILL.md", "skills/one/SKILL.md")])
            self.assertEqual(repository.content("base", "skills/one/SKILL.md"), "content")
            self.assertEqual(run.call_args_list[0], mock.call(
                "diff", "--name-status", "-z", "--find-renames", "base...head", "--", "skills/"))
            self.assertEqual(run.call_args_list[2], mock.call("show", "base:skills/one/SKILL.md"))

    def test_repository_failures_and_invalid_cli_arguments_fail(self):
        with mock.patch.object(validator.subprocess, "run", return_value=subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="unavailable"
        )):
            with self.assertRaisesRegex(validator.ValidationError, "git diff failed: unavailable"):
                validator.Repository().changes("base", "head")
        with mock.patch.object(validator.subprocess, "run", side_effect=FileNotFoundError("git not found")):
            with self.assertRaisesRegex(validator.ValidationError, "git diff failed"):
                validator.Repository().changes("base", "head")
        with mock.patch("sys.stderr", new_callable=io.StringIO) as errors:
            self.assertEqual(validator.main(["not-a-sha", "head"]), 1)
            self.assertIn("expected base and head commit SHAs", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
