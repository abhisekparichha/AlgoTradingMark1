#!/usr/bin/env bash
set -euo pipefail

# Runs the end-to-end simulation/backtest workflow with research-friendly defaults.
# Generates synthetic data, shortlist, selection, trades, equity curve, diagnostics, and report.
#
# Usage:
#   ./scripts/run_simulation.sh
#   DATA_ROOT=/tmp/data ARTIFACT_DIR=/tmp/out SELECTION_MODE=random-sample ./scripts/run_simulation.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DATA_ROOT=${DATA_ROOT:-"artifacts/data_repo"}
ARTIFACT_DIR=${ARTIFACT_DIR:-"artifacts/model_outputs"}
SELECTION_MODE=${SELECTION_MODE:-"random-sample"}
SELECTION_K=${SELECTION_K:-2}
SHORTLIST_N=${SHORTLIST_N:-15}
ENTRY_THRESHOLD=${ENTRY_THRESHOLD:-0.7}
EXIT_THRESHOLD=${EXIT_THRESHOLD:-0.0}
TARGET_PCT=${TARGET_PCT:-0.03}
STOP_PCT=${STOP_PCT:-0.0125}
MAX_TOTAL_INVEST=${MAX_TOTAL_INVEST:-75000}
SIM_START=${SIM_START:-""}
SIM_END=${SIM_END:-""}

CMD=(python -m quant_india.cli.main run-objective
  --data-root "$DATA_ROOT"
  --model-artifact-dir "$ARTIFACT_DIR"
  --selection-mode "$SELECTION_MODE"
  --selection-k "$SELECTION_K"
  --shortlist-n "$SHORTLIST_N"
  --entry-threshold "$ENTRY_THRESHOLD"
  --exit-threshold "$EXIT_THRESHOLD"
  --target-pct "$TARGET_PCT"
  --stop-pct "$STOP_PCT"
  --max-total-invest "$MAX_TOTAL_INVEST"
)

if [ -n "$SIM_START" ]; then
  CMD+=(--sim-start "$SIM_START")
fi
if [ -n "$SIM_END" ]; then
  CMD+=(--sim-end "$SIM_END")
fi

echo "[run_simulation] Running objective pipeline with args:"
printf '  %q\n' "${CMD[@]}"
"${CMD[@]}"

echo "[run_simulation] Completed. Artifacts in $ARTIFACT_DIR"
