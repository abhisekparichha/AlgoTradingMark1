from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class StorageConfig(BaseModel):
    raw_root: Path = Field(default=Path("/data/quant-india/raw"))
    processed_root: Path = Field(default=Path("/data/quant-india/processed"))
    feature_store_root: Path = Field(default=Path("/data/feature-store"))
    checkpoints_root: Path = Field(default=Path("/data/quant-india/checkpoints"))


class KiteConfig(BaseModel):
    api_key: str = Field(default="<<KITE_API_KEY>>")
    api_secret: str = Field(default="<<KITE_API_SECRET>>")
    access_token: str = Field(default="<<KITE_ACCESS_TOKEN>>")
    root_dir: Path = Field(default=Path("/data/quant-india/kite"))


class DataSourceConfig(BaseModel):
    kite: KiteConfig = KiteConfig()
    nse_api_key: str = Field(default="<<NSE_DATA_API_KEY>>")
    truedata_api_key: str = Field(default="<<TRUE_DATA_KEY>>")


class FeatureStoreConfig(BaseModel):
    registry_uri: str = Field(default="s3://quant-india/feature-store/registry.json")
    local_cache: Path = Field(default=Path("/data/feature-store"))
    default_backfill_days: int = Field(default=365)


class BacktestConfig(BaseModel):
    default_slippage_bps: float = Field(default=5.0)
    brokerage_pct: float = Field(default=0.0003)
    stamp_duty_pct: float = Field(default=0.00015)
    exchange_charges_pct: float = Field(default=0.00002)


class ExecutorConfig(BaseModel):
    dry_run: bool = True
    max_notional_per_order: float = 2_500_000.0
    max_unrealized_drawdown_pct: float = 0.1


class Settings(BaseModel):
    environment: str = Field(default="local")
    timezone: str = Field(default="Asia/Kolkata")
    storage: StorageConfig = StorageConfig()
    data_sources: DataSourceConfig = DataSourceConfig()
    feature_store: FeatureStoreConfig = FeatureStoreConfig()
    backtest: BacktestConfig = BacktestConfig()
    executor: ExecutorConfig = ExecutorConfig()


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings(config_path: Optional[Path] = None) -> Settings:
    default_config = _read_yaml(Path(__file__).resolve().parents[2] / "configs" / "base.yaml")
    override_config: Dict[str, Any] = {}

    env_path_str = os.getenv("QUANT_INDIA_CONFIG")
    if config_path is None and env_path_str:
        config_path = Path(env_path_str)

    if config_path:
        override_config = _read_yaml(config_path)

    merged = _merge_dicts(default_config, override_config)
    return Settings(**merged)


@lru_cache(maxsize=1)
def get_settings(config_path: Optional[Path] = None) -> Settings:
    return load_settings(config_path)
