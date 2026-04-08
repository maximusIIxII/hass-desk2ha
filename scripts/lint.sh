#!/usr/bin/env bash
set -euo pipefail

echo "=== ruff check ==="
ruff check .

echo "=== ruff format ==="
ruff format --check .

echo "=== mypy ==="
mypy custom_components/desk2ha/

echo "=== pytest ==="
pytest tests/ -x --tb=short

echo "All checks passed"
