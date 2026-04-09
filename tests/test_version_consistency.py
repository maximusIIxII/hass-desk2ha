"""Tests for version consistency across integration files.

Ensures manifest.json version has a matching CHANGELOG entry
and that version strings follow semver format.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "custom_components" / "desk2ha" / "manifest.json"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def test_manifest_version_is_semver():
    """manifest.json version must be valid semver (MAJOR.MINOR.PATCH)."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    version = manifest["version"]
    assert SEMVER_RE.match(version), (
        f"manifest.json version '{version}' is not valid semver (expected X.Y.Z)"
    )


def test_changelog_has_manifest_version():
    """CHANGELOG.md must contain an entry for the current manifest.json version."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    version = manifest["version"]
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    assert f"[{version}]" in changelog, (
        f"CHANGELOG.md has no entry for version {version}. "
        "Add a ## [{version}] section before releasing."
    )


def test_changelog_version_has_date():
    """The CHANGELOG entry for the current version must include a date."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    version = manifest["version"]
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    # Match pattern like: ## [0.8.5] - 2026-04-09
    pattern = rf"\[{re.escape(version)}\]\s*-\s*\d{{4}}-\d{{2}}-\d{{2}}"
    assert re.search(pattern, changelog), (
        f"CHANGELOG.md entry for [{version}] is missing a date "
        f"(expected format: ## [{version}] - YYYY-MM-DD)"
    )
