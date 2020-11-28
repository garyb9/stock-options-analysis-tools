#!/usr/bin/env python

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as dates
import pandas as pd
from pandas.tseries import converter
import datetime
import FinvizScraper

class StockData:
    """A :class:`StockData` object.
    """
    def __init__(self, ticker, refticker=None, dataDir=None):
        """Constructor for the :class:`StockData` class."""
        # Main Ticker name
        if ticker:
            self.ticker = str(ticker).strip().upper().lstrip("0")
        else:
            raise Exception("No ticker given")

        # Reference Ticker name
        if refticker:
            self.refticker = str(refticker).strip().upper().lstrip("0")

        # Data Directory
        if dataDir:
            self.dataDir = dataDir
        else:
            self.dataDir = r'../data'

        # Main Ticker Data Frame and Dates Dictionary of Data Frames
        self.tickerDF = self._getData(self.ticker, self.dataDir)
        self.tickerDatesDict = self._getDatesDict(self.tickerDF)

        # Reference Ticker Data Frame and Dates Dictionary of Data Frames
        if refticker:
            self.reftickerDF = self._getData(self.refticker, self.dataDir)
            self.reftickerDatesDict = self._getDatesDict(self.reftickerDF)

    @staticmethod
    def _getData(ticker, dataDir):
        df = None
        for name in os.listdir(dataDir):
            if ticker in name:
                df = pd.read_csv(os.path.join(dataDir, name))
                df = df.drop(['OverBot', 'OverSld', 'OI', 'Vol.1', 'Up', 'Down'], axis=1,
                             errors='ignore')  # drop columns, ignore if not found
                df = df[df.all(axis=1)].reset_index(drop=True)  # re format data frame
        if df is None:
            raise Exception("Did not find "+ticker+" data")
        return df

    @staticmethod
    def _getDatesDict(df):
        retDict = {}
        converter.register()
        dateKeys = []
        for date in df['Date']:
            dateKeys.append(datetime.datetime.strptime(date, '%m/%d/%Y').strftime('%d/%m/%Y'))
        df['Date'] = dateKeys
        dateKeys = list(dict.fromkeys(dateKeys))  # remove duplicates from dates
        for count, key in enumerate(dateKeys):
            retDict[key] = df.loc[df['Date'] == dateKeys[count]]
        return retDict

    @staticmethod
    def _plotDict(Dict, Dict2=None, annotate=True):
        fig, ax = plt.subplots()
        color = 'tab:red'
        ax.set_xlabel('time (s)')
        ax.set_ylabel('exp', color=color)
        keys = [datetime.datetime.strptime(date, '%d/%m/%Y').strftime('%m/%d/%Y') for date in
                list(Dict.keys())]
        idx = pd.DatetimeIndex(data=keys, start=list(Dict.keys())[0], end=list(Dict.keys())[-1])
        values = list(Dict.values())
        ax.plot_date(idx.to_pydatetime(), values, color=color, fmt='v-')
        ax.xaxis.set_minor_locator(dates.DayLocator())
        ax.xaxis.set_minor_formatter(dates.DateFormatter('%d'))
        ax.xaxis.grid(True, which="minor")
        ax.yaxis.grid()
        ax.xaxis.set_major_locator(dates.MonthLocator())
        ax.xaxis.set_major_formatter(dates.DateFormatter('%d\n%b\n%Y'))
        if annotate:
            for x, y in zip(keys, values):
                ax.annotate("{:.2f}".format(y), (x, y), textcoords="offset points", xytext=(0, 10), ha='center')
        ax.tick_params(axis='y', labelcolor=color)

        if Dict2:
            ax2 = ax.twinx()  # instantiate a second axes that shares the same x-axis
            color = 'tab:blue'
            ax2.set_xlabel('time (s)')
            ax2.set_ylabel('exp', color=color)
            keys = [datetime.datetime.strptime(date, '%d/%m/%Y').strftime('%m/%d/%Y') for date in
                    list(Dict2.keys())]
            idx = pd.DatetimeIndex(data=keys, start=list(Dict2.keys())[0], end=list(Dict2.keys())[-1])
            values = list(Dict2.values())
            ax2.plot_date(idx.to_pydatetime(), values, color=color, fmt='v-')
            ax2.xaxis.set_minor_locator(dates.DayLocator())
            ax2.xaxis.set_minor_formatter(dates.DateFormatter('%d'))
            ax2.xaxis.grid(True, which="minor")
            ax2.yaxis.grid()
            ax2.xaxis.set_major_locator(dates.MonthLocator())
            ax2.xaxis.set_major_formatter(dates.DateFormatter('%d\n%b\n%Y'))
            if annotate:
                for x, y in zip(keys, values):
                    ax2.annotate("{:.2f}".format(y), (x, y), textcoords="offset points", xytext=(0, 10), ha='center')
            ax2.tick_params(axis='y', labelcolor=color)

        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        plt.show()

    @staticmethod
    def _plotHistogram(Dict, Dict2=None):
        bins = [item.strftime("%H:%M") for item in pd.date_range("16:30", "23:00", freq="1min")]
        binsDict1 = dict.fromkeys(bins, 0)
        for occ in [item.strftime("%H:%M") for item in list(Dict.values())]:
            if occ in binsDict1:
                binsDict1[occ] += 1
        if Dict2:
            binsDict2 = dict.fromkeys(bins, 0)
            for occ in [item.strftime("%H:%M") for item in list(Dict2.values())]:
                if occ in binsDict2:
                    binsDict2[occ] += 1
        plt.bar(binsDict1.keys(), binsDict1.values(), alpha=0.5, width=1.0, color='red')
        plt.bar(binsDict2.keys(), binsDict2.values(), alpha=0.5, width=1.0, color='blue')
        plt.show()

    def _dateAnalysis(self, CorrelationDict):
        # get all dates where correlation was outside of [mean-std, mean+std]
        values = np.array(list(CorrelationDict.values()))
        minVal = max(-1, values.mean() - values.std())
        maxVal = min(1, values.mean() + values.std())
        rareDates = [item for item in list(CorrelationDict.keys()) if
                     (CorrelationDict[item] <= minVal) or (CorrelationDict[item] >= maxVal)]
        print("Dates where 'something weird' happened:\n", rareDates)
        print("-" * 100)
        finviz = FinvizScraper.FinvizScraper(self.ticker)
        for raredate in rareDates:
            for newsObj in finviz.news:
                if raredate == newsObj.date:
                    print("Found news at:", raredate)
                    print(newsObj.string)
                    print("Link:", newsObj.link)
                    print("-"*100)

    def CorrelationWithRef(self, dateAnalysis=True, plot=True):
        # Assuming same dates for reference ticker and main ticker
        if self.refticker is None:
            raise Exception("No Reference Ticker was provided")

        CorrelationDict = {}
        for key in self.tickerDatesDict:
            # Calculate average for Main Ticker
            Open = self.tickerDatesDict[key]['Open']
            Close = self.tickerDatesDict[key]['Close']
            Low = self.tickerDatesDict[key]['Low']
            High = self.tickerDatesDict[key]['High']
            Average1 = (Open+Close+Low+High)/4

            # Calculate average for Reference Ticker
            Open = self.reftickerDatesDict[key]['Open']
            Close = self.reftickerDatesDict[key]['Close']
            Low = self.reftickerDatesDict[key]['Low']
            High = self.reftickerDatesDict[key]['High']
            Average2 = (Open+Close+Low+High)/4

            CorrelationDict[key] = Average1.corr(Average2)

        values = np.array(list(CorrelationDict.values()))
        print("Calculated Correlation of", self.ticker, "to", self.refticker)
        print("Correlation Median:\t\t", "%.4f" % np.median(values))
        print("Correlation Mean:\t\t", "%.4f" % values.mean())
        print("Correlation Variance:\t", "%.4f" % values.var())
        print("Correlation STD:\t\t", "%.4f" % values.std())

        if dateAnalysis:
            self._dateAnalysis(CorrelationDict)

        if plot:
            self._plotDict(CorrelationDict)

        return CorrelationDict

    def HighestLowestPointDaily(self, hist=True):
        HighestPointsDailyTime = {}
        LowestPointsDailyTime = {}
        for key in self.tickerDatesDict:
            High = self.tickerDatesDict[key]['High']
            Low = self.tickerDatesDict[key]['Low']
            df = self.tickerDatesDict[key]
            HighTime = df[df['High'] == High.max()]['Time']
            HighestPointsDailyTime[key]  = datetime.datetime.strptime(HighTime.values[0], '%H:%M').time()
            LowTime = df[df['High'] == High.min()]['Time']
            LowestPointsDailyTime[key] = datetime.datetime.strptime(LowTime.values[0], '%H:%M').time()

        if hist:
            self._plotHistogram(HighestPointsDailyTime, LowestPointsDailyTime)

    def IntradayAnalysis(self):
        # TODO fill with analysis
        for key, value in self.tickerDatesDict.items():
            print("Min:", value['Low'].min())
            print("Max:", value['High'].max())


def main():
    TQQQ = StockData(ticker="OIIM", refticker="SMH")
    TQQQ.CorrelationWithRef(plot=True)
    TQQQ.HighestLowestPointDaily()

if __name__ == "__main__":
    main()


