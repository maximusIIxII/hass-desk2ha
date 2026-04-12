#!/usr/bin/env bash
# Release script for hass-desk2ha
#
# Usage:
#   ./scripts/release.sh              # auto-detect bump type, interactive
#   ./scripts/release.sh patch         # force patch release (x.y.Z)
#   ./scripts/release.sh minor         # force minor release (x.Y.0)
#   ./scripts/release.sh major         # force major release (X.0.0)
#   ./scripts/release.sh 1.2.3         # explicit version
#
# Workflow:
#   1. Reads [Unreleased] from CHANGELOG.md
#   2. Auto-detects bump type from section headers:
#      - ### Breaking → major
#      - ### Added / ### ✨ New features → minor
#      - ### Changed / ### Fixed / ### 🐛 Bug fixes → patch
#   3. Shows changes and suggested version, asks for confirmation
#   4. Bumps manifest.json, updates CHANGELOG, commits, tags, pushes
#   5. release.yml workflow creates GitHub Release + HACS zip automatically

set -euo pipefail

REPO_NAME="hass-desk2ha"
REPO_URL="https://github.com/maximusIIxII/hass-desk2ha"
VERSION_FILE="custom_components/desk2ha/manifest.json"

# ── Helpers ──────────────────────────────────────────────────────

get_current_version() {
    python3 -c "import json; print(json.load(open('$VERSION_FILE'))['version'])"
}

set_version() {
    python3 -c "
import json
with open('$VERSION_FILE', 'r') as f:
    m = json.load(f)
m['version'] = '$1'
with open('$VERSION_FILE', 'w') as f:
    json.dump(m, f, indent=2)
    f.write('\n')
"
}

bump_version() {
    local current="$1" type="$2"
    IFS='.' read -r major minor patch <<< "$current"
    case "$type" in
        major) echo "$((major + 1)).0.0" ;;
        minor) echo "${major}.$((minor + 1)).0" ;;
        patch) echo "${major}.${minor}.$((patch + 1))" ;;
    esac
}

# ── Preflight checks ────────────────────────────────────────────

BRANCH=$(git branch --show-current)
if [[ "$BRANCH" != "master" && "$BRANCH" != "main" ]]; then
    echo "Error: must be on master/main (currently on $BRANCH)"
    exit 1
fi

if ! git diff --quiet HEAD 2>/dev/null; then
    echo "Error: uncommitted changes. Commit or stash first."
    exit 1
fi

git pull --ff-only origin "$BRANCH"

if ! grep -q '## \[Unreleased\]' CHANGELOG.md 2>/dev/null; then
    if ! grep -qE '## \[Unreleased\]|## Unreleased' CHANGELOG.md 2>/dev/null; then
        echo "Error: no [Unreleased] section in CHANGELOG.md"
        exit 1
    fi
fi

UNRELEASED=$(awk '/^## \[Unreleased\]/{found=1; next} /^## \[/{exit} found{print}' CHANGELOG.md)
if [[ -z "$(echo "$UNRELEASED" | tr -d '[:space:]')" ]]; then
    echo "Error: [Unreleased] section in CHANGELOG.md is empty."
    echo "Add your changes there before releasing."
    exit 1
fi

# ── Run pre-release checks ───────────────────────────────────────

echo "Running lint + tests..."
if command -v ruff &>/dev/null; then
    ruff check custom_components/desk2ha tests || { echo "Error: ruff lint failed"; exit 1; }
    ruff format --check custom_components/desk2ha tests || { echo "Error: ruff format failed"; exit 1; }
fi
if command -v pytest &>/dev/null; then
    pytest tests/ -q || { echo "Error: tests failed"; exit 1; }
fi
echo "[OK] Lint + tests passed"

# ── Run security scan ────────────────────────────────────────────

if [[ -f "../scripts/security-scan.py" ]]; then
    echo "Running security scan..."
    python3 ../scripts/security-scan.py . || { echo "Error: security scan failed"; exit 1; }
    echo "[OK] Security scan passed"
fi

# ── Check agent version on PyPI ──────────────────────────────────

AGENT_VERSION=$(pip index versions desk2ha-agent 2>/dev/null | head -1 | grep -oP '\([\d.]+\)' | tr -d '()') || true
if [[ -n "$AGENT_VERSION" ]]; then
    echo "Latest desk2ha-agent on PyPI: v$AGENT_VERSION"
fi

# ── Detect bump type from CHANGELOG sections ────────────────────

CURRENT=$(get_current_version)

HAS_BREAKING=$(echo "$UNRELEASED" | grep -c '^### Breaking' || true)
HAS_ADDED=$(echo "$UNRELEASED" | grep -cE '^### (Added|✨)' || true)
HAS_CHANGED=$(echo "$UNRELEASED" | grep -cE '^### (Changed|🔧)' || true)
HAS_FIXED=$(echo "$UNRELEASED" | grep -cE '^### (Fixed|🐛)' || true)
HAS_REMOVED=$(echo "$UNRELEASED" | grep -c '^### Removed' || true)
HAS_SECURITY=$(echo "$UNRELEASED" | grep -cE '^### (Security|🔒)' || true)

if [[ "$HAS_BREAKING" -gt 0 ]]; then
    AUTO_TYPE="major"
elif [[ "$HAS_ADDED" -gt 0 ]]; then
    AUTO_TYPE="minor"
else
    AUTO_TYPE="patch"
fi

AUTO_VERSION=$(bump_version "$CURRENT" "$AUTO_TYPE")

# ── Parse argument ──────────────────────────────────────────────

ARG="${1:-}"

if [[ -z "$ARG" ]]; then
    VERSION="$AUTO_VERSION"
    BUMP_TYPE="$AUTO_TYPE"
elif [[ "$ARG" == "major" || "$ARG" == "minor" || "$ARG" == "patch" ]]; then
    BUMP_TYPE="$ARG"
    VERSION=$(bump_version "$CURRENT" "$BUMP_TYPE")
elif [[ "$ARG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    VERSION="$ARG"
    IFS='.' read -r cmaj cmin cpat <<< "$CURRENT"
    IFS='.' read -r nmaj nmin npat <<< "$VERSION"
    if [[ "$nmaj" -gt "$cmaj" ]]; then BUMP_TYPE="major"
    elif [[ "$nmin" -gt "$cmin" ]]; then BUMP_TYPE="minor"
    else BUMP_TYPE="patch"; fi
else
    echo "Usage: $0 [patch|minor|major|x.y.z]"
    exit 1
fi

if [[ "$BUMP_TYPE" == "patch" && "$HAS_BREAKING" -gt 0 ]]; then
    echo "WARNING: [Unreleased] contains ### Breaking changes but you chose patch!"
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo ""
    [[ $REPLY =~ ^[Yy]$ ]] || exit 0
fi

if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Error: tag v$VERSION already exists"
    exit 1
fi

# ── Show summary and confirm ────────────────────────────────────

echo ""
echo "  Release: $REPO_NAME v$VERSION ($BUMP_TYPE)"
echo "  Current: v$CURRENT"
echo "  ────────────────────────────────────────"
echo ""

if [[ "$HAS_BREAKING" -gt 0 ]]; then echo "  BREAKING CHANGES:"; echo "$UNRELEASED" | awk '/^### Breaking/{f=1;next}/^### /{f=0}f' | head -10 | sed 's/^/    /'; echo ""; fi
if [[ "$HAS_ADDED" -gt 0 ]]; then echo "  NEW FEATURES:"; echo "$UNRELEASED" | awk '/^### (Added|✨)/{f=1;next}/^### /{f=0}f' | head -10 | sed 's/^/    /'; echo ""; fi
if [[ "$HAS_CHANGED" -gt 0 ]]; then echo "  CHANGES:"; echo "$UNRELEASED" | awk '/^### (Changed|🔧)/{f=1;next}/^### /{f=0}f' | head -10 | sed 's/^/    /'; echo ""; fi
if [[ "$HAS_FIXED" -gt 0 ]]; then echo "  FIXES:"; echo "$UNRELEASED" | awk '/^### (Fixed|🐛)/{f=1;next}/^### /{f=0}f' | head -10 | sed 's/^/    /'; echo ""; fi
if [[ "$HAS_SECURITY" -gt 0 ]]; then echo "  SECURITY:"; echo "$UNRELEASED" | awk '/^### (Security|🔒)/{f=1;next}/^### /{f=0}f' | head -10 | sed 's/^/    /'; echo ""; fi
if [[ "$HAS_REMOVED" -gt 0 ]]; then echo "  REMOVED:"; echo "$UNRELEASED" | awk '/^### Removed/{f=1;next}/^### /{f=0}f' | head -10 | sed 's/^/    /'; echo ""; fi

echo "  Suggested: v$AUTO_VERSION ($AUTO_TYPE) based on CHANGELOG sections"
if [[ -n "${AGENT_VERSION:-}" ]]; then
    echo "  Agent:     v$AGENT_VERSION (PyPI)"
fi
echo ""

read -p "Release v$VERSION? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# ── Execute release ─────────────────────────────────────────────

set_version "$VERSION"
echo "[OK] $VERSION_FILE -> $VERSION"

DATE=$(date +%Y-%m-%d)
sed -i "s/^## \[Unreleased\]/## [Unreleased]\n\n## [$VERSION] - $DATE/" CHANGELOG.md

PREV_VERSION=$(grep -oP '^\## \[\K[\d.]+' CHANGELOG.md | head -2 | tail -1)
if [[ -n "$PREV_VERSION" ]]; then
    if grep -q "^\[${PREV_VERSION}\]:" CHANGELOG.md; then
        sed -i "/^\[${PREV_VERSION}\]:/i [$VERSION]: $REPO_URL/compare/v${PREV_VERSION}...v$VERSION" CHANGELOG.md
    fi
fi
echo "[OK] CHANGELOG.md updated"

git add "$VERSION_FILE" CHANGELOG.md
git commit -m "release: v$VERSION"
git tag "v$VERSION"
echo "[OK] Committed and tagged v$VERSION"

git push origin "$BRANCH" --tags
echo "[OK] Pushed to origin"

echo ""
echo "Release workflow triggered. Monitor:"
echo "  gh run list --repo $REPO_URL --limit 3"
echo "  gh run watch --repo $REPO_URL"
