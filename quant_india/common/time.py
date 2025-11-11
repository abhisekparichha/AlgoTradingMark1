from __future__ import annotations

from datetime import datetime, timezone
from typing import Union

import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")


def ensure_timezone(dt: Union[str, datetime, pd.Timestamp], tz: str = "Asia/Kolkata") -> pd.Timestamp:
    """
    Convert a datetime-like object to a timezone-aware pandas Timestamp.
    All internal processing defaults to Asia/Kolkata unless otherwise specified.
    """
    if isinstance(dt, str):
        timestamp = pd.Timestamp(dt)
    elif isinstance(dt, pd.Timestamp):
        timestamp = dt
    else:
        timestamp = pd.Timestamp(dt)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(pytz.timezone(tz))
    else:
        timestamp = timestamp.tz_convert(pytz.timezone(tz))
    return timestamp


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc))


def ist_now() -> pd.Timestamp:
    return utc_now().tz_convert(IST)
