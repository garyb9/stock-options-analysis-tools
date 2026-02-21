"""Integration: run options analysis on fixture file and sanity-check outputs."""

from pathlib import Path

from options_analysis import OptsAnalysis
from options_analysis.sources.tradestation import load_tradestation_file

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_options_analysis_on_ts_fixture() -> None:
    """Load TS fixture, build OptsAnalysis, run GetOptsDF and basic checks."""
    path = FIXTURES_DIR / "sample_ts_options.csv"
    if not path.exists():
        return  # skip if fixture missing
    result = load_tradestation_file(path)
    opts = OptsAnalysis()
    opts.load_from_source(result)
    dates = opts.GetExpirationDates()
    assert len(dates) >= 1
    df = opts.GetOptsDF("Both", dates=dates)
    assert df is not None
    assert not df.empty
    assert df["all"].sum() > 0
