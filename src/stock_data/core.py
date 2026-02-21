"""Stock data: load CSV, date-indexed frames, correlation with reference ticker."""

import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _get_data(ticker: str, data_dir: str | Path) -> pd.DataFrame:
    """Load first CSV in data_dir that contains ticker in filename."""
    data_dir = Path(data_dir)
    df = None
    for name in data_dir.iterdir():
        if not name.is_file() or ticker not in name.name:
            continue
        df = pd.read_csv(name)
        df = df.drop(
            ["OverBot", "OverSld", "OI", "Vol.1", "Up", "Down"],
            axis=1,
            errors="ignore",
        )
        df = df[df.all(axis=1)].reset_index(drop=True)
        break
    if df is None:
        raise FileNotFoundError(f"Did not find {ticker} data in {data_dir}")
    return df


def _get_dates_dict(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split dataframe by date; keys are dd/mm/yyyy."""
    dates_parsed = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
    df = df.copy()
    df["Date"] = dates_parsed.dt.strftime("%d/%m/%Y")
    date_keys = list(dict.fromkeys(df["Date"].tolist()))
    return {k: df.loc[df["Date"] == k] for k in date_keys}


class StockData:
    """Load ticker (and optional reference) CSV data; correlation and intraday analysis."""

    def __init__(
        self,
        ticker: str,
        refticker: str | None = None,
        data_dir: str | Path | None = None,
    ) -> None:
        if not ticker:
            raise ValueError("No ticker given")
        self.ticker = str(ticker).strip().upper().lstrip("0")
        self.refticker = str(refticker).strip().upper().lstrip("0") if refticker else None
        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.ticker_df = _get_data(self.ticker, self.data_dir)
        self.ticker_dates_dict = _get_dates_dict(self.ticker_df)
        self.refticker_df: pd.DataFrame | None = None
        self.refticker_dates_dict: dict[str, pd.DataFrame] = {}
        if self.refticker:
            self.refticker_df = _get_data(self.refticker, self.data_dir)
            self.refticker_dates_dict = _get_dates_dict(self.refticker_df)

    @staticmethod
    def _plot_dict(
        d: dict[str, float],
        d2: dict[str, float] | None = None,
        annotate: bool = True,
    ) -> None:
        fig, ax = plt.subplots()
        keys = list(d.keys())
        times = [datetime.datetime.strptime(k, "%d/%m/%Y") for k in keys]
        values = list(d.values())
        ax.plot_date(times, values, color="tab:red", fmt="v-")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("exp", color="tab:red")
        ax.xaxis.set_minor_locator(mdates.DayLocator())
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d"))
        ax.xaxis.grid(True, which="minor")
        ax.yaxis.grid()
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d\n%b\n%Y"))
        if annotate:
            for t, v in zip(times, values, strict=False):
                ax.annotate(
                    f"{v:.2f}", (t, v), textcoords="offset points", xytext=(0, 10), ha="center"
                )
        ax.tick_params(axis="y", labelcolor="tab:red")
        if d2:
            ax2 = ax.twinx()
            keys2 = list(d2.keys())
            times2 = [datetime.datetime.strptime(k, "%d/%m/%Y") for k in keys2]
            values2 = list(d2.values())
            ax2.plot_date(times2, values2, color="tab:blue", fmt="v-")
            ax2.set_ylabel("exp", color="tab:blue")
            ax2.xaxis.set_minor_locator(mdates.DayLocator())
            ax2.xaxis.set_minor_formatter(mdates.DateFormatter("%d"))
            ax2.xaxis.grid(True, which="minor")
            ax2.yaxis.grid()
            ax2.xaxis.set_major_locator(mdates.MonthLocator())
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d\n%b\n%Y"))
            if annotate:
                for t, v in zip(times2, values2, strict=False):
                    ax2.annotate(
                        f"{v:.2f}", (t, v), textcoords="offset points", xytext=(0, 10), ha="center"
                    )
            ax2.tick_params(axis="y", labelcolor="tab:blue")
        fig.tight_layout()
        plt.show()

    @staticmethod
    def _plot_histogram(
        d: dict[str, datetime.time],
        d2: dict[str, datetime.time] | None = None,
    ) -> None:
        bins = [t.strftime("%H:%M") for t in pd.date_range("16:30", "23:00", freq="1min")]
        bins1 = dict.fromkeys(bins, 0)
        for t in d.values():
            key = t.strftime("%H:%M")
            if key in bins1:
                bins1[key] += 1
        plt.bar(bins1.keys(), bins1.values(), alpha=0.5, width=1.0, color="red")
        if d2:
            bins2 = dict.fromkeys(bins, 0)
            for t in d2.values():
                key = t.strftime("%H:%M")
                if key in bins2:
                    bins2[key] += 1
            plt.bar(bins2.keys(), bins2.values(), alpha=0.5, width=1.0, color="blue")
        plt.show()

    def _date_analysis(self, correlation_dict: dict[str, float]) -> None:
        from finviz_scraper import FinvizScraper

        values_arr = np.array(list(correlation_dict.values()))
        min_val = max(-1.0, float(values_arr.mean() - values_arr.std()))
        max_val = min(1.0, float(values_arr.mean() + values_arr.std()))
        rare_dates = [
            d
            for d in correlation_dict
            if correlation_dict[d] <= min_val or correlation_dict[d] >= max_val
        ]
        print("Dates where 'something weird' happened:\n", rare_dates)
        print("-" * 100)
        finviz = FinvizScraper(self.ticker)
        for rare_date in rare_dates:
            for news in finviz.news:
                if rare_date == news.date:
                    print("Found news at:", rare_date)
                    print(news.string)
                    print("Link:", news.link)
                    print("-" * 100)

    def correlation_with_ref(
        self,
        date_analysis: bool = True,
        plot: bool = True,
    ) -> dict[str, float]:
        if not self.refticker:
            raise ValueError("No reference ticker was provided")
        correlation_dict: dict[str, float] = {}
        for key in self.ticker_dates_dict:
            if key not in self.refticker_dates_dict:
                continue
            open1 = self.ticker_dates_dict[key]["Open"]
            close1 = self.ticker_dates_dict[key]["Close"]
            low1 = self.ticker_dates_dict[key]["Low"]
            high1 = self.ticker_dates_dict[key]["High"]
            avg1 = (open1 + close1 + low1 + high1) / 4
            open2 = self.refticker_dates_dict[key]["Open"]
            close2 = self.refticker_dates_dict[key]["Close"]
            low2 = self.refticker_dates_dict[key]["Low"]
            high2 = self.refticker_dates_dict[key]["High"]
            avg2 = (open2 + close2 + low2 + high2) / 4
            correlation_dict[key] = float(avg1.corr(avg2))
        values_arr = np.array(list(correlation_dict.values()))
        print("Calculated Correlation of", self.ticker, "to", self.refticker)
        print("Correlation Median:\t\t", f"{np.median(values_arr):.4f}")
        print("Correlation Mean:\t\t", f"{values_arr.mean():.4f}")
        print("Correlation Variance:\t", f"{values_arr.var():.4f}")
        print("Correlation STD:\t\t", f"{values_arr.std():.4f}")
        if date_analysis:
            self._date_analysis(correlation_dict)
        if plot:
            self._plot_dict(correlation_dict)
        return correlation_dict

    def highest_lowest_point_daily(
        self,
        hist: bool = True,
    ) -> tuple[dict[str, datetime.time], dict[str, datetime.time]]:
        highest: dict[str, datetime.time] = {}
        lowest: dict[str, datetime.time] = {}
        for key, frame in self.ticker_dates_dict.items():
            high_series = frame["High"]
            low_series = frame["Low"]
            high_max = high_series.max()
            low_min = low_series.min()
            high_time_str = frame.loc[frame["High"] == high_max, "Time"].iloc[0]
            low_time_str = frame.loc[frame["Low"] == low_min, "Time"].iloc[0]
            highest[key] = datetime.datetime.strptime(high_time_str, "%H:%M").time()
            lowest[key] = datetime.datetime.strptime(low_time_str, "%H:%M").time()
        if hist:
            self._plot_histogram(highest, lowest)
        return highest, lowest

    def intraday_analysis(self) -> None:
        for _key, frame in self.ticker_dates_dict.items():
            print("Min:", frame["Low"].min())
            print("Max:", frame["High"].max())
