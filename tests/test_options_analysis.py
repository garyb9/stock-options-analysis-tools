"""Tests for options_analysis: parsing, GetDatesStartEnd, GetOptsDF."""

from pathlib import Path

import pandas as pd

from options_analysis import OptsAnalysis
from options_analysis.core import Values, _normalize_val
from options_analysis.sources.tradestation import load_tradestation_file

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_normalize_val() -> None:
    assert _normalize_val(Values.Both) == Values.Both
    assert _normalize_val(Values.Volume) == Values.Volume
    assert _normalize_val("Both") == Values.Both
    assert _normalize_val("Volume") == Values.Volume
    assert _normalize_val("OpenInt") == Values.OpenInt
    assert _normalize_val("unknown") is None
    assert _normalize_val(123) is None


def test_tradestation_parse_fixture() -> None:
    path = FIXTURES_DIR / "sample_ts_options.csv"
    result = load_tradestation_file(path)
    assert result["ticker"] == "sample_ts_options"
    assert len(result["dates"]) == 1
    assert result["dates"][0] == "01/17/25"
    assert "01/17/25" in result["big_dict"]
    block = result["big_dict"]["01/17/25"]
    assert "calls" in block and "puts" in block
    calls = block["calls"]
    puts = block["puts"]
    assert "Strike" in calls.columns
    assert "Volume" in calls.columns or "OpenInt" in calls.columns
    assert len(calls) == 2
    assert len(puts) == 2


def test_get_dates_start_end() -> None:
    opts = OptsAnalysis()
    opts.load_from_source(
        {
            "ticker": "TEST",
            "dates": ["01/01/25", "02/01/25", "03/01/25"],
            "big_dict": {},
        }
    )
    # default start = first date, end = last
    got = opts.GetDatesStartEnd()
    assert got == ["01/01/25", "02/01/25", "03/01/25"]
    # explicit start and end
    got = opts.GetDatesStartEnd(start_date="02/01/25", end_date="03/01/25")
    assert got == ["02/01/25", "03/01/25"]
    # single date
    got = opts.GetDatesStartEnd(start_date="02/01/25", end_date="02/01/25")
    assert got == ["02/01/25"]
    # invalid start
    got = opts.GetDatesStartEnd(start_date="99/99/99")
    assert got == []
    # invalid end
    got = opts.GetDatesStartEnd(start_date="01/01/25", end_date="99/99/99")
    assert got == []
    # end before start
    got = opts.GetDatesStartEnd(start_date="03/01/25", end_date="01/01/25")
    assert got == []


def test_get_opts_df_aggregation() -> None:
    """GetOptsDF sums by strike and respects Volume/OpenInt/Both."""
    opts = OptsAnalysis()
    # Build minimal big_dict: one date, two strikes, calls and puts
    calls = pd.DataFrame(
        {
            "Strike": [100.0, 105.0],
            "Volume": [10, 20],
            "OpenInt": [5, 15],
        }
    )
    puts = pd.DataFrame(
        {
            "Strike": [95.0, 100.0],
            "Volume": [30, 40],
            "OpenInt": [10, 20],
        }
    )
    opts.load_from_source(
        {
            "ticker": "T",
            "dates": ["01/17/25"],
            "big_dict": {"01/17/25": {"calls": calls, "puts": puts}},
        }
    )
    dates = ["01/17/25"]

    df_vol = opts.GetOptsDF(Values.Volume, dates=dates)
    assert df_vol is not None
    assert not df_vol.empty
    # Calls 100: 10, 105: 20. Puts 95: 30, 100: 40. So 95: 0+30, 100: 10+40, 105: 20+0
    assert df_vol.loc[95, "puts"] == 30 and df_vol.loc[95, "calls"] == 0
    assert df_vol.loc[100, "calls"] == 10 and df_vol.loc[100, "puts"] == 40
    assert df_vol.loc[105, "calls"] == 20 and df_vol.loc[105, "puts"] == 0
    assert df_vol["all"].sum() == 10 + 20 + 30 + 40

    df_oi = opts.GetOptsDF(Values.OpenInt, dates=dates)
    assert df_oi is not None
    assert (
        df_oi.loc[95, "puts"] == 10
        and df_oi.loc[100, "calls"] == 5
        and df_oi.loc[100, "puts"] == 20
    )

    df_both = opts.GetOptsDF(Values.Both, dates=dates)
    assert df_both is not None
    # 100 calls: 10+5=15, 105: 20+15=35, 95 puts: 30+10=40, 100 puts: 40+20=60
    assert df_both.loc[100, "calls"] == 15 and df_both.loc[100, "puts"] == 60
    assert df_both.loc[105, "calls"] == 35
    assert df_both.loc[95, "puts"] == 40


def test_get_opts_df_accepts_string_val() -> None:
    opts = OptsAnalysis()
    calls = pd.DataFrame({"Strike": [100.0], "Volume": [1], "OpenInt": [0]})
    puts = pd.DataFrame({"Strike": [100.0], "Volume": [0], "OpenInt": [1]})
    opts.load_from_source(
        {
            "ticker": "T",
            "dates": ["01/17/25"],
            "big_dict": {"01/17/25": {"calls": calls, "puts": puts}},
        }
    )
    df = opts.GetOptsDF("Both", dates=["01/17/25"])
    assert df is not None
    assert df.loc[100, "all"] == 2


def test_get_opts_df_default_val_enum() -> None:
    """Default val=Values.Both should work (regression for old bug)."""
    opts = OptsAnalysis()
    calls = pd.DataFrame({"Strike": [100.0], "Volume": [1], "OpenInt": [0]})
    puts = pd.DataFrame({"Strike": [100.0], "Volume": [0], "OpenInt": [0]})
    opts.load_from_source(
        {
            "ticker": "T",
            "dates": ["01/17/25"],
            "big_dict": {"01/17/25": {"calls": calls, "puts": puts}},
        }
    )
    df = opts.GetOptsDF(dates=["01/17/25"])  # default val=Values.Both
    assert df is not None
    assert not df.empty
