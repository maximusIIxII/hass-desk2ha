#!/usr/bin/env bash
set -euo pipefail

SPEC="../shared/openapi.yaml"
OUTPUT="custom_components/desk2ha/model.py"

datamodel-codegen \
  --input "$SPEC" \
  --input-file-type openapi \
  --output "$OUTPUT" \
  --output-model-type pydantic_v2.BaseModel \
  --use-standard-collections \
  --use-union-operator

echo "Generated $OUTPUT from $SPEC"
