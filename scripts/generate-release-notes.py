#!/usr/bin/env python3
"""Generate structured GitHub Release notes from CHANGELOG.md.

Usage: python3 scripts/generate-release-notes.py <version> [prev_tag]

Output format matches the standard HA integration release style:
  ## Breaking changes / New features / Bug fixes / Improvements / Other changes
  with "- None" for empty sections and a Full Changelog link at the bottom.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Map CHANGELOG headers (emoji or text) to release note sections.
# Order matters — first match wins.
_HEADER_MAP: list[tuple[str, list[str]]] = [
    ("breaking", [r"Breaking", r"BREAKING"]),
    ("features", [r"New features", r"Added", r"\u2728"]),
    ("fixes", [r"Bug fixes", r"Fixed", r"\U0001f41b"]),
    ("improvements", [r"Improvements", r"Changed", r"\U0001f527"]),
]

# Anything not matched above goes into "other".
_OTHER_HEADERS = [r"Security", r"Removed", r"Documentation", r"\U0001f512", r"\U0001f4d6"]

_SECTION_TITLES = {
    "breaking": "\U0001f4a5 Breaking changes",
    "features": "\u2728 New features",
    "fixes": "\U0001f41b Bug fixes",
    "improvements": "\U0001f527 Improvements",
    "other": "\U0001f4e6 Other changes",
}


def _extract_version_section(changelog: str, version: str) -> str:
    """Extract the content between ## [version] and the next ## [."""
    pattern = rf"^## \[{re.escape(version)}\].*?\n(.*?)(?=^## \[|\Z)"
    m = re.search(pattern, changelog, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _classify_items(section_text: str) -> dict[str, list[str]]:
    """Parse CHANGELOG section into classified buckets."""
    buckets: dict[str, list[str]] = {
        "breaking": [],
        "features": [],
        "fixes": [],
        "improvements": [],
        "other": [],
    }

    current_bucket: str | None = None

    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this is a ### header line
        if stripped.startswith("### "):
            header_text = stripped[4:]
            current_bucket = None

            # Try main sections
            for bucket_key, patterns in _HEADER_MAP:
                for pat in patterns:
                    if re.search(pat, header_text, re.IGNORECASE):
                        current_bucket = bucket_key
                        break
                if current_bucket:
                    break

            # Try "other" sections
            if current_bucket is None:
                for pat in _OTHER_HEADERS:
                    if re.search(pat, header_text, re.IGNORECASE):
                        current_bucket = "other"
                        break

            # Fallback: unknown headers go to "other"
            if current_bucket is None:
                current_bucket = "other"
            continue

        # Collect list items (- or *) under current header
        if current_bucket and re.match(r"^[-*] ", stripped):
            buckets[current_bucket].append(stripped)

    return buckets


def _format_body(
    buckets: dict[str, list[str]],
    version: str,
    prev_tag: str,
    repo_url: str,
) -> str:
    """Format the release body in the standard style."""
    lines: list[str] = []

    for key in ("breaking", "features", "fixes", "improvements", "other"):
        title = _SECTION_TITLES[key]
        items = buckets.get(key, [])
        lines.append(f"## {title}")
        if items:
            lines.extend(items)
        else:
            lines.append("- None")
        lines.append("")

    # Full Changelog link
    if prev_tag:
        lines.append(f"Full Changelog: [CHANGELOG]({repo_url}/compare/{prev_tag}...v{version})")
    else:
        lines.append(f"Full Changelog: [CHANGELOG]({repo_url}/blob/main/CHANGELOG.md)")

    return "\n".join(lines)


def _detect_repo_url() -> str:
    """Detect repo URL from git remote origin."""
    import subprocess

    try:
        remote = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
        # Convert SSH to HTTPS format
        m = re.match(r"git@github\.com:(.+?)(?:\.git)?$", remote)
        if m:
            return f"https://github.com/{m.group(1)}"
        # Already HTTPS
        return remote.removesuffix(".git")
    except Exception:
        pass
    # Fallback: parse from CHANGELOG compare links
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"(https://github\.com/[^/]+/[^/\s\])]+)", changelog)
    if m:
        return m.group(1).rstrip("/")
    return "https://github.com/maximusIIxII/unknown"


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <version> [prev_tag]", file=sys.stderr)
        sys.exit(1)

    version = sys.argv[1]
    prev_tag = sys.argv[2] if len(sys.argv) > 2 else ""

    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    section = _extract_version_section(changelog, version)

    if not section:
        # Fallback: try [Unreleased] (for dry-run / preview)
        section = _extract_version_section(changelog, "Unreleased")

    buckets = _classify_items(section)
    repo_url = _detect_repo_url()
    body = _format_body(buckets, version, prev_tag, repo_url)
    sys.stdout.buffer.write(body.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
