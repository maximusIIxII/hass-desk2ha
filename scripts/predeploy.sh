#!/usr/bin/env bash
# Predeploy checks for hass-desk2ha.
#
# Runs lint, tests, security-scan, and CHANGELOG preflight.
# Does NOT bump version, tag, or push.
#
# Used by: scripts/release-orchestrator.py (root). Can be run standalone.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "== [predeploy] hass-desk2ha =="

BRANCH=$(git branch --show-current || true)
if [[ -z "$BRANCH" ]]; then
    echo "[WARN] detached HEAD"
elif [[ "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
    echo "[WARN] on feature branch '$BRANCH'"
fi

if ! git diff --quiet HEAD 2>/dev/null; then
    echo "[FAIL] uncommitted changes in $REPO_ROOT"
    exit 1
fi

# CHANGELOG [Unreleased] check
if ! grep -qE '^## \[Unreleased\]|^## Unreleased' CHANGELOG.md 2>/dev/null; then
    echo "[FAIL] no [Unreleased] section in CHANGELOG.md"
    exit 1
fi

UNRELEASED=$(awk '/^## \[Unreleased\]/{f=1; next} /^## \[/{exit} f{print}' CHANGELOG.md)
if [[ -z "$(echo "$UNRELEASED" | tr -d '[:space:]')" ]]; then
    echo "[FAIL] [Unreleased] section is empty"
    exit 1
fi
echo "[OK] CHANGELOG has [Unreleased] content"

# Lint + format (limited scope)
if command -v ruff &>/dev/null; then
    ruff check custom_components/desk2ha tests || { echo "[FAIL] ruff check"; exit 1; }
    ruff format --check custom_components/desk2ha tests || { echo "[FAIL] ruff format"; exit 1; }
    echo "[OK] ruff"
else
    echo "[WARN] ruff not on PATH — skipping lint"
fi

# Tests
if command -v pytest &>/dev/null; then
    pytest tests/ -q --tb=short || { echo "[FAIL] pytest"; exit 1; }
    echo "[OK] pytest"
else
    echo "[WARN] pytest not on PATH — skipping tests"
fi

# Security scan (shared tool)
if [[ -f "../scripts/security-scan.py" ]]; then
    python3 ../scripts/security-scan.py . || { echo "[FAIL] security-scan"; exit 1; }
    echo "[OK] security-scan"
else
    echo "[WARN] ../scripts/security-scan.py not found — skipping"
fi

echo "[OK] predeploy clean"
