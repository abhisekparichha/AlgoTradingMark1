#!/usr/bin/env bash
set -euo pipefail

# Cleans local artifact directories and regenerates them via the simulation workflow.
# Usage:
#   ./scripts/regenerate_artifacts.sh
#   DATA_ROOT=artifacts/data_repo ARTIFACT_DIR=artifacts/model_outputs ./scripts/regenerate_artifacts.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DATA_ROOT=${DATA_ROOT:-"artifacts/data_repo"}
ARTIFACT_DIR=${ARTIFACT_DIR:-"artifacts/model_outputs"}

echo "[regenerate_artifacts] Removing $DATA_ROOT and $ARTIFACT_DIR ..."
rm -rf "$DATA_ROOT" "$ARTIFACT_DIR"

echo "[regenerate_artifacts] Re-running simulation to recreate artifacts ..."
DATA_ROOT="$DATA_ROOT" ARTIFACT_DIR="$ARTIFACT_DIR" ./scripts/run_simulation.sh

echo "[regenerate_artifacts] Done."
