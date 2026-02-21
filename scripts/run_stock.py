#!/usr/bin/env python3
"""Example: run options analysis for a few tickers from web (yfinance)."""

from options_analysis import OptsAnalysis


def main() -> None:
    opts = OptsAnalysis()
    for symbol in ("PLTR", "NIO"):
        opts.BuildFromYFinance(symbol)
        opts.PrintExpirationDates()
        exp_dates = opts.GetExpirationDates()
        if exp_dates:
            opts.PlotHistByDate(exp_dates[0], "Volume")
            opts.PlotHistByDate(exp_dates[0], "Both")


if __name__ == "__main__":
    main()
