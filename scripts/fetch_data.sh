#!/usr/bin/env bash
set -euo pipefail

# Pulls historical data (NSE daily + Kite intraday) for the symbols specified.
# Requires valid Zerodha credentials in the environment/config for the Kite ingestion.
#
# Usage:
#   SYMBOLS="RELIANCE,TCS" START_DATE=2024-01-01 END_DATE=2024-01-31 \
#     INTRADAY_START="2024-01-01T09:15" INTRADAY_END="2024-01-01T15:30" \
#     ./scripts/fetch_data.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SYMBOLS=${SYMBOLS:-"RELIANCE,TCS,INFY"}
START_DATE=${START_DATE:-"2024-01-01"}
END_DATE=${END_DATE:-"2024-01-31"}
INTRADAY_START=${INTRADAY_START:-"2024-01-01T09:15"}
INTRADAY_END=${INTRADAY_END:-"2024-01-01T15:30"}
INTRADAY_INTERVAL=${INTRADAY_INTERVAL:-"1m"}

IFS=',' read -r -a SYMBOL_ARRAY <<< "$SYMBOLS"
SYMBOL_ARGS=()
for sym in "${SYMBOL_ARRAY[@]}"; do
  SYMBOL_ARGS+=("--symbols" "$sym")
done

echo "[fetch_data] Pulling NSE bhavcopy data..."
python -m quant_india.cli.main ingest-nse \
  --start "$START_DATE" \
  --end "$END_DATE" \
  "${SYMBOL_ARGS[@]}"

echo "[fetch_data] Pulling Kite intraday data..."
python -m quant_india.cli.main ingest-kite \
  --start "$INTRADAY_START" \
  --end "$INTRADAY_END" \
  --interval "$INTRADAY_INTERVAL" \
  "${SYMBOL_ARGS[@]}"

echo "[fetch_data] Data ingestion complete."
