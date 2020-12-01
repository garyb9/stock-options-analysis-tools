#!/usr/bin/env python

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import locale
import enum

class OptsAnalysis:
    """A :class:`OptsAnalysis` object.
       Disclaimer - only supports TradeStation formatting of option spreads!
    """
    class Values(enum.Enum):
        Both = 0
        Volume = 1
        OpenInt = 2

    def __init__(self, filePath):
        """Constructor for the :class:`OptsAnalysis` class.
            File should be called in the format:
            <ticker>.[xls, xlsx, csv]
        """
        if filePath:
            if type(filePath) is str:
                self.filePath = filePath.lower()
                if self.filePath.endswith(('.xls', '.xlsx', '.csv')):
                    """
                        taking values to skip the "C A L L S - P U T S" first line
                        keeping calls on the left to strike price puts on the right
                    """
                    try:
                        ticker = self.filePath.split('/')[-1].split("\\")[-1].split('.')[0]
                        self.ticker = str(ticker).strip().upper().lstrip("0")
                    except:
                        print("Bad file name format, please provide in the format: <ticker>.[xls, xlsx, csv]")
                        return
                    tempDF = pd.DataFrame(pd.read_excel(self.filePath).values)
                    firstRow = [x.replace(" ", "") for x in list(tempDF.iloc[0])]
                    strikeIndex = [x.lower() for x in firstRow].index('strike')  # middle of the pack
                    dates = []
                    indexes = []
                    for idx, val in enumerate(list(tempDF.iloc[:, 0])):
                        if type(val) is str and val != "Pos":
                            splt = val.split("\t")
                            date = splt[0].replace("   ", "")
                            # expectedMove = splt[2].replace("(Custom=(", "").replace("))", "")
                            dates.append(date)
                            indexes.append(idx)
                    self.bigDict = {}
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

                        self.bigDict[val] = {'calls': calls, 'puts': puts}

                else:
                    raise Exception("Only excel files or csv files are allowed")
            else:
                raise Exception("Only string are allowed as an argument")
        else:
            raise Exception("No file given")

    def GetExpirationDates(self):
        return list(self.bigDict.keys())

    def GetValuesString(self, val):
        if val == self.Values.Both or val == "Both":
            return "Volume and Open Interest"
        elif val == self.Values.Volume or val == "Volume":
            return "Volume"
        elif val == self.Values.OpenInt or val == "OpenInt":
            return "Open Interest"
        else:
            return

    def PlotHistByDate(self, date, val=Values.Both):
        """ date format example = 27 Nov 20
            val = Volume or Open Int
        """
        if date not in self.bigDict:
            print("Date given not in available expiration dates:", self.GetExpirationDates())
            return
        if val not in self.Values.__members__:
            print("Value given is not a part of Values class")
            return
        locale.setlocale(locale.LC_ALL, 'en_US')
        x = self.bigDict[date]['calls']['Strike'].to_numpy().astype(float)

        if val == self.Values.Both or val == "Both":
            yCalls = np.asarray([v.replace(",", "") for v in self.bigDict[date]['calls']['Volume']], dtype=np.int) \
                + np.asarray([v.replace(",", "") for v in self.bigDict[date]['calls']['OpenInt']], dtype=np.int)
            yPuts = np.asarray([v.replace(",", "") for v in self.bigDict[date]['puts']['Volume']], dtype=np.int) \
                + np.asarray([v.replace(",", "") for v in self.bigDict[date]['puts']['OpenInt']], dtype=np.int)
        else:
            yCalls = np.asarray([v.replace(",", "") for v in self.bigDict[date]['calls'][val]], dtype=np.int)
            yPuts = np.asarray([v.replace(",", "") for v in self.bigDict[date]['puts'][val]], dtype=np.int)

        sumCalls = np.sum(yCalls)
        sumPuts = np.sum(yPuts)
        strCalls = locale.format_string("%d", sumCalls, grouping=True)
        strPuts = locale.format_string("%d", sumPuts, grouping=True)
        perCalls = str(round(100 * float(sumCalls)/float(sumCalls + sumPuts), 2)) + '%'
        perPuts = str(round(100 * float(sumPuts)/float(sumCalls + sumPuts), 2)) + '%'

        plt.bar(x, yCalls, alpha=0.5, width=1.0, color='blue', label='Calls = ' + strCalls + ', ' + perCalls)
        plt.bar(x, yPuts, alpha=0.5, width=1.0, color='red', label='Puts = ' + strPuts + ', ' + perPuts)
        plt.title(self.ticker + ' Options ' + self.GetValuesString(val) + ', Expiration Date - ' + date)
        plt.xlabel('Strike')
        plt.ylabel(self.GetValuesString(val) + ' Count')
        plt.legend(loc='upper left')
        plt.show()

    def PlotHistCumulative(self, val):
        """ val = Volume or Open Int """
        if val not in self.Values.__members__:
            print("Value given is not a part of Values class")
            return
        callsDict = {}
        putsDict = {}
        for key in self.bigDict.keys():
            x = self.bigDict[key]['calls']['Strike'].to_numpy().astype(float)
            if val == self.Values.Both or val == "Both":
                yCalls = np.asarray([v.replace(",", "") for v in self.bigDict[key]['calls']['Volume']], dtype=np.int) \
                    + np.asarray([v.replace(",", "") for v in self.bigDict[key]['calls']['OpenInt']], dtype=np.int)
            else:
                yCalls = np.asarray([v.replace(",", "") for v in self.bigDict[key]['calls'][val]], dtype=np.int)
            for i in range(len(x)):
                if x[i] not in callsDict:
                    callsDict[x[i]] = yCalls[i]
                else:
                    callsDict[x[i]] += yCalls[i]

            x = self.bigDict[key]['puts']['Strike'].to_numpy().astype(float)
            if val == self.Values.Both or val == "Both":
                yPuts = np.asarray([v.replace(",", "") for v in self.bigDict[key]['puts']['Volume']], dtype=np.int) \
                    + np.asarray([v.replace(",", "") for v in self.bigDict[key]['puts']['OpenInt']], dtype=np.int)
            else:
                yPuts = np.asarray([v.replace(",", "") for v in self.bigDict[key]['puts'][val]], dtype=np.int)
            for i in range(len(x)):
                if x[i] not in putsDict:
                    putsDict[x[i]] = yPuts[i]
                else:
                    putsDict[x[i]] += yPuts[i]

        locale.setlocale(locale.LC_ALL, 'en_US')
        sumCalls = np.sum(list(callsDict.values()))
        sumPuts = np.sum(list(putsDict.values()))
        strCalls = locale.format_string("%d", sumCalls, grouping=True)
        strPuts = locale.format_string("%d", sumPuts, grouping=True)
        perCalls = str(round(100 * float(sumCalls) / float(sumCalls + sumPuts), 2)) + '%'
        perPuts = str(round(100 * float(sumPuts) / float(sumCalls + sumPuts), 2)) + '%'

        plt.bar(callsDict.keys(), callsDict.values(), alpha=0.5, width=1.0, color='blue', label='Calls = ' + strCalls + ', ' + perCalls)
        plt.bar(putsDict.keys(), putsDict.values(), alpha=0.5, width=1.0, color='red', label='Puts = ' + strPuts + ', ' + perPuts)
        plt.title(self.ticker + ' Options ' + self.GetValuesString(val) + ', All Expiration Dates')
        plt.xlabel('Strike')
        plt.ylabel(self.GetValuesString(val) + ' Count')
        plt.legend(loc='upper left')
        plt.show()
