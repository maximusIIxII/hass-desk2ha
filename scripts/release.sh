#!/usr/bin/env bash
# Deprecated thin wrapper — delegates to release-orchestrator.py.
#
# History: this script used to do lint+tests+security+tag+push in one shot.
# That allowed tagged releases to ship with broken Live deploys. The new
# orchestrator enforces deploy-first: staging deploy + live verify happens
# BEFORE any tag is created.
#
# Usage:
#   ./scripts/release.sh              # auto-detect bump
#   ./scripts/release.sh patch
#   ./scripts/release.sh 1.3.0
#
# To release both agent + integration together (recommended):
#   python3 ../scripts/release-orchestrator.py [bump]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ORCHESTRATOR="$REPO_ROOT/../scripts/release-orchestrator.py"

echo "[DEPRECATION] release.sh is a thin wrapper around release-orchestrator.py."
echo "  The orchestrator enforces deploy-first (staging deploy + live verify"
echo "  before tag/push). Directly calling publish.sh bypasses verification."
echo ""

if [[ -f "$ORCHESTRATOR" ]]; then
    echo "Delegating to orchestrator: $ORCHESTRATOR --integration $*"
    exec python3 "$ORCHESTRATOR" --integration "$@"
fi

echo "[WARN] Orchestrator not found at $ORCHESTRATOR"
echo "[WARN] Falling back to legacy path: predeploy + publish (no live verify)"
echo ""

bash "$SCRIPT_DIR/predeploy.sh"
bash "$SCRIPT_DIR/publish.sh" "$@"
