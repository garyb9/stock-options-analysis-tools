#!/usr/bin/env python

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import locale
import enum
import requests
from bs4 import BeautifulSoup
import datetime

class OptsAnalysis:
    """A :class:`OptsAnalysis` object.
    """
    class Values(enum.Enum):
        Both = 0
        Volume = 1
        OpenInt = 2

    def __init__(self):
        """Constructor for the :class:`OptsAnalysis` class.
        """
        self.Ticker = ""
        self.Dates = []
        self.BigDict = {}

    def GetExpirationDates(self):
        return self.Dates

    def PrintExpirationDates(self):
        print(self.Ticker + " Expiration Dates available:")
        print(self.Dates)

    def GetValuesString(self, val):
        if val == self.Values.Both or val == "Both":
            return "Volume and Open Interest"
        elif val == self.Values.Volume or val == "Volume":
            return "Volume"
        elif val == self.Values.OpenInt or val == "OpenInt":
            return "Open Interest"
        else:
            return

    def BuildFromTS(self, filePath=None):
        """
        Supports TradeStation formatting of option spreads!
        File should be called in the format:
            <ticker>.[xls, xlsx, csv]
        """
        if filePath:
            if type(filePath) is str:
                filePath = filePath.lower()
                if filePath.endswith(('.xls', '.xlsx', '.csv')):
                    """
                        taking values to skip the "C A L L S - P U T S" first line
                        keeping calls on the left to strike price puts on the right
                    """
                    try:
                        ticker = filePath.split('/')[-1].split("\\")[-1].split('.')[0]
                        self.Ticker = str(ticker).strip().upper().lstrip("0")
                    except:
                        print("Bad file name format, please provide in the format: <ticker>.[xls, xlsx, csv]")
                        return
                    tempDF = pd.DataFrame(pd.read_excel(filePath).values)
                    firstRow = [x.replace(" ", "") for x in list(tempDF.iloc[0])]
                    strikeIndex = [x.lower() for x in firstRow].index('strike')  # middle of the pack
                    dates = []
                    indexes = []
                    for idx, val in enumerate(list(tempDF.iloc[:, 0])):
                        if type(val) is str and val != "Pos":
                            date = val.split("\t")[0].replace("   ", "")
                            dates.append(date)
                            indexes.append(idx)
                    self.BigDict = {}
                    for idx, val in enumerate(dates):
                        if idx != len(dates) - 1:
                            endRow = indexes[idx + 1]
                        else:
                            endRow = len(tempDF.index)  # last line

                        calls = pd.DataFrame(tempDF.iloc[indexes[idx] + 1:endRow, :strikeIndex + 1])
                        calls.columns = firstRow[:strikeIndex + 1]
                        calls.index = np.arange(1, len(calls) + 1)
                        calls = calls.drop('Pos', axis=1, errors='ignore')  # drop column, ignore if not found

                        puts = pd.DataFrame(tempDF.iloc[indexes[idx] + 1:endRow, strikeIndex:])
                        puts.columns = firstRow[strikeIndex:]
                        puts.index = np.arange(1, len(puts) + 1)
                        puts = puts.drop('Pos', axis=1, errors='ignore')  # drop column, ignore if not found

                        self.BigDict[val] = {'calls': calls, 'puts': puts}

                    self.Dates = list(self.BigDict.keys())

                else:
                    raise Exception("Only excel files or csv files are allowed")
            else:
                raise Exception("Only string are allowed as an argument")
        else:
            raise Exception("No file given")

    def BuildDatesWeb(self, ticker=None):
        if ticker:
            self.Ticker = str(ticker).strip().upper().lstrip("0")
        else:
            raise Exception("No ticker given")

        # Get Dates and Date codes
        baseURL = r'https://finance.yahoo.com/quote/'
        tickerURl = baseURL + self.Ticker + r'/options'
        dateCodes = []
        self.Dates = []
        print("Getting Dates from: ", tickerURl)
        resp = requests.get(tickerURl, headers={"User-Agent": "Mozilla/5.0"})  # passing user agent for granting access
        if not resp.ok:
            raise Exception("Response Error - " + resp.reason)
        soup = BeautifulSoup(resp.content, 'html.parser')
        for dateCode in soup.find_all("option"):
            dateCodes.append([dateCode.attrs['value'], dateCode.text])
            self.Dates.append(dateCode.text)
        print("Done")
        return dateCodes

    def BuildFromWeb(self, ticker=None):
        dateCodes = self.BuildDatesWeb(ticker=ticker)

        # Get Option Data per date
        baseURL = r'https://finance.yahoo.com/quote/'
        tickerURl = baseURL + self.Ticker + r'/options'
        self.BigDict = {}
        for dateCode in dateCodes:
            dateURL = tickerURl + r'?date=' + dateCode[0]
            print("Getting Options Data from: ", dateURL)
            resp = requests.get(dateURL,
                                headers={"User-Agent": "Mozilla/5.0"})  # passing user agent for granting access
            if not resp.ok:
                raise Exception("Response Error - " + resp.reason)
            soup = BeautifulSoup(resp.content, 'html.parser')
            for table in soup.find_all("table"):
                # Head
                firstRow = []
                for head in table.find_all("thead"):
                    for th in head.find("tr").find_all("th"):
                        firstRow.append(th.text)
                replacements = {'Open Interest': 'OpenInt', 'Implied Volatility': 'ImpVol'}
                firstRow = [replacements.get(x, x) for x in firstRow]

                # Body
                optsRows = []
                for body in table.find_all("tbody"):
                    for tr in body.find_all("tr"):
                        thisRow = []
                        for td in tr.find_all("td"):
                            thisRow.append(td.text)
                        optsRows.append(thisRow)

                optsDF = pd.DataFrame(data=optsRows, columns=firstRow)

                # Calls
                if 'calls' in table.attrs['class']:
                    self.BigDict[dateCode[1]] = {'calls': optsDF}

                # Puts
                if 'puts' in table.attrs['class']:
                    self.BigDict[dateCode[1]] = {'puts': optsDF}

                print(optsDF)

    def StatsPlot(self, stats=True, plot=True, val=Values.Both, start_date=None, end_date=None, allOptions=None, allCalls=None, allPuts=None):
        if start_date is None or end_date is None or allOptions is None or allCalls is None or allPuts is None:
            return

        mean = 0; meanCalls = 0; meanPuts = 0
        std = 0; stdCalls = 0; stdPuts = 0

        for strike in list(allOptions.keys()):
            meanCalls += float(strike * allCalls[strike])
            meanPuts += float(strike * allPuts[strike])
            mean += float(strike * allOptions[strike])

            stdCalls += np.power(float(strike * allCalls[strike]), 2)
            stdPuts += np.power(float(strike * allPuts[strike]), 2)
            std += np.power(float(strike * allOptions[strike]), 2)

        sumCalls = np.sum(list(allCalls.values()))
        sumPuts = np.sum(list(allPuts.values()))
        sumOverall = sumCalls+sumPuts

        meanCalls /= float(sumCalls)
        meanPuts /= float(sumPuts)
        mean /= float(sumCalls + sumPuts)

        stdCalls = np.sqrt(std / np.power(float(sumCalls), 2))
        stdPuts = np.sqrt(std / np.power(float(sumPuts), 2))
        std = np.sqrt(std / np.power(float(sumOverall), 2))

        perCalls = str(round(100 * float(sumCalls) / float(sumOverall), 2)) + '%'
        perPuts = str(round(100 * float(sumPuts) / float(sumOverall), 2)) + '%'

        printStatsStr = "---- " + self.Ticker + ' Options ' + self.GetValuesString(val) + " Stats ----"

        locale.setlocale(locale.LC_ALL, 'en_US')
        strCalls = locale.format_string("%d", sumCalls, grouping=True)
        strPuts = locale.format_string("%d", sumPuts, grouping=True)
        strOverall = locale.format_string("%d", sumOverall, grouping=True)
        widthStr = str(max([len(strCalls), len(strPuts), len(strOverall)]))
        strCalls = '{:<{width}}'.format(strCalls, width=widthStr)
        strPuts = '{:<{width}}'.format(strPuts, width=widthStr)
        strOverall = '{:<{width}}'.format(strOverall, width=widthStr)

        printCallsStr = "Calls:\t" + strCalls + " | Mean = " + "%.2f" % meanCalls + " | STD = ±" + "%.2f" % stdCalls + " | " + perCalls
        printPutsStr = "Puts:\t" + strPuts + " | Mean = " + "%.2f" % meanPuts + " | STD = ±" + "%.2f" % stdPuts + " | " + perPuts
        printAllStr = "All:\t" + strOverall + " | Mean = " + "%.2f" % mean + " | STD = ±" + "%.2f" % std

        start = self.Dates.index(start_date)
        end = self.Dates.index(end_date)

        if start_date == self.Dates[0] and end_date == self.Dates[-1]:
            printExpDatesStr = "All Expiration Dates"
        elif start_date == end_date:
            printExpDatesStr = "Expiring at " + self.Dates[start]
        else:
            printExpDatesStr = "Expiring From " + self.Dates[start] + " Up To " + self.Dates[end]

        if stats:
            print(printStatsStr)
            print("\t", printAllStr)
            print("\t", printCallsStr)
            print("\t", printPutsStr)
            print("-" * len(printStatsStr))

        if plot:
            plt.bar(allCalls.keys(), allCalls.values(), alpha=0.5, width=1.0, color='blue', label=printCallsStr.replace("\t", " ").replace(" |", ","))
            plt.bar(allPuts.keys(), allPuts.values(), alpha=0.5, width=1.0, color='red', label=printPutsStr.replace("\t", " ").replace(" |", ","))
            plt.plot([], [], color='black', label=printAllStr.replace("\t", " ").replace(" |", ","))

            plt.title(self.Ticker + ' Options ' + self.GetValuesString(val) + ", " + printExpDatesStr)
            plt.xlabel('Strike')
            plt.ylabel(self.GetValuesString(val) + ' Count')
            plt.legend(loc='upper left')
            plt.show()

    def PlotHistByDate(self, date, val=Values.Both):
        """ date format example = 27 Nov 20
            val = Volume or Open Int
        """
        if date not in self.BigDict:
            print("Date given not in available expiration dates:", self.GetExpirationDates())
            return
        if val not in self.Values.__members__:
            print("Value given is not a part of Values class")
            return
        locale.setlocale(locale.LC_ALL, 'en_US')
        x = self.BigDict[date]['calls']['Strike'].to_numpy().astype(float)

        if val == self.Values.Both or val == "Both":
            yCalls = np.asarray([v.replace(",", "") for v in self.BigDict[date]['calls']['Volume']], dtype=np.int) \
                + np.asarray([v.replace(",", "") for v in self.BigDict[date]['calls']['OpenInt']], dtype=np.int)
            yPuts = np.asarray([v.replace(",", "") for v in self.BigDict[date]['puts']['Volume']], dtype=np.int) \
                + np.asarray([v.replace(",", "") for v in self.BigDict[date]['puts']['OpenInt']], dtype=np.int)
        else:
            yCalls = np.asarray([v.replace(",", "") for v in self.BigDict[date]['calls'][val]], dtype=np.int)
            yPuts = np.asarray([v.replace(",", "") for v in self.BigDict[date]['puts'][val]], dtype=np.int)

        allOptions = {}; allCalls = {}; allPuts = {}
        for idx, strike in enumerate(x):
            allCalls[strike] = yCalls[idx]
            allPuts[strike] = yPuts[idx]
            allOptions[strike] = yCalls[idx] + yPuts[idx]

        self.StatsPlot(val=val, stats=True, plot=True, start_date=date, end_date=date, allOptions=allOptions, allCalls=allCalls, allPuts=allPuts)

    def PlotHist(self, val=Values.Both, start_date=None, end_date=None):
        """ val = Volume, OpenInt or Both
            start_date = one of available expiration dates
            end_Date = one of available expiration dates, must be later than start_date
        """
        if val not in self.Values.__members__:
            print("Value given is not a part of Values class")
            return

        if start_date is not None:
            if start_date not in self.Dates:
                print("Start Date given not in available expiration dates:", self.Dates)
                return
        else:
            start_date = self.Dates[0]

        if end_date is not None:
            if  end_date not in self.Dates:
                print("End Date given not in available expiration dates:", self.Dates)
                return
        else:
            end_date = self.Dates[-1]

        start = self.Dates.index(start_date)
        end = self.Dates.index(end_date)
        if start > end:
            print("End Date given should be equal or before Start Date")
            return

        allOptions = {}; allCalls = {}; allPuts = {}
        for key in self.Dates[start:end]:
            x = self.BigDict[key]['calls']['Strike'].to_numpy().astype(float)
            if val == self.Values.Both or val == "Both":
                yCalls = np.asarray([v.replace(",", "") for v in self.BigDict[key]['calls']['Volume']], dtype=np.int) \
                    + np.asarray([v.replace(",", "") for v in self.BigDict[key]['calls']['OpenInt']], dtype=np.int)
            else:
                yCalls = np.asarray([v.replace(",", "") for v in self.BigDict[key]['calls'][val]], dtype=np.int)

            for i in range(len(x)):
                allCalls[x[i]] = allCalls.get(x[i], 0) + yCalls[i]
                allOptions[x[i]] = allOptions.get(x[i], 0) + yCalls[i]

            x = self.BigDict[key]['puts']['Strike'].to_numpy().astype(float)
            if val == self.Values.Both or val == "Both":
                yPuts = np.asarray([v.replace(",", "") for v in self.BigDict[key]['puts']['Volume']], dtype=np.int) \
                    + np.asarray([v.replace(",", "") for v in self.BigDict[key]['puts']['OpenInt']], dtype=np.int)
            else:
                yPuts = np.asarray([v.replace(",", "") for v in self.BigDict[key]['puts'][val]], dtype=np.int)

            for i in range(len(x)):
                allPuts[x[i]] = allPuts.get(x[i], 0) + yPuts[i]
                allOptions[x[i]] = allOptions.get(x[i], 0) + yPuts[i]

        self.StatsPlot(val=val, stats=True, plot=True, start_date=start_date, end_date=end_date, allOptions=allOptions, allCalls=allCalls, allPuts=allPuts)
