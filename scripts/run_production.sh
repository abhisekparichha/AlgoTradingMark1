#!/usr/bin/env bash
set -euo pipefail

# Runs the objective pipeline with production-oriented defaults:
# - Deterministic selection (signal-rank or user-defined tickers)
# - Higher capital cap and configurable ticker whitelist
# - Durable data/artifact directories (override via env)
#
# Usage:
#   ./scripts/run_production.sh
#   MAX_TOTAL_INVEST=200000 CUSTOM_TICKERS="RELIANCE,TCS" ./scripts/run_production.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DATA_ROOT=${DATA_ROOT:-"/data/quant-india/prod/data_repo"}
ARTIFACT_DIR=${ARTIFACT_DIR:-"/data/quant-india/prod/model_outputs"}
MAX_TOTAL_INVEST=${MAX_TOTAL_INVEST:-150000}
SHORTLIST_N=${SHORTLIST_N:-30}
SELECTION_MODE=${SELECTION_MODE:-"signal-rank"}
SELECTION_K=${SELECTION_K:-3}
ENTRY_THRESHOLD=${ENTRY_THRESHOLD:-0.6}
EXIT_THRESHOLD=${EXIT_THRESHOLD:--0.2}
TARGET_PCT=${TARGET_PCT:-0.025}
STOP_PCT=${STOP_PCT:-0.012}
SIM_START=${SIM_START:-""}
SIM_END=${SIM_END:-""}
CUSTOM_TICKERS=${CUSTOM_TICKERS:-""}

CMD=(python -m quant_india.cli.main run-objective
  --data-root "$DATA_ROOT"
  --model-artifact-dir "$ARTIFACT_DIR"
  --max-total-invest "$MAX_TOTAL_INVEST"
  --shortlist-n "$SHORTLIST_N"
  --selection-mode "$SELECTION_MODE"
  --selection-k "$SELECTION_K"
  --entry-threshold "$ENTRY_THRESHOLD"
  --exit-threshold "$EXIT_THRESHOLD"
  --target-pct "$TARGET_PCT"
  --stop-pct "$STOP_PCT"
)

if [ -n "$SIM_START" ]; then
  CMD+=(--sim-start "$SIM_START")
fi
if [ -n "$SIM_END" ]; then
  CMD+=(--sim-end "$SIM_END")
fi

if [ -n "$CUSTOM_TICKERS" ]; then
  IFS=',' read -r -a TICKER_ARRAY <<< "$CUSTOM_TICKERS"
  for ticker in "${TICKER_ARRAY[@]}"; do
    CMD+=(--custom-ticker-list "$ticker")
  done
fi

mkdir -p "$DATA_ROOT" "$ARTIFACT_DIR"

echo "[run_production] Executing production run with args:"
printf '  %q\n' "${CMD[@]}"
"${CMD[@]}"

echo "[run_production] Completed. Review artifacts in $ARTIFACT_DIR"
