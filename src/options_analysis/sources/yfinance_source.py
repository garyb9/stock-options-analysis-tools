"""yfinance options chain source (free, programmatic)."""

from datetime import datetime

import pandas as pd
import yfinance as yf

from options_analysis.sources.base import OptionsSourceResult


def _date_to_ddmmyyyy(exp: str) -> str:
    """Convert yfinance expiration (YYYY-MM-DD) to dd/mm/yyyy."""
    dt = datetime.strptime(exp, "%Y-%m-%d")
    return dt.strftime("%d/%m/%Y")


def _normalize_chain_df(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to Strike, Volume, OpenInt for core compatibility."""
    renames: dict[str, str] = {}
    for c in df.columns:
        if c == "strike":
            renames[c] = "Strike"
        elif c == "volume":
            renames[c] = "Volume"
        elif c == "openInterest":
            renames[c] = "OpenInt"
    out = df.rename(columns=renames).copy()
    if "Volume" not in out.columns:
        out["Volume"] = 0
    if "OpenInt" not in out.columns:
        out["OpenInt"] = 0
    return out


def load_yfinance(ticker: str) -> OptionsSourceResult:
    """Fetch options chain for ticker from yfinance (Yahoo)."""
    ticker = str(ticker).strip().upper().lstrip("0")
    t = yf.Ticker(ticker)
    expirations = t.options
    if not expirations:
        return OptionsSourceResult(ticker=ticker, dates=[], big_dict={})

    dates_str = [_date_to_ddmmyyyy(exp) for exp in expirations]
    big_dict: dict[str, dict[str, pd.DataFrame]] = {}
    for exp, date_str in zip(expirations, dates_str, strict=False):
        chain = t.option_chain(exp)
        calls = _normalize_chain_df(chain.calls)
        puts = _normalize_chain_df(chain.puts)
        big_dict[date_str] = {"calls": calls, "puts": puts}

    return OptionsSourceResult(ticker=ticker, dates=dates_str, big_dict=big_dict)


class YFinanceSource:
    """Options data via yfinance (free, no API key)."""

    def fetch(self, ticker: str) -> OptionsSourceResult:
        """Fetch options chain for symbol."""
        return load_yfinance(ticker)
