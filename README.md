# Quant India Trading System

End-to-end quant trading stack for Indian equities and derivatives with Zerodha Kite Connect integration. Includes ingestion, feature engineering, ensemble modelling, backtesting with India-specific cost model, and live execution controls.

## Repository Layout

```
.
├── configs/             # Base configuration (storage, API keys placeholders)
├── docs/                # Data catalogue, architecture diagram, runbook
├── quant_india/
│   ├── common/          # Settings, logging, IO utilities
│   ├── data/            # Ingestion jobs (Kite, NSE, News), schemas, quality checks
│   ├── features/        # Feature registry, builder, feature store API
│   ├── models/          # Dataset assembly, ensemble pipelines, walk-forward
│   ├── backtest/        # Cost models, engine, mean-reversion strategy
│   ├── executor/        # Zerodha executor, simulator, risk manager
│   ├── nlp/             # News sentiment, event classification, entity linking
│   ├── monitoring/      # Reporting and Streamlit dashboard stub
│   └── cli/             # Typer CLI entrypoints
├── scripts/             # Helper scripts (extend as needed)
└── tests/               # Pytest suites for ingestion & model pipelines
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run sample ingestion (simulated if credentials absent):

```bash
python -m quant_india.cli.main ingest-kite --symbols RELIANCE \
  --start 2024-01-01T09:15 --end 2024-01-01T10:15 --interval 1m
```

Build features and run backtest:

```bash
python -m quant_india.cli.main build-features --price-path data/sample_prices.parquet
python -m quant_india.cli.main run-backtest \
  --price-path data/sample_prices.parquet \
  --feature-path data/features_mean_reversion.parquet
```

Train the ensemble model:

```bash
python -m quant_india.cli.main train-model \
  --price-path data/sample_prices.parquet \
  --feature-paths data/features_return_1m.parquet data/features_volume_zscore.parquet \
  --horizon 5
```

Generate monitoring report:

```bash
python -m quant_india.cli.main report --pnl-path artifacts/backtest.parquet
```

## Objective Pipeline (Data ➜ Shortlist ➜ Simulation)

Use the `run-objective` command to stand up a synthetic data repository, shortlist tradable stocks, size positions under ₹100k, and backtest model-driven entries/exits in a single pass.

### Installation & Environment Setup

1. Clone and create a virtualenv
   ```bash
   git clone <repo-url> && cd quant-india
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```
2. (Optional) Create persistent storage locations
   ```bash
   mkdir -p /data/quant-india/raw /data/quant-india/processed artifacts/data_repo artifacts/model_outputs
   ```
3. Configure `QUANT_INDIA_CONFIG` or export API keys if you plan to use real feeds (see docs/wiki.md §4).

### Pulling Data

| Method | Command | Notes |
| --- | --- | --- |
| **Synthetic repo (for experiments)** | `python -m quant_india.cli.main run-objective --data-root artifacts/data_repo ...` | Builds 5y daily + 1y intraday parquet, holiday calendar, corporate actions, embeddings, manifest. |
| **Kite historical** | `python -m quant_india.cli.main ingest-kite --symbols RELIANCE --start ... --end ...` | Uses Zerodha API credentials from config/env; stores parquet under `storage.raw_root`. |
| **NSE bhavcopy** | `python -m quant_india.cli.main ingest-nse --symbols SBIN --start 2024-01-01 --end 2024-01-31` | Daily EOD data (CSV/zip) → partitioned parquet. |
| **Custom historical parquet** | Place file at `data/your_prices.parquet` with `symbol,timestamp,open,high,low,close,volume`. | Compatible with feature builder/backtester. |

### Creating & Training Models

1. Build features from your price file:
   ```bash
   python -m quant_india.cli.main build-features --price-path data/your_prices.parquet
   ```
2. Assemble datasets + train ensemble:
   ```bash
   python -m quant_india.cli.main train-model \
     --price-path data/your_prices.parquet \
     --feature-paths data/features_return_1m.parquet data/features_volume_zscore.parquet \
     --horizon 5
   ```
   - Produces cross-validation metrics and in-sample evaluation.
   - Extend the pipeline in `quant_india/models` for transformer/XGBoost hybrids as needed.

### Backtesting Options

| Use case | Command | Output |
| --- | --- | --- |
| **Classical feature-driven backtest** | `python -m quant_india.cli.main run-backtest --price-path ... --feature-path ...` | PnL parquet + metrics from `MeanReversionStrategy` via `BacktestEngine`. |
| **End-to-end objective workflow** | `python -m quant_india.cli.main run-objective --data-root ... --model-artifact-dir ...` | Manifests, shortlist, selection, trades, equity curve, diagnostics, backtest report. |
| **Custom strategy** | Implement `generate_signals` in `quant_india/backtest/strategies` and wire into CLI or notebook. | Use `BacktestEngine` with realistic cost model (brokerage/stamp duty/slippage). |

### Run the full workflow

```bash
python -m quant_india.cli.main run-objective \
  --data-root artifacts/data_repo \
  --model-artifact-dir artifacts/model_outputs \
  --selection-mode signal-rank \
  --selection-k 3 \
  --entry-threshold 0.6 \
  --stop-pct 0.015
```

- **Data repository** (`--data-root`): generates `raw/daily`, `raw/intraday`, `meta/`, `corporate_actions/`, and `embeddings/` along with `manifest_<date>.json` capturing row counts, timestamps, and SHA256 hashes.
- **Artifacts** (`--model-artifact-dir`): `shortlist_<date>.csv`, `selection_<date>.json`, `trades_<date>.csv`, `equity_curve_<date>.csv`, `diagnostics_<date>.json`, `backtest_report_<date>.json`, and `debug_<date>.log`.
- **Window**: defaults to the last six months; override via `--sim-start`/`--sim-end` (ISO timestamps, assumed UTC if tz-naive).
- **Constraints**: capital capped by `--max-total-invest` (₹100k by default); lot sizes respect NSE conventions (≥1 lot even for high-priced names).

### Configuration cheat sheet

| Scenario | Recommended switches | Notes |
| --- | --- | --- |
| **Testing & trials** | `--selection-mode random-sample`, `--selection-k 2`, `--shortlist-n 10`, `--max-holding-minutes 60`, higher `--entry-threshold` (e.g., 0.8) | Keeps runtime low, stresses robustness across random tickers, and tightens exposure windows. |
| **Production execution** | Deterministic `signal-rank`, curated `--custom-ticker-list` or larger shortlist, durable paths (e.g., `/data/quant-india/...`), audited `--max-total-invest` | Archive manifest/selection/trades/diagnostics after every run; align thresholds and stop/target levels with live risk policy. |
| **Feedback & tuning** | Adjust `--entry-threshold`, `--stop-pct`, `--target-pct`, seed variations, and analyze `diagnostics_*.json` | Track IC stability, slippage spikes, and adverse trades to drive fine-tuning across rolling windows. |

See `docs/wiki.md` for a deeper setup guide, environment matrix (trial vs production), and the feedback loop that turns these artifacts into parameter updates.

## Key Modules

- **Ingestion**: Jobs for Kite REST/WebSocket, NSE bhavcopy & option chain, NewsAPI, TrueData (placeholder). Columnar Parquet storage with IST partitions and quality checks for completeness & price sanity.
- **Feature Store**: 20+ intraday, cross-sectional, derivative, and news-driven features (VWAP deviation, volume z-score, news_shock, IV skew, etc.) saved under `/data/feature-store/<feature>/`.
- **NLP Pipeline**: Sentiment scoring, event classification, and entity linking to map news to symbols; produces `news_shock` risk gate.
- **Models**: Ensemble of XGBoost regressor and LSTM skeleton with time-series CV and walk-forward validation helpers.
- **Backtester**: Minute-level engine applying brokerage (0.03%), stamp duty (0.015%), exchange levies (0.002%), and spread-based slippage.
- **Executor**: Zerodha Kite executor with strict `--confirm-live` requirement, dry-run simulator, and risk guardrails.
- **Monitoring**: Daily P&L/drawdown report generator and Streamlit dashboard stub (Plotly-ready).

## Human-in-the-loop Policy

- Events flagged `news_shock` > 0.8 require analyst review before enabling new positions.
- Manual labels stored alongside news metadata for retraining.
- Retrain models weekly (incremental) and quarterly (full rebuild); disable live trading if walk-forward Sharpe < target.

## Tests

```bash
pytest
```

`tests/test_ingestion.py` validates simulated ingestion, `tests/test_model_eval.py` checks feature builder + training pipeline.

## Safety Notes

- Never run live trading without explicit `--confirm-live` flag *and* valid API keys supplied at runtime.
- Credentials must not be committed; use vault or environment variables.
- Logging captures every order request/response for audit. Use `/data/quant-india/logs/`.

For detailed deployment and operations, refer to `docs/runbook.md` and architecture overview in `docs/architecture.md`.
