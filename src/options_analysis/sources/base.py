"""Base types for options data sources."""

from typing import TypedDict

import pandas as pd


class OptionsSourceResult(TypedDict):
    """Unified result from an options source."""

    ticker: str
    dates: list[str]
    big_dict: dict[str, dict[str, pd.DataFrame]]  # date -> {calls, puts}
