# Quant India Trading System Architecture

```mermaid
flowchart TD
    subgraph Data Sources
        Kite[(Kite Connect)]
        NSE[NSE Bhavcopy / Option Chain]
        TrueData[TrueData Tick]
        News[News & Sentiment APIs]
        Macro[NSDL / RBI Macro]
    end

    subgraph Ingestion Layer
        IngestJobs[Batch & Streaming Jobs]
        Quality[Quality Checks]
    end

    subgraph Storage
        Raw[/Parquet Raw Zone/]
        Processed[/Parquet Processed Zone/]
        FeatureStore[(Feature Store)]
    end

    subgraph Compute
        Features[Feature Builder]
        Backtest[Backtest Engine]
        Models[Model Training\n(Walk-forward + CV)]
        Strategies[Strategy Layer]
    end

    subgraph Execution
        Executor[Kite Executor\n(dry-run/live)]
        Risk[Risk Manager]
    end

    subgraph Monitoring
        Reports[Daily Reports]
        Dashboard[Streamlit Dashboard]
    end

    Kite --> IngestJobs
    NSE --> IngestJobs
    TrueData --> IngestJobs
    News --> IngestJobs
    Macro --> IngestJobs
    IngestJobs --> Quality --> Raw --> Processed
    Processed --> Features --> FeatureStore
    FeatureStore --> Models --> Strategies --> Backtest
    Strategies --> Executor --> Risk
    Backtest --> Reports
    Executor --> Reports
    Reports --> Dashboard
```

**Key Principles**

- All timestamps stored in `Asia/Kolkata` with UTC copies for analytics.
- Columnar storage (Parquet) with partitioning by `date`, `symbol`, and `feature_name`.
- Backtests account for brokerage, stamp duty, exchange fees, and slippage.
- Live execution guarded by `--confirm-live` flag and dry-run simulator for testing.
