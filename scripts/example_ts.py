#!/usr/bin/env python3
"""Example: load options from TradeStation file and plot."""

from pathlib import Path

from options_analysis import OptsAnalysis


def main() -> None:
    # Use data/ at repo root; adjust path if running from elsewhere
    data_dir = Path(__file__).resolve().parent.parent / "data"
    pltr_file = data_dir / "pltr.xls"
    if not pltr_file.exists():
        pltr_file = data_dir / "pltr.xlsx"
    if not pltr_file.exists():
        print("No pltr.xls or pltr.xlsx in data/; add a TradeStation export to try.")
        return
    opts = OptsAnalysis()
    opts.BuildFromTS(pltr_file)
    opts.PrintExpirationDates()
    exp_dates = opts.GetExpirationDates()
    if exp_dates:
        opts.PlotHistByDate(exp_dates[0], "Volume")
        opts.PlotHistByDate(exp_dates[0], "OpenInt")
        opts.PlotHistByDate(exp_dates[0], "Both")
        opts.PlotHist("Volume")
        opts.PlotHist("OpenInt")
        opts.PlotHist("Both")


if __name__ == "__main__":
    main()
