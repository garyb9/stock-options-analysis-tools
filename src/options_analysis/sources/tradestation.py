"""TradeStation file source (xls, xlsx, csv)."""

from pathlib import Path

import numpy as np
import pandas as pd

from options_analysis.sources.base import OptionsSourceResult


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure Strike, Volume, OpenInt column names (title case)."""
    col_map = {c: str(c).replace(" ", "") for c in df.columns}
    df = df.rename(columns=col_map)
    renames: dict[str, str] = {}
    for c in df.columns:
        cnorm = c.replace(" ", "")
        if cnorm.lower() == "strike" and cnorm != "Strike":
            renames[c] = "Strike"
        elif cnorm == "OpenInterest" or "Open Interest" in c:
            renames[c] = "OpenInt"
    df = df.rename(columns=renames)
    if "OpenInt" not in df.columns and "Volume" in df.columns:
        df["OpenInt"] = 0
    return df


def load_tradestation_file(file_path: str | Path) -> OptionsSourceResult:
    """
    Load options data from a TradeStation-format file.
    File should be named <ticker>.[xls, xlsx, csv].
    """
    path = Path(file_path)
    path_str = str(path).lower()
    if not path_str.endswith((".xls", ".xlsx", ".csv")):
        raise ValueError("Only .xls, .xlsx or .csv files are allowed")
    ticker = path.stem
    if not ticker:
        raise ValueError("Bad file name format; use <ticker>.[xls, xlsx, csv]")
    ticker = str(ticker).strip().upper().lstrip("0")

    raw = pd.read_excel(path) if path.suffix.lower() != ".csv" else pd.read_csv(path)
    temp_df = pd.DataFrame(raw.values)
    first_row = [str(x).replace(" ", "") for x in list(temp_df.iloc[0])]
    first_row_lower = [x.lower() for x in first_row]
    if "strike" not in first_row_lower:
        raise ValueError("No 'strike' column found in file")
    strike_index = first_row_lower.index("strike")

    dates: list[str] = []
    indexes: list[int] = []
    for idx, val in enumerate(list(temp_df.iloc[:, 0])):
        if isinstance(val, str) and val != "Pos":
            date = val.split("\t")[0].replace("   ", "").strip()
            dates.append(date)
            indexes.append(idx)

    big_dict: dict[str, dict[str, pd.DataFrame]] = {}
    for i, date in enumerate(dates):
        start_row = indexes[i] + 1
        end_row = indexes[i + 1] if i + 1 < len(indexes) else len(temp_df.index)

        calls = pd.DataFrame(temp_df.iloc[start_row:end_row, : strike_index + 1])
        calls.columns = first_row[: strike_index + 1]
        calls.index = np.arange(1, len(calls) + 1)
        calls = calls.drop("Pos", axis=1, errors="ignore")
        calls = _normalize_columns(calls)

        puts = pd.DataFrame(temp_df.iloc[start_row:end_row, strike_index:])
        puts.columns = first_row[strike_index:]
        puts.index = np.arange(1, len(puts) + 1)
        puts = puts.drop("Pos", axis=1, errors="ignore")
        puts = _normalize_columns(puts)

        big_dict[date] = {"calls": calls, "puts": puts}

    return OptionsSourceResult(ticker=ticker, dates=dates, big_dict=big_dict)


class TradeStationFileSource:
    """Options data from a local TradeStation file."""

    def fetch(self, file_path: str | Path) -> OptionsSourceResult:
        """Load from file; ticker is derived from filename."""
        return load_tradestation_file(file_path)
