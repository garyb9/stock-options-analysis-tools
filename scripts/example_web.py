#!/usr/bin/env python3
"""Example: load options from web (yfinance preferred) and plot first expiration."""

from options_analysis import OptsAnalysis


def main() -> None:
    opts = OptsAnalysis()
    # Prefer yfinance (free, stable API)
    opts.BuildFromYFinance("PLTR")
    opts.PrintExpirationDates()
    exp_dates = opts.GetExpirationDates()
    if exp_dates:
        opts.PlotHistByDate(exp_dates[0], "Volume")
        opts.PlotHistByDate(exp_dates[0], "OpenInt")
        opts.PlotHistByDate(exp_dates[0], "Both")


if __name__ == "__main__":
    main()
