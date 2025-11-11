#!/usr/bin/env bash
set -euo pipefail

python3 -m quant_india.cli.main ingest-kite --symbols RELIANCE \
  --start 2024-01-01T09:15 --end 2024-01-01T10:15 --interval 1m

python3 -m quant_india.cli.main build-features --price-path data/sample_prices.parquet

python3 -m quant_india.cli.main run-backtest \
  --price-path data/sample_prices.parquet \
  --feature-path data/features_mean_reversion.parquet \
  --output-path artifacts/backtest.parquet
