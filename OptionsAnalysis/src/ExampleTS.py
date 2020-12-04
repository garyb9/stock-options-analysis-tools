import numpy as np
from OptsAnalysis import OptsAnalysis

# PLTR (Palantir) example
filePath = r'../data/pltr.xls'
Opts = OptsAnalysis()
Opts.BuildFromTS(filePath)
Opts.PrintExpirationDates()

expDates = Opts.GetExpirationDates()
Opts.PlotHistByDate(expDates[0], 'Volume')
Opts.PlotHistByDate(expDates[0], 'OpenInt')
Opts.PlotHistByDate(expDates[0], 'Both')
Opts.PlotHist('Volume')
Opts.PlotHist('OpenInt')
Opts.PlotHist('Both')

# NIO example
filePath = r'../data/nio.xls'
Opts.BuildFromTS(filePath)
Opts.PrintExpirationDates()

expDates = Opts.GetExpirationDates()
Opts.PlotHistByDate(expDates[0], 'Volume')
Opts.PlotHistByDate(expDates[0], 'OpenInt')
Opts.PlotHistByDate(expDates[0], 'Both')
Opts.PlotHist('Volume')
Opts.PlotHist('OpenInt')
Opts.PlotHist('Both')
