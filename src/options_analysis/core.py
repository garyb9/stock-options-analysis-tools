"""Core options analysis: aggregation, stats, plots."""

import contextlib
import locale
from enum import Enum

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from options_analysis.sources.base import OptionsSourceResult
from options_analysis.sources.tradestation import load_tradestation_file
from options_analysis.sources.yahoo_scrape import load_yahoo_scrape
from options_analysis.sources.yfinance_source import load_yfinance


class Values(Enum):
    """Metric to aggregate: volume, open interest, or both."""

    Both = 0
    Volume = 1
    OpenInt = 2


def _normalize_val(val: Values | str) -> Values | None:
    """Accept enum or string 'Both'/'Volume'/'OpenInt'; return Values or None."""
    if isinstance(val, Values):
        return val
    if isinstance(val, str):
        u = val.strip()
        if u == "Both":
            return Values.Both
        if u == "Volume":
            return Values.Volume
        if u == "OpenInt":
            return Values.OpenInt
    return None


def _to_numeric_series(series: pd.Series) -> np.ndarray:
    """Coerce option volume/OI column to int64 (handles commas, dashes, float strings)."""
    if series.dtype.kind in "iu":
        return np.asarray(series, dtype=np.int64)
    # Use pd.to_numeric so "4.0" and "1,234" coerce to float, then int64
    numeric = pd.to_numeric(
        series.astype(str).str.replace(",", "").str.replace("-", "0"), errors="coerce"
    )
    return np.asarray(numeric.fillna(0), dtype=np.int64)


class OptsAnalysis:
    """Options chain analysis: load from multiple sources, aggregate by strike, plot."""

    def __init__(self) -> None:
        self._ticker = ""
        self._dates: list[str] = []
        self._big_dict: dict[str, dict[str, pd.DataFrame]] = {}

    @property
    def Ticker(self) -> str:
        return self._ticker

    @Ticker.setter
    def Ticker(self, value: str) -> None:
        self._ticker = value

    @property
    def Dates(self) -> list[str]:
        return self._dates

    @property
    def BigDict(self) -> dict[str, dict[str, pd.DataFrame]]:
        return self._big_dict

    def load_from_source(self, result: OptionsSourceResult) -> None:
        """Load state from a source result (ticker, dates, big_dict)."""
        self._ticker = result["ticker"]
        self._dates = result["dates"]
        self._big_dict = result["big_dict"]

    def BuildFromTS(self, file_path: str | None = None) -> None:
        """Load from TradeStation file (<ticker>.[xls, xlsx, csv])."""
        if not file_path:
            raise ValueError("No file given")
        result = load_tradestation_file(file_path)
        self.load_from_source(result)

    def BuildFromWeb(self, ticker: str | None = None, verbose: bool = True) -> None:
        """Load from Yahoo Finance (HTML scrape)."""
        if not ticker:
            raise ValueError("No ticker given")
        result = load_yahoo_scrape(ticker, verbose=verbose)
        self.load_from_source(result)

    def BuildFromYFinance(self, ticker: str | None = None) -> None:
        """Load from yfinance (recommended free source)."""
        if not ticker:
            raise ValueError("No ticker given")
        result = load_yfinance(ticker)
        self.load_from_source(result)

    def GetExpirationDates(self) -> list[str]:
        return self._dates.copy()

    def PrintExpirationDates(self) -> None:
        print(self._ticker, "Expiration Dates available:")
        print(self._dates)

    def GetValuesString(self, val: Values | str) -> str:
        v = _normalize_val(val)
        if v == Values.Both:
            return "Volume and Open Interest"
        if v == Values.Volume:
            return "Volume"
        if v == Values.OpenInt:
            return "Open Interest"
        return ""

    def GetDatesStartEnd(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[str]:
        """Return list of expiration dates in [start_date, end_date]; empty if invalid."""
        if not self._dates:
            return []
        start_date = start_date or self._dates[0]
        if start_date not in self._dates:
            print("Start Date given not in available expiration dates:", self._dates)
            return []
        start_idx = self._dates.index(start_date)
        if end_date is None or self._dates.index(end_date) == len(self._dates) - 1:
            return self._dates[start_idx:]
        if end_date not in self._dates:
            print("End Date given not in available expiration dates:", self._dates)
            return []
        end_idx = self._dates.index(end_date)
        if start_idx > end_idx:
            print("End Date should be on or after Start Date")
            return []
        if start_idx == end_idx:
            return self._dates[start_idx : start_idx + 1]
        return self._dates[start_idx : end_idx + 1]

    def GetOptsDF(
        self,
        val: Values | str = Values.Both,
        dates: list[str] | None = None,
    ) -> pd.DataFrame | None:
        """Aggregate calls/puts by strike for the given dates. val = Volume, OpenInt, or Both."""
        v = _normalize_val(val)
        if v is None:
            print("Value must be Volume, OpenInt, or Both")
            return None
        if not dates:
            return None
        df = pd.DataFrame(columns=["calls", "puts", "all"])
        for key in dates:
            if key not in self._big_dict:
                continue
            block = self._big_dict[key]
            calls_df = block["calls"]
            puts_df = block["puts"]
            strike_col = "Strike" if "Strike" in calls_df.columns else "strike"
            if strike_col not in calls_df.columns:
                continue
            x_calls = np.asarray(calls_df[strike_col], dtype=float)
            vol_c = (
                calls_df["Volume"]
                if "Volume" in calls_df.columns
                else pd.Series(0, index=calls_df.index)
            )
            oi_c = (
                calls_df["OpenInt"]
                if "OpenInt" in calls_df.columns
                else pd.Series(0, index=calls_df.index)
            )
            if v == Values.Both:
                y_calls = _to_numeric_series(vol_c) + _to_numeric_series(oi_c)
            elif v == Values.Volume:
                y_calls = _to_numeric_series(vol_c)
            else:
                y_calls = _to_numeric_series(oi_c)

            for idx, strike in enumerate(x_calls):
                if strike in df.index:
                    df.loc[strike, "calls"] += y_calls[idx]
                    df.loc[strike, "all"] += y_calls[idx]
                else:
                    df.loc[strike] = [y_calls[idx], 0, y_calls[idx]]

            x_puts = np.asarray(puts_df[strike_col], dtype=float)
            vol_p = (
                puts_df["Volume"]
                if "Volume" in puts_df.columns
                else pd.Series(0, index=puts_df.index)
            )
            oi_p = (
                puts_df["OpenInt"]
                if "OpenInt" in puts_df.columns
                else pd.Series(0, index=puts_df.index)
            )
            if v == Values.Both:
                y_puts = _to_numeric_series(vol_p) + _to_numeric_series(oi_p)
            elif v == Values.Volume:
                y_puts = _to_numeric_series(vol_p)
            else:
                y_puts = _to_numeric_series(oi_p)

            for idx, strike in enumerate(x_puts):
                if strike in df.index:
                    df.loc[strike, "puts"] += y_puts[idx]
                    df.loc[strike, "all"] += y_puts[idx]
                else:
                    df.loc[strike] = [0, y_puts[idx], y_puts[idx]]

        return df.sort_index() if not df.empty else df

    def StatsPlot(
        self,
        stats: bool = True,
        plot: bool = True,
        val: Values | str = Values.Both,
        dates: list[str] | None = None,
        opts_df: pd.DataFrame | None = None,
    ) -> None:
        """Print weighted mean/std and optionally show bar chart."""
        if not dates or dates == []:
            print("Empty list of dates given")
            return
        if opts_df is None or opts_df.empty:
            print("No opts DataFrame given")
            return
        sum_calls = opts_df["calls"].sum()
        sum_puts = opts_df["puts"].sum()
        sum_overall = opts_df["all"].sum()
        mean_calls = np.average(opts_df.index, weights=opts_df["calls"])
        std_calls = np.sqrt(np.average((opts_df.index - mean_calls) ** 2, weights=opts_df["calls"]))
        mean_puts = np.average(opts_df.index, weights=opts_df["puts"])
        std_puts = np.sqrt(np.average((opts_df.index - mean_puts) ** 2, weights=opts_df["puts"]))
        mean_all = np.average(opts_df.index, weights=opts_df["all"])
        std_all = np.sqrt(np.average((opts_df.index - mean_all) ** 2, weights=opts_df["all"]))
        per_calls = str(round(100 * float(sum_calls) / float(sum_overall), 2)) + "%"
        per_puts = str(round(100 * float(sum_puts) / float(sum_overall), 2)) + "%"
        print_stats_str = (
            "---- " + self._ticker + " Options " + self.GetValuesString(val) + " Stats ----"
        )
        with contextlib.suppress(locale.Error):
            locale.setlocale(locale.LC_ALL, "en_US")
        str_calls = locale.format_string("%d", int(sum_calls), grouping=True)
        str_puts = locale.format_string("%d", int(sum_puts), grouping=True)
        str_overall = locale.format_string("%d", int(sum_overall), grouping=True)
        w = max(len(str_calls), len(str_puts), len(str_overall))
        str_calls = f"{str_calls:<{w}}"
        str_puts = f"{str_puts:<{w}}"
        str_overall = f"{str_overall:<{w}}"
        str_mean_calls = f"{mean_calls:.2f}"
        str_mean_puts = f"{mean_puts:.2f}"
        str_mean_all = f"{mean_all:.2f}"
        wm = max(len(str_mean_calls), len(str_mean_puts), len(str_mean_all))
        str_mean_calls = f"{str_mean_calls:<{wm}}"
        str_mean_puts = f"{str_mean_puts:<{wm}}"
        str_mean_all = f"{str_mean_all:<{wm}}"
        str_std_calls = f"{std_calls:.2f}"
        str_std_puts = f"{std_puts:.2f}"
        str_std_all = f"{std_all:.2f}"
        ws = max(len(str_std_calls), len(str_std_puts), len(str_std_all))
        str_std_calls = f"{str_std_calls:<{ws}}"
        str_std_puts = f"{str_std_puts:<{ws}}"
        str_std_all = f"{str_std_all:<{ws}}"
        print_calls_str = (
            "Calls:\t"
            + str_calls
            + " | Mean = "
            + str_mean_calls
            + " | STD = ±"
            + str_std_calls
            + " | "
            + per_calls
        )
        print_puts_str = (
            "Puts:\t"
            + str_puts
            + " | Mean = "
            + str_mean_puts
            + " | STD = ±"
            + str_std_puts
            + " | "
            + per_puts
        )
        print_all_str = (
            "All:\t" + str_overall + " | Mean = " + str_mean_all + " | STD = ±" + str_std_all
        )
        if dates[0] == self._dates[0] and dates[-1] == self._dates[-1]:
            print_exp_str = "All Expiration Dates"
        elif len(dates) == 1:
            print_exp_str = "Expiring at " + dates[0]
        else:
            print_exp_str = "Expiring From " + dates[0] + " Up To " + dates[-1]
        if stats:
            print(print_stats_str)
            print("\t", print_all_str)
            print("\t", print_calls_str)
            print("\t", print_puts_str)
            print("-" * len(print_stats_str))
        if plot:
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=opts_df.index,
                    y=opts_df["calls"],
                    name=print_calls_str.replace("\t", " ").replace(" |", ","),
                    marker_color="rgba(0,0,255,0.5)",
                )
            )
            fig.add_trace(
                go.Bar(
                    x=opts_df.index,
                    y=opts_df["puts"],
                    name=print_puts_str.replace("\t", " ").replace(" |", ","),
                    marker_color="rgba(255,0,0,0.5)",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=opts_df.index,
                    y=opts_df["all"],
                    mode="lines",
                    name=print_all_str.replace("\t", " ").replace(" |", ","),
                    line={"color": "black", "width": 2},
                )
            )
            fig.update_layout(
                title=f"{self._ticker} Options {self.GetValuesString(val)}, {print_exp_str}",
                xaxis_title="Strike",
                yaxis_title=f"{self.GetValuesString(val)} Count",
                legend={
                    "orientation": "h",
                    "yanchor": "bottom",
                    "y": 1.02,
                    "xanchor": "left",
                    "x": 0,
                },
                barmode="overlay",
            )
            fig.show()

    def PlotHistByDate(
        self,
        date: str,
        val: Values | str = Values.Both,
    ) -> None:
        opts_df = self.GetOptsDF(val=val, dates=[date])
        if opts_df is not None and not opts_df.empty:
            self.StatsPlot(val=val, stats=True, plot=True, dates=[date], opts_df=opts_df)

    def PlotHist(
        self,
        val: Values | str = Values.Both,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> None:
        dates = self.GetDatesStartEnd(start_date=start_date, end_date=end_date)
        if not dates:
            return
        opts_df = self.GetOptsDF(val=val, dates=dates)
        if opts_df is not None and not opts_df.empty:
            self.StatsPlot(val=val, stats=True, plot=True, dates=dates, opts_df=opts_df)

    def PlotTimelineWithErrors(
        self,
        val: Values | str = Values.Both,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> None:
        dates = self.GetDatesStartEnd(start_date=start_date, end_date=end_date)
        if not dates:
            return
        v = _normalize_val(val)
        if v is None:
            return
        df = pd.DataFrame(
            columns=["calls", "callsErr", "perCalls", "puts", "putsErr", "perPuts", "all", "allErr"]
        )
        for key in dates:
            if key not in self._big_dict:
                continue
            block = self._big_dict[key]
            calls_df = block["calls"]
            puts_df = block["puts"]
            strike_col = "Strike" if "Strike" in calls_df.columns else "strike"
            x_calls = np.asarray(calls_df[strike_col], dtype=float)
            vol_c = calls_df.get("Volume", pd.Series(0, index=calls_df.index))
            oi_c = calls_df.get("OpenInt", pd.Series(0, index=calls_df.index))
            if v == Values.Both:
                y_calls = _to_numeric_series(vol_c) + _to_numeric_series(oi_c)
            elif v == Values.Volume:
                y_calls = _to_numeric_series(vol_c)
            else:
                y_calls = _to_numeric_series(oi_c)
            mean_calls = np.average(x_calls, weights=y_calls)
            std_calls = np.sqrt(np.average((x_calls - mean_calls) ** 2, weights=y_calls))
            x_puts = np.asarray(puts_df[strike_col], dtype=float)
            vol_p = puts_df.get("Volume", pd.Series(0, index=puts_df.index))
            oi_p = puts_df.get("OpenInt", pd.Series(0, index=puts_df.index))
            if v == Values.Both:
                y_puts = _to_numeric_series(vol_p) + _to_numeric_series(oi_p)
            elif v == Values.Volume:
                y_puts = _to_numeric_series(vol_p)
            else:
                y_puts = _to_numeric_series(oi_p)
            mean_puts = np.average(x_puts, weights=y_puts)
            std_puts = np.sqrt(np.average((x_puts - mean_puts) ** 2, weights=y_puts))
            df_all = pd.DataFrame(columns=["all"])
            for idx, strike in enumerate(x_calls):
                if strike in df_all.index:
                    df_all.loc[strike] = df_all.loc[strike] + y_calls[idx]
                else:
                    df_all.loc[strike] = y_calls[idx]
            for idx, strike in enumerate(x_puts):
                if strike in df_all.index:
                    df_all.loc[strike] = df_all.loc[strike] + y_puts[idx]
                else:
                    df_all.loc[strike] = y_puts[idx]
            mean_all = np.average(df_all.index, weights=df_all["all"])
            std_all = np.sqrt(np.average((df_all.index - mean_all) ** 2, weights=df_all["all"]))
            total = float(df_all["all"].sum())
            per_calls = round(100 * float(np.sum(y_calls)) / total, 2) if total else 0
            per_puts = round(100 * float(np.sum(y_puts)) / total, 2) if total else 0
            df.loc[key] = [
                mean_calls,
                std_calls,
                per_calls,
                mean_puts,
                std_puts,
                per_puts,
                mean_all,
                std_all,
            ]
        if dates[0] == self._dates[0] and dates[-1] == self._dates[-1]:
            exp_str = "All Expiration Dates"
        elif len(dates) == 1:
            exp_str = "Expiring at " + dates[0]
        else:
            exp_str = "Expiring From " + dates[0] + " Up To " + dates[-1]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["calls"],
                error_y={"type": "data", "array": df["callsErr"], "visible": True},
                mode="lines+markers",
                name="Calls",
                line={"dash": "dot", "color": "rgba(0,0,255,0.4)"},
                marker={"size": 8},
                text=[f"{y:.2f}, {z}%" for y, z in zip(df["calls"], df["perCalls"], strict=False)],
                textposition="top right",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["puts"],
                error_y={"type": "data", "array": df["putsErr"], "visible": True},
                mode="lines+markers",
                name="Puts",
                line={"dash": "dot", "color": "rgba(255,0,0,0.4)"},
                marker={"size": 8},
                text=[f"{y:.2f}, {z}%" for y, z in zip(df["puts"], df["perPuts"], strict=False)],
                textposition="top left",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["all"],
                error_y={"type": "data", "array": df["allErr"], "visible": True},
                mode="lines+markers",
                name="All Options",
                line={"color": "black", "width": 2},
                marker={"size": 10},
                text=[f"{y:.2f}" for y in df["all"]],
                textposition="top center",
            )
        )
        fig.update_traces(textfont_size=10)
        fig.update_layout(
            title=f"{self._ticker} Options Mean and STD spreads, {exp_str}",
            xaxis_title="Expiration Dates",
            yaxis_title="Mean and STD Count",
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
            xaxis={"tickangle": -45},
            showlegend=True,
        )
        fig.show()
