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
