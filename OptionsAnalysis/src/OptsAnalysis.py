#!/usr/bin/env python

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import locale
import enum
import requests
from bs4 import BeautifulSoup
import utils
from threading import Thread, Lock
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
            date = datetime.datetime.strptime(dateCode.text, '%B %d, %Y').strftime('%d/%m/%Y')
            dateCodes.append([dateCode.attrs['value'], date])
            self.Dates.append(date)
        print("Done")
        return dateCodes

    def ReqThread(self, dateCode, mutex):
        startTimer = utils.start_timer()
        dateURL = r'https://finance.yahoo.com/quote/' + self.Ticker + r'/options?date=' + dateCode[0]
        mutex.acquire()
        try:
            print("Getting Options Data from: ", dateURL)
        finally:
            mutex.release()
        resp = requests.get(dateURL,
                            headers={"User-Agent": "Mozilla/5.0"})  # passing user agent for granting access
        if not resp.ok:
            raise Exception("Response Error - " + resp.reason)
        soup = BeautifulSoup(resp.content, 'html.parser')
        optsDict = {'calls': None, 'puts': None}
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
                optsDict['calls'] = optsDF

            # Puts
            if 'puts' in table.attrs['class']:
                optsDict['puts'] = optsDF

        mutex.acquire()
        try:
            self.BigDict[dateCode[1]] = optsDict
            print("Request Thread for: " + dateURL + " ended after " + utils.get_timer(startTimer) + " seconds")
        finally:
            mutex.release()

    def BuildFromWeb(self, ticker=None):
        dateCodes = self.BuildDatesWeb(ticker=ticker)

        # Get Option Data per date
        self.BigDict = {}
        mutex = Lock()
        threads = []
        for dateCode in dateCodes:
            t = Thread(target=self.ReqThread, args=(dateCode, mutex))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    def GetDatesStartEnd(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = self.Dates[0]
        else:
            if start_date not in self.Dates:
                print("Start Date given not in available expiration dates:", self.Dates)
                return

        if end_date is None or self.Dates.index(end_date) == len(self.Dates) - 1:
            start = self.Dates.index(start_date)
            dates = self.Dates[start:]
        else:
            if end_date not in self.Dates:
                print("End Date given not in available expiration dates:", self.Dates)
                return
            start = self.Dates.index(start_date)
            end = self.Dates.index(end_date)
            if start > end:
                print("End Date given should be equal or before Start Date")
                return
            elif start == end:
                dates = self.Dates[start:start + 1]
            else:
                dates = self.Dates[start:end + 1]

        return dates if dates else []

    def GetOptsDF(self, val=Values.Both, dates=None):
        """ val = Volume, OpenInt or Both
            start_date = one of available expiration dates
            end_Date = one of available expiration dates, must be later than start_date
        """
        if val not in self.Values.__members__:
            print("Value given is not a part of Values class")
            return
        """
        allOptions = {}; allCalls = {}; allPuts = {}
        for key in dates:
            xCalls = np.asarray(self.BigDict[key]['calls']['Strike'], dtype=np.float)
            if val == self.Values.Both or val == "Both":
                yCalls = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls']['Volume']], dtype=np.int) \
                         + np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls']['OpenInt']], dtype=np.int)
            else:
                yCalls = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls'][val]], dtype=np.int)

            for idx, strike in enumerate(xCalls):
                allCalls[strike]    = allCalls.get(strike, 0) + yCalls[idx]
                allOptions[strike]  = allOptions.get(strike, 0) + allCalls[strike]

            xPuts = np.asarray(self.BigDict[key]['puts']['Strike'], dtype=np.float)
            if val == self.Values.Both or val == "Both":
                yPuts = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts']['Volume']], dtype=np.int) \
                        + np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts']['OpenInt']], dtype=np.int)
            else:
                yPuts = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts'][val]], dtype=np.int)

            for idx, strike in enumerate(xPuts):
                allPuts[strike]     = allPuts.get(strike, 0) + yPuts[idx]
                allOptions[strike]  = allOptions.get(strike, 0) + allPuts[strike]

        return {'calls': allCalls, 'puts': allPuts, 'all': allOptions}
        """
        df = pd.DataFrame(columns=['calls', 'puts', 'all'])
        for key in dates:
            xCalls = np.asarray(self.BigDict[key]['calls']['Strike'], dtype=np.float)
            if val == self.Values.Both or val == "Both":
                yCalls = np.asarray(
                    [v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls']['Volume']], dtype=np.int) \
                         + np.asarray(
                    [v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls']['OpenInt']], dtype=np.int)
            else:
                yCalls = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls'][val]],
                                    dtype=np.int)

            for idx, strike in enumerate(xCalls):
                if strike in df.index:
                    df.loc[strike] += [yCalls[idx], 0, yCalls[idx]]
                else:
                    df.loc[strike] = [yCalls[idx], 0, yCalls[idx]]

            xPuts = np.asarray(self.BigDict[key]['puts']['Strike'], dtype=np.float)
            if val == self.Values.Both or val == "Both":
                yPuts = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts']['Volume']],
                                   dtype=np.int) \
                        + np.asarray(
                    [v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts']['OpenInt']], dtype=np.int)
            else:
                yPuts = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts'][val]],
                                   dtype=np.int)

            for idx, strike in enumerate(xPuts):
                if strike in df.index:
                    df.loc[strike] += [0, yPuts[idx], yPuts[idx]]
                else:
                    df.loc[strike] = [0, yPuts[idx], yPuts[idx]]

        df = df.sort_index()
        return df

    def StatsPlot(self, stats=True, plot=True, val=Values.Both, dates=None, optsDF=None):
        if dates is None or dates is []:
            print("Empty list of dates given")
            return
        # startTimer = utils.start_timer()

        sumCalls = optsDF['calls'].sum()
        sumPuts = optsDF['puts'].sum()
        sumOverall = optsDF['all'].sum()

        """
        mean = 0; meanCalls = 0; meanPuts = 0
        std = 0; stdCalls = 0; stdPuts = 0

        # Calls
        for strike in list(allCalls.keys()):
            meanCalls += float(strike * allCalls[strike]) / sumCalls
        for strike in list(allCalls.keys()):
            stdCalls += np.power(float((strike - meanCalls)), 2) * allCalls[strike] / sumCalls
        stdCalls = np.sqrt(stdCalls)

        # Puts
        for strike in list(allPuts.keys()):
            meanPuts += float(strike * allPuts[strike]) / sumPuts
        for strike in list(allPuts.keys()):
            stdPuts += np.power(float((strike - meanPuts)), 2) * allPuts[strike] / sumPuts
        stdPuts = np.sqrt(stdPuts)

        # All Options
        for strike in list(allOptions.keys()):
            mean += float(strike * allOptions[strike]) / sumOverall
        for strike in list(allOptions.keys()):
            std += np.power(float((strike - mean)), 2) * allOptions[strike] / sumOverall
        std = np.sqrt(std)
        """
        meanCalls = np.average(optsDF.index, weights=optsDF['calls'])
        stdCalls = np.sqrt(np.average((optsDF.index - meanCalls) ** 2, weights=optsDF['calls']))

        meanPuts = np.average(optsDF.index, weights=optsDF['puts'])
        stdPuts = np.sqrt(np.average((optsDF.index - meanPuts) ** 2, weights=optsDF['puts']))

        meanAll = np.average(optsDF.index, weights=optsDF['all'])
        stdAll = np.sqrt(np.average((optsDF.index - meanAll) ** 2, weights=optsDF['all']))

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

        strMeanCalls = "%.2f" % meanCalls
        strMeanPuts = "%.2f" % meanPuts
        strMeanAll = "%.2f" % meanAll
        widthStr = str(max([len(strMeanCalls), len(strMeanPuts), len(strMeanAll)]))
        strMeanCalls = '{:<{width}}'.format(strMeanCalls, width=widthStr)
        strMeanPuts = '{:<{width}}'.format(strMeanPuts, width=widthStr)
        strMeanAll = '{:<{width}}'.format(strMeanAll, width=widthStr)

        strStdCalls = "%.2f" % stdCalls
        strStdPuts = "%.2f" % stdPuts
        strStdAll = "%.2f" % stdAll
        widthStr = str(max([len(strStdCalls), len(strStdPuts), len(strStdAll)]))
        strStdCalls = '{:<{width}}'.format(strStdCalls, width=widthStr)
        strStdPuts = '{:<{width}}'.format(strStdPuts, width=widthStr)
        strStdAll = '{:<{width}}'.format(strStdAll, width=widthStr)

        printCallsStr = "Calls:\t" + strCalls + " | Mean = " + strMeanCalls + " | STD = ±" + strStdCalls + " | " + perCalls
        printPutsStr = "Puts:\t" + strPuts + " | Mean = " + strMeanPuts + " | STD = ±" + strStdPuts + " | " + perPuts
        printAllStr = "All:\t" + strOverall + " | Mean = " + strMeanAll + " | STD = ±" + strStdAll

        if dates[0] == self.Dates[0] and dates[-1] == self.Dates[-1]:
            printExpDatesStr = "All Expiration Dates"
        elif len(dates) == 1:
            printExpDatesStr = "Expiring at " + dates[0]
        else:
            printExpDatesStr = "Expiring From " + dates[0] + " Up To " + dates[-1]

        if stats:
            print(printStatsStr)
            print("\t", printAllStr)
            print("\t", printCallsStr)
            print("\t", printPutsStr)
            print("-" * len(printStatsStr))
            # utils.print_time(startTimer)

        if plot:
            plt.bar(optsDF.index, optsDF['calls'], alpha=0.5, width=1.0, color='blue',
                    label=printCallsStr.replace("\t", " ").replace(" |", ","))
            plt.bar(optsDF.index, optsDF['puts'], alpha=0.5, width=1.0, color='red',
                    label=printPutsStr.replace("\t", " ").replace(" |", ","))
            plt.plot([], [], color='black', label=printAllStr.replace("\t", " ").replace(" |", ","))
            plt.title(self.Ticker + ' Options ' + self.GetValuesString(val) + ", " + printExpDatesStr)
            plt.xlabel('Strike')
            plt.ylabel(self.GetValuesString(val) + ' Count')
            plt.legend(loc='upper left')
            plt.show()

    def PlotHistByDate(self, date, val=Values.Both):
        optsDF = self.GetOptsDF(val=val, dates=[date])

        self.StatsPlot(val=val, stats=True, plot=True, dates=[date], optsDF=optsDF)

    def PlotHist(self, val=Values.Both, start_date=None, end_date=None):
        dates = self.GetDatesStartEnd(start_date=start_date, end_date=end_date)

        optsDF = self.GetOptsDF(val=val, dates=dates)

        self.StatsPlot(val=val, stats=True, plot=True, dates=dates, optsDF=optsDF)

    def PlotTimelineWithErrors(self, val=Values.Both, start_date=None, end_date=None):
        dates = self.GetDatesStartEnd(start_date=start_date, end_date=end_date)

        df = pd.DataFrame(columns=['calls', 'callsErr', 'perCalls', 'puts', 'putsErr', 'perPuts', 'all', 'allErr'])
        for key in dates:
            xCalls = np.asarray(self.BigDict[key]['calls']['Strike'], dtype=np.float)
            if val == self.Values.Both or val == "Both":
                yCalls = np.asarray(
                    [v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls']['Volume']], dtype=np.int) \
                         + np.asarray(
                    [v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls']['OpenInt']], dtype=np.int)
            else:
                yCalls = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['calls'][val]],
                                    dtype=np.int)

            meanCalls = np.average(xCalls, weights=yCalls)
            stdCalls = np.sqrt(np.average((xCalls - meanCalls) ** 2, weights=yCalls))

            xPuts = np.asarray(self.BigDict[key]['puts']['Strike'], dtype=np.float)
            if val == self.Values.Both or val == "Both":
                yPuts = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts']['Volume']],
                                   dtype=np.int) \
                        + np.asarray(
                    [v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts']['OpenInt']], dtype=np.int)
            else:
                yPuts = np.asarray([v.replace(",", "").replace("-", "0") for v in self.BigDict[key]['puts'][val]],
                                   dtype=np.int)

            meanPuts = np.average(xPuts, weights=yPuts)
            stdPuts = np.sqrt(np.average((xPuts - meanPuts) ** 2, weights=yPuts))

            dfAll = pd.DataFrame(columns=['all'])
            for idx, strike in enumerate(xCalls):
                if strike in dfAll.index:
                    dfAll.loc[strike] += yCalls[idx]
                else:
                    dfAll.loc[strike] = yCalls[idx]

            for idx, strike in enumerate(xPuts):
                if strike in dfAll.index:
                    dfAll.loc[strike] += yPuts[idx]
                else:
                    dfAll.loc[strike] = yPuts[idx]

            meanAll = np.average(dfAll.index, weights=dfAll['all'])
            stdAll = np.sqrt(np.average((dfAll.index - meanAll) ** 2, weights=dfAll['all']))
            perCalls = round(100 * float(np.sum(yCalls)) / float(dfAll['all'].sum()), 2)
            perPuts = round(100 * float(np.sum(yPuts)) / float(dfAll['all'].sum()), 2)

            df.loc[key] = [meanCalls, stdCalls, perCalls, meanPuts, stdPuts, perPuts, meanAll, stdAll]

        # df = df.sort_index()
        fig, ax = plt.subplots()

        # Calls
        ax.errorbar(df.index, df['calls'], yerr=df['callsErr'], alpha=0.25, color='blue', ecolor='blue',
                    linestyle=':',
                    capsize=5,
                    elinewidth=3,
                    markeredgewidth=3,
                    label='Calls')

        for x, y, z in zip(df.index, df['calls'], df['perCalls']):
            fy = "{:.2f}".format(y)
            per = str(z) + '%'
            ax.annotate(fy+', '+per, (x, y), textcoords="offset points", xytext=(0, 10),
                        ha='right', va='top', color='navy')

        # Puts
        ax.errorbar(df.index, df['puts'], yerr=df['putsErr'], alpha=0.25, color='red', ecolor='red',
                    linestyle=':',
                    capsize=5,
                    elinewidth=3,
                    markeredgewidth=3,
                    label='Puts')

        for x, y, z in zip(df.index, df['puts'], df['perPuts']):
            fy = "{:.2f}".format(y)
            per = str(z) + '%'
            ax.annotate(fy+', '+per, (x, y), textcoords="offset points", xytext=(0, 10),
                        ha='left', va='top', color='firebrick')

        # All
        ax.errorbar(df.index, df['all'], yerr=df['allErr'], alpha=0.5, color='black', ecolor='black',
                    linestyle='-',
                    capsize=5,
                    elinewidth=3,
                    markeredgewidth=3,
                    label='All Options')

        for x, y in zip(df.index, df['all']):
            ax.annotate("{:.2f}".format(y), (x, y), textcoords="offset points", xytext=(0, 10),
                        ha='center', va='bottom', weight='bold')

        ax.grid(b=True, linestyle='--')

        if dates[0] == self.Dates[0] and dates[-1] == self.Dates[-1]:
            printExpDatesStr = "All Expiration Dates"
        elif len(dates) == 1:
            printExpDatesStr = "Expiring at " + dates[0]
        else:
            printExpDatesStr = "Expiring From " + dates[0] + " Up To " + dates[-1]

        plt.title(self.Ticker + " Options Mean and STD spreads, " + printExpDatesStr)
        plt.xlabel('Expiration Dates')
        plt.ylabel('Mean and STD Count')
        plt.legend(loc='upper left')
        plt.show()
