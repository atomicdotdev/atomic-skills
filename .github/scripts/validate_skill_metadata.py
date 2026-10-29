#!/usr/bin/env python3
"""Validate metadata for skills changed in a pull request."""

import calendar
from decimal import Decimal
import re
import subprocess
import sys

import yaml


SKILL_PATH = re.compile(r"skills/[^/]+/SKILL\.md\Z")
SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z"
)
TIMESTAMP = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T"
    r"([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]+))?"
    r"(Z|[+-][0-9]{2}:[0-9]{2})\Z"
)
FRONTMATTER = re.compile(r"\A---\s*\r?\n(.*?)^---\s*\r?\n", re.DOTALL | re.MULTILINE)


class ValidationError(Exception):
    """An invalid skill or an error retrieving repository data."""


def version(value):
    match = SEMVER.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValidationError("version must be a semantic version string")
    prerelease = match.group(4).split(".") if match.group(4) else None
    if prerelease and any(re.fullmatch(r"0[0-9]+", part) for part in prerelease):
        raise ValidationError("numeric prerelease identifiers cannot have leading zeroes")
    # Length plus lexical order compares arbitrary-size numeric identifiers
    # without Python's integer-string conversion limit.
    core = tuple((len(part), part) for part in match.group(1, 2, 3))
    return core, prerelease


def version_greater(current, previous):
    current_core, current_pre = version(current)
    previous_core, previous_pre = version(previous)
    if current_core != previous_core:
        return current_core > previous_core
    if current_pre is None:
        return previous_pre is not None
    if previous_pre is None:
        return False
    for left, right in zip(current_pre, previous_pre):
        if left == right:
            continue
        left_numeric, right_numeric = left.isdigit(), right.isdigit()
        if left_numeric != right_numeric:
            return not left_numeric
        return (len(left), left) > (len(right), right) if left_numeric else left > right
    return len(current_pre) > len(previous_pre)


def timestamp(value):
    match = TIMESTAMP.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValidationError("updatedAt must be an ISO 8601 timestamp string with a timezone")
    year, month, day, hour, minute, second = map(int, match.group(1, 2, 3, 4, 5, 6))
    zone = match.group(8)
    zone_hour = int(zone[1:3]) if zone != "Z" else 0
    zone_minute = int(zone[4:6]) if zone != "Z" else 0
    if not (1 <= month <= 12 and 1 <= day <= calendar.monthrange(year, month)[1]
            and hour < 24 and minute < 60 and second < 60
            and zone_hour < 24 and zone_minute < 60):
        raise ValidationError("updatedAt must be a valid ISO 8601 timestamp")

    # Compare UTC seconds and the exact decimal fraction separately: datetime's
    # microsecond resolution would silently lose precision beyond six digits.
    previous_year = year - 1
    days = 365 * previous_year + previous_year // 4 - previous_year // 100 + previous_year // 400
    days += sum(calendar.monthrange(year, m)[1] for m in range(1, month)) + day
    offset = (zone_hour * 60 + zone_minute) * 60
    if zone.startswith("-"):
        offset = -offset
    seconds = days * 86400 + hour * 3600 + minute * 60 + second - offset
    return seconds, Decimal("0." + (match.group(7) or "0"))


def frontmatter(content):
    match = FRONTMATTER.match(content)
    if not match:
        raise ValidationError("missing YAML frontmatter")
    return match.group(1)


def metadata(content, *, legacy=False):
    source = frontmatter(content)
    # Legacy files may have no metadata and even invalid unrelated YAML.
    if legacy and not re.search(r"^metadata\s*:", source, re.MULTILINE):
        return None
    try:
        data = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        raise ValidationError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError("frontmatter must be a mapping")
    result = data.get("metadata")
    if not isinstance(result, dict):
        raise ValidationError("metadata must be a mapping")
    version(result.get("version"))
    timestamp(result.get("updatedAt"))
    return result


def validate(current_content, base_content=None):
    current = metadata(current_content)
    base = metadata(base_content, legacy=True) if base_content is not None else None
    if base is None:
        return
    if not version_greater(current["version"], base["version"]):
        raise ValidationError(f"version must increase from {base['version']}")
    if timestamp(current["updatedAt"]) <= timestamp(base["updatedAt"]):
        raise ValidationError(f"updatedAt must be later than {base['updatedAt']}")


def changed_skills(diff):
    """Parse NUL-delimited git --name-status output, including renames."""
    fields = diff.split("\0")
    if fields[-1] == "":
        fields.pop()
    changes = []
    position = 0
    while position < len(fields):
        status = fields[position]
        position += 1
        if position >= len(fields):
            raise ValidationError("incomplete change list")
        old_path = fields[position]
        position += 1
        new_path = old_path
        if status.startswith(("R", "C")):
            if position >= len(fields):
                raise ValidationError("incomplete change list")
            new_path = fields[position]
            position += 1
        if status.startswith("D") or not SKILL_PATH.fullmatch(new_path):
            continue
        changes.append((new_path, old_path if SKILL_PATH.fullmatch(old_path) else new_path))
    return changes


class Repository:
    def run(self, *args):
        try:
            result = subprocess.run(
                ["git", *args], capture_output=True, text=True,
                encoding="utf-8", errors="surrogateescape", check=False,
            )
        except OSError as exc:
            raise ValidationError(f"git {args[0]} failed: {exc}") from exc
        if result.returncode:
            raise ValidationError(f"git {args[0]} failed: {result.stderr.strip()}")
        return result.stdout

    def changes(self, base, head):
        return changed_skills(self.run(
            "diff", "--name-status", "-z", "--find-renames", f"{base}...{head}", "--", "skills/"
        ))

    def content(self, revision, path):
        if not self.run("ls-tree", "-z", "--full-tree", revision, "--", path):
            return None
        return self.run("show", f"{revision}:{path}")


def check(repository, base, head, *, output=None, errors=None):
    output = output if output is not None else sys.stdout
    errors = errors if errors is not None else sys.stderr
    failures = []
    for path, old_path in repository.changes(base, head):
        try:
            current = repository.content(head, path)
            if current is None:
                raise ValidationError("skill is missing from the PR head")
            previous = repository.content(base, old_path)
            if previous is None and old_path != path:
                previous = repository.content(base, path)
            validate(current, previous)
            print(f"OK: {path}", file=output)
        except ValidationError as exc:
            failures.append(f"{path}: {exc}")
    for failure in failures:
        print(f"ERROR: {failure}", file=errors)
    return not failures


def main(args):
    try:
        if len(args) != 2 or not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in args):
            raise ValidationError("expected base and head commit SHAs")
        return 0 if check(Repository(), *args) else 1
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
