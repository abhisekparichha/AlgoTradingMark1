from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
import typer

from quant_india.backtest import BacktestEngine, MeanReversionStrategy
from quant_india.common.logging import configure_logging
from quant_india.data import (
    KiteHistoricalIngestion,
    NSEBhavcopyIngestion,
    NewsAPIIngestion,
    export_catalogue,
)
from quant_india.features import FeatureBuilder
from quant_india.models import assemble_feature_matrix, default_training_pipeline
from quant_india.monitoring import generate_daily_report
from quant_india.pipelines import ObjectiveConfig, run_objective_pipeline

app = typer.Typer(add_completion=False, help="Quant India trading system CLI")


@app.command()
def build_catalogue(output: Path = typer.Option(Path("docs/data_catalogue.csv"), help="Output CSV path")) -> None:
    """Export the data catalogue."""
    export_catalogue(output)
    typer.echo(f"Data catalogue written to {output}")


@app.command()
def ingest_kite(
    symbols: List[str] = typer.Option(..., help="Symbols to ingest"),
    start: datetime = typer.Option(..., help="Start datetime (IST)"),
    end: datetime = typer.Option(..., help="End datetime (IST)"),
    interval: str = typer.Option("1m", help="Bar interval"),
) -> None:
    """Ingest historical data from Kite."""
    configure_logging()
    job = KiteHistoricalIngestion()
    df = job.run(symbols=symbols, start=start, end=end, interval=interval)
    typer.echo(f"Ingested {len(df)} rows for symbols {symbols}")


@app.command()
def ingest_nse(
    symbols: List[str] = typer.Option(..., help="Symbols to ingest"),
    start: datetime = typer.Option(..., help="Start date"),
    end: datetime = typer.Option(..., help="End date"),
) -> None:
    """Ingest NSE bhavcopy data."""
    configure_logging()
    job = NSEBhavcopyIngestion()
    df = job.run(symbols=symbols, start=start, end=end, interval="1d")
    typer.echo(f"Ingested {len(df)} NSE rows for symbols {symbols}")


@app.command()
def ingest_news(
    keywords: List[str] = typer.Option(..., help="Keywords to query"),
    hours: int = typer.Option(24, help="Lookback window in hours"),
) -> None:
    """Ingest news articles using NewsAPI."""
    configure_logging()
    job = NewsAPIIngestion()
    end = pd.Timestamp.utcnow()
    start = end - pd.Timedelta(hours=hours)
    df = job.run(symbols=keywords, start=start.to_pydatetime(), end=end.to_pydatetime())
    typer.echo(f"Ingested {len(df)} news articles for keywords {keywords}")


@app.command()
def build_features(
    price_path: Path = typer.Option(..., help="Parquet path with price data"),
    persist: bool = typer.Option(True, help="Persist features to store"),
) -> None:
    """Build feature set for provided price data."""
    configure_logging()
    price_df = pd.read_parquet(price_path)
    builder = FeatureBuilder()
    results = builder.build(price_df, persist=persist)
    typer.echo(f"Created {len(results)} feature tables")


@app.command()
def run_backtest(
    price_path: Path = typer.Option(..., help="Parquet path with price data"),
    feature_path: Path = typer.Option(..., help="Parquet path with features containing vwap_deviation"),
    output_path: Path = typer.Option(Path("artifacts/backtest.parquet"), help="Path to store PnL output"),
) -> None:
    """Run mean reversion backtest with realistic costs."""
    configure_logging()
    price_df = pd.read_parquet(price_path)
    features_df = pd.read_parquet(feature_path)
    strategy = MeanReversionStrategy()
    signals = strategy.generate_signals(features_df)
    engine = BacktestEngine()
    result = engine.run(price_df, signals)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.pnl.to_parquet(output_path)
    typer.echo(f"Backtest completed. Metrics: {result.metrics}")


@app.command()
def train_model(
    price_path: Path = typer.Option(..., help="Price data path"),
    feature_paths: List[Path] = typer.Option(..., help="Feature parquet paths"),
    horizon: int = typer.Option(5, help="Prediction horizon in bars"),
) -> None:
    """Train ensemble model with cross-validation and walk-forward evaluation."""
    configure_logging()
    price_df = pd.read_parquet(price_path)
    feature_frames = [pd.read_parquet(path) for path in feature_paths]
    dataset = assemble_feature_matrix(price_df, feature_frames, horizon=horizon)
    feature_cols = [col for col in dataset.columns if col not in {"symbol", "timestamp", "close", "target_return"}]
    X = dataset[feature_cols].fillna(0).values
    y = dataset["target_return"].values
    pipeline = default_training_pipeline()
    cv_metrics = pipeline.cross_validate(X, y)
    pipeline.fit(X, y)
    eval_metrics = pipeline.evaluate(X, y)
    typer.echo(f"Cross-validation metrics: {cv_metrics}")
    typer.echo(f"Training evaluation metrics: {eval_metrics}")


@app.command()
def report(
    pnl_path: Path = typer.Option(..., help="Parquet path with backtest pnl"),
    output_path: Path = typer.Option(Path("artifacts/daily_report.json"), help="Output JSON path"),
) -> None:
    """Generate monitoring report from PnL series."""
    pnl_df = pd.read_parquet(pnl_path)
    report = generate_daily_report(pnl_df, output_path)
    typer.echo(f"Report written to {output_path}: {report}")


def _to_utc(dt: Optional[datetime]) -> Optional[pd.Timestamp]:
    if dt is None:
        return None
    ts = pd.Timestamp(dt)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


@app.command("run-objective")
def run_objective_cli(
    data_root: Path = typer.Option(Path("artifacts/data_repo"), help="Data root for repository build"),
    model_artifact_dir: Path = typer.Option(Path("artifacts/model_outputs"), help="Directory for model artifacts"),
    max_total_invest: float = typer.Option(100_000.0, help="Maximum capital allocation across trades"),
    shortlist_n: int = typer.Option(30, help="Number of tickers to keep in shortlist"),
    selection_mode: str = typer.Option("signal-rank", help="Selection mode: SIGNAL-RANK | RANDOM-SAMPLE | USER-DEFINED"),
    selection_k: int = typer.Option(3, help="Number of tickers to select"),
    entry_threshold: float = typer.Option(0.6, help="Signal threshold for entries"),
    exit_threshold: float = typer.Option(-0.2, help="Signal threshold for exits"),
    target_pct: float = typer.Option(0.03, help="Profit target (fraction)"),
    stop_pct: float = typer.Option(0.015, help="Stop loss (fraction)"),
    min_adv_inr: float = typer.Option(10_000_000.0, help="Minimum ADV filter in INR"),
    min_daily_vol: float = typer.Option(100_000.0, help="Minimum average daily volume filter"),
    random_seed: int = typer.Option(42, help="Base random seed"),
    sim_start: Optional[datetime] = typer.Option(None, help="Simulation window start (UTC, default = end-6months)"),
    sim_end: Optional[datetime] = typer.Option(None, help="Simulation window end (UTC, default = now)"),
) -> None:
    """Run the end-to-end objective pipeline: create data repo, shortlist, simulate, and backtest."""
    configure_logging()
    config = ObjectiveConfig(
        data_root=data_root,
        model_artifact_dir=model_artifact_dir,
        max_total_invest=max_total_invest,
        shortlist_n=shortlist_n,
        selection_mode=selection_mode,
        selection_k=selection_k,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        target_pct=target_pct,
        stop_pct=stop_pct,
        min_adv_inr=min_adv_inr,
        min_daily_vol=min_daily_vol,
        random_seed=random_seed,
        sim_start=_to_utc(sim_start),
        sim_end=_to_utc(sim_end),
    )
    artifacts = run_objective_pipeline(config)
    typer.echo(f"Objective pipeline completed. Artifacts directory: {model_artifact_dir}")
    typer.echo(artifacts)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
