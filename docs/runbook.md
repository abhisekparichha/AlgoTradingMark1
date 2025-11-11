# Quant India Runbook

## Prerequisites
- Python 3.10+
- `pip install -e .[dev]`
- Access to `/data/quant-india/` storage (local or mounted EFS/S3 sync)
- Secrets stored in environment or Vault (never commit keys)

## Local Setup
1. Create virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```
2. Adjust `configs/base.yaml` or point `QUANT_INDIA_CONFIG` to environment-specific overrides.
3. Export credentials at runtime:
   ```bash
   export KITE_API_KEY=...
   export KITE_API_SECRET=...
   export KITE_ACCESS_TOKEN=...
   ```

## Data Ingestion
### Historical backfill
```bash
python -m quant_india.cli.main ingest-kite --symbols RELIANCE TCS \
  --start 2024-01-01T09:15 --end 2024-01-31T15:30 --interval 1m
python -m quant_india.cli.main ingest-nse --symbols RELIANCE TCS \
  --start 2024-01-01 --end 2024-01-31
```
Results stored in `/data/quant-india/raw/source=<source>/date=<YYYY-MM-DD>/symbol=<SYMBOL>/data.parquet`.

### Streaming (production)
- Deploy `quant_india.data.loaders.kite_ws_listener` (extend skeleton) on k8s with autoscaling.
- Publish heartbeats to monitoring queue (Prometheus/Grafana).

## Feature Engineering
```bash
python -m quant_india.cli.main build-features --price-path data/sample_prices.parquet
```
Feature store writes to `/data/feature-store/<feature_name>/`.

## Model Training
1. Collect feature parquet paths (or use S3 manifest).
2. Run training:
   ```bash
   python -m quant_india.cli.main train-model \
     --price-path data/sample_prices.parquet \
     --feature-paths data/features_return_1m.parquet data/features_volume_zscore.parquet \
     --horizon 5
   ```
3. Persist trained artefacts to `s3://quant-india/models/<timestamp>/`.

## Backtesting
```bash
python -m quant_india.cli.main run-backtest \
  --price-path data/sample_prices.parquet \
  --feature-path data/features_mean_reversion.parquet \
  --output-path artifacts/backtest.parquet
```
Review metrics in terminal and open `artifacts/backtest.parquet` for PnL series.

## Execution
- **Dry Run** (default): uses simulated executor with audit trail.
- **Live**: run with `--confirm-live` and ensure `dry_run=False`.
- Integrate with risk manager by validating orders before submission.

## Monitoring & Reporting
```bash
python -m quant_india.cli.main report --pnl-path artifacts/backtest.parquet
streamlit run -m quant_india.monitoring.dashboard
```
Set up cron/batch to generate daily `json` reports, push to S3, and notify via Slack.

## Failure Playbook
- **Ingestion gaps**: trigger `backfill` job with alternate vendor (TrueData CSV dump).
- **API rate limits**: throttle via exponential back-off, switch to cached data.
- **Order failures**: auto-retry with exponential backoff, alert human if 3 consecutive failures.
- **Model drift**: schedule weekly walk-forward evaluation; if Sharpe < threshold, disable live trading and retrain.

## Human-in-the-loop Policy
- Analysts review high-severity news events flagged by `news_shock`.
- Manual labels stored in feature store metadata (`/meta/manual_labels/`).
- Retraining cadence: weekly incremental updates + quarterly full rebuild.
