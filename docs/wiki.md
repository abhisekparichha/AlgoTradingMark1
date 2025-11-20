# Quant India Wiki

Comprehensive reference for setting up the environment, running the objective pipeline, and managing configurations across testing/trials and production execution.

---

## 1. Setup

1. **System requirements**
   - Python 3.10+ (repo currently tested on CPython 3.12)
   - `gcc`, `make`, and other build tools for scientific packages
   - Optional: access to `/data/quant-india` or equivalent durable storage

2. **Clone & install**
   ```bash
   git clone <repo-url> && cd quant-india
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```

3. **Environment variables**
   - `QUANT_INDIA_CONFIG` – optional override for `configs/base.yaml`
   - Data/API credentials (e.g., `KITE_API_KEY`) should be exported or sourced from a vault, never committed.

4. **Filesystem prep**
   ```bash
   mkdir -p artifacts/data_repo artifacts/model_outputs /data/quant-india/logs
   ```
   Adjust paths to match your environment; the objective pipeline accepts custom roots for data and artifacts.

5. **Smoke test**
   ```bash
   python -m quant_india.cli.main run-objective --data-root artifacts/data_repo \
     --model-artifact-dir artifacts/model_outputs --selection-mode random-sample --selection-k 1
   ```
   Confirm that `manifest_<date>.json`, shortlist/selection files, and trade logs are produced.

### 1.1 Data Acquisition Options

| Method | Command | Output location |
| --- | --- | --- |
| Synthetic generator (experiments) | `python -m quant_india.cli.main run-objective --data-root artifacts/data_repo ...` | `data_repo/raw/daily|intraday`, `meta/`, `corporate_actions/`, `embeddings/`, plus manifest |
| Zerodha Kite historical | `python -m quant_india.cli.main ingest-kite --symbols RELIANCE --start 2024-01-01T09:15 --end 2024-01-01T10:15 --interval 1m` | Partitioned parquet under `storage.raw_root` (see config) |
| NSE Bhavcopy | `python -m quant_india.cli.main ingest-nse --symbols SBIN --start 2024-01-01 --end 2024-01-31` | Daily EOD parquet partitions |
| Custom parquet | Place file at `data/your_prices.parquet` with `symbol,timestamp,open,high,low,close,volume` | Used directly by feature builder/backtester |

### 1.2 Model Creation & Training

1. Build features
   ```bash
   python -m quant_india.cli.main build-features --price-path data/your_prices.parquet
   ```
2. Train ensemble (cross-validation + fit)
   ```bash
   python -m quant_india.cli.main train-model \
     --price-path data/your_prices.parquet \
     --feature-paths data/features_return_1m.parquet data/features_volume_zscore.parquet \
     --horizon 5
   ```
   - Produces CV metrics and evaluation logs on stdout.
   - Extend `quant_india/models` to register additional estimators/pipelines if required.

### 1.3 Backtesting Choices

| Use case | Command | Outputs |
| --- | --- | --- |
| Feature-driven strategy backtest | `python -m quant_india.cli.main run-backtest --price-path ... --feature-path ...` | PnL parquet + metrics via `BacktestEngine` |
| End-to-end objective workflow | `python -m quant_india.cli.main run-objective --data-root ... --model-artifact-dir ...` | Manifest, shortlist, selection, trades, equity curve, diagnostics, backtest report |
| Custom strategy | Write a class in `quant_india/backtest/strategies` implementing `generate_signals`, then call `BacktestEngine` (CLI/notebook) | Controlled entry/exit logic with same cost model |

---

## 2. Objective Pipeline Reference

| Flag | Description | Default |
| --- | --- | --- |
| `--data-root` | Destination for generated raw/meta/corporate/embedding data | `artifacts/data_repo` |
| `--model-artifact-dir` | Output directory for shortlist/trades/diagnostics | `artifacts/model_outputs` |
| `--selection-mode` | `signal-rank`, `random-sample`, or `user-defined` | `signal-rank` |
| `--selection-k` | Number of tickers to trade | 3 |
| `--max-total-invest` | Capital cap across concurrent positions (INR) | 100000 |
| `--entry-threshold`, `--exit-threshold` | Signal bands for entries/exits | 0.6 / -0.2 |
| `--target-pct`, `--stop-pct` | Take-profit / stop-loss percentages | 0.03 / 0.015 |
| `--sim-start`, `--sim-end` | Explicit UTC window (ISO format) | last 6 months |

Artifacts generated per run:

- `manifest_<date>.json` – dataset inventory with SHA256 hashes
- `shortlist_<date>.csv` – liquidity/vol/momentum/stability scores
- `selection_<date>.json` – tickers, lot sizes, capital allocation
- `trades_<date>.csv`, `equity_curve_<date>.csv` – execution log and NAV
- `diagnostics_<date>.json` – signal IC, slippage spikes, adverse trades
- `backtest_report_<date>.json` – metrics (PnL, ROIC, Sharpe, grid search)

---

## 3. Configurations for Testing & Trials

Goal: rapid iteration, low runtime, randomized coverage.

- **Paths**: keep `--data-root` and `--model-artifact-dir` inside `artifacts/` so runs are disposable.
- **Universe control**:
  - Reduce shortlist size: `--shortlist-n 10`
  - Provide explicit tickers: `--custom-ticker-list TCS INFY SBIN`
- **Selection diversity**: use `--selection-mode random-sample --selection-k 2` with a fixed `--selection-seed` for reproducibility.
- **Tighter risk envelope**:
  - `--entry-threshold 0.8` or greater to cut noise
  - `--stop-pct 0.01` and `--max-holding-minutes 60` for fast turnover
  - Lower `--max-total-invest` (e.g., 25_000) when exploring edge cases
- **Diagnostics focus**:
  - Inspect `diagnostics_*.json` for IC, slippage, and adverse trades
  - Track `grid_search` variants in `backtest_report_*.json` to prune parameter ranges before full-scale runs
- **Automation tip**: wrap the command in a shell script that sweeps seeds/thresholds and stores outputs under `artifacts/trials/<param-set>/`.

---

## 4. Configurations for Production Execution & Feedback

### Production posture

- **Durable storage**: point roots to `/data/quant-india/<env>/...` or cloud mounts; ensure run users have write permissions.
- **Deterministic selection**: stick with `signal-rank`, optionally provide curated lists via `--custom-ticker-list` to enforce compliance and borrow limits.
- **Capital controls**: align `--max-total-invest`, `--selection-k`, and lot sizing policy with risk rules; document overrides in the debug log.
- **Extended history**: leave `--shortlist-n` at 30+ to maintain breadth; keep `--intraday-lookback-days` at 252 for realistic covariance.
- **Audit artifacts**: archive manifests, selection JSON, trade logs, diagnostics, and backtest reports to immutable storage each run.

### Feedback & continuous improvement

1. **Artifact review**
   - `backtest_report_<date>.json` ➜ monitor net/gross PnL, max drawdown, return on invested capital, and parameter grid results.
   - `diagnostics_<date>.json` ➜ check mean/median IC, slippage spikes (>30 bps), and list of adverse trades (>3σ losses).
   - `trades_<date>.csv` ➜ validate compliance with lot/tick sizes and confirm total exposure never exceeded cap.
2. **Parameter tuning loop**
   - Adjust thresholds (`entry`, `exit`, `stop`, `target`) and rerun on overlapping windows.
   - Compare random seeds or selection modes to detect concentration risk.
   - Feed diagnostics into model-finetuning jobs (e.g., update feature weights or execution overlays).
3. **Production gating**
   - Require stable IC (positive mean/median) and acceptable Sharpe before promoting configs.
   - Capture execution logs from the live venue and replace the default slippage model when available.
4. **Feedback channels**
   - Log issues (`allocation_error.json`, `data_error.json`) and remediate before next cycle.
   - Summarize findings in the runbook or monitoring dashboard for stakeholder review.

---

## 5. Troubleshooting

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| `allocation_error.json` emitted | Capital cap too low for selected symbols | Increase `--max-total-invest`, reduce `--selection-k`, or include lower-priced tickers. |
| Empty shortlist | Liquidity/volume filters too strict | Lower `--min-adv-inr`, `--min-daily-vol`, or expand universe. |
| `pandas` timezone errors | Naive datetime passed to `--sim-start/--sim-end` with local tz assumption | Provide explicit `Z` suffix or ISO timestamp with offset. |
| High slippage warnings | Large spreads on selected symbols | Reduce `--max-spread-pct`, increase liquidity threshold, or integrate real execution logs. |

For additional operational notes, cross-reference `docs/runbook.md` and the repository README.

