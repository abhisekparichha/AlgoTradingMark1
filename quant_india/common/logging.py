from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from loguru import logger

_CONFIGURED = False


def _configure_loguru(log_file: Optional[Path] = None) -> None:
    logger.remove()
    logger.add(
        sink=lambda msg: logging.getLogger().handle(logging.makeLogRecord(msg.record)),  # type: ignore[arg-type]
        level="INFO",
        colorize=True,
    )
    if log_file:
        logger.add(log_file, rotation="10 MB", retention=10, level="INFO")


def configure_logging(log_file: Optional[Path] = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if log_file is None:
        log_dir = Path(os.getenv("QUANT_INDIA_LOG_DIR", "/tmp/quant_india"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "quant_india.log"
    _configure_loguru(log_file)
    _CONFIGURED = True
