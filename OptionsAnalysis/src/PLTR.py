from OptsAnalysis import OptsAnalysis

# SPY (S&P 500 ETF) example
filePath = r'../data/pltr.xls'
Opts = OptsAnalysis()
# Opts.BuildFromTS(filePath)
Opts.BuildFromWeb('PLTR')

for date in Opts.GetExpirationDates():
    Opts.PlotHistByDate(date, 'Both')

Opts.PlotTimelineWithErrors()
"""
Opts.PrintExpirationDates()
expDates = Opts.GetExpirationDates()
Opts.PlotHistByDate(expDates[0], 'Volume')
Opts.PlotHistByDate(expDates[0], 'OpenInt')
Opts.PlotHistByDate(expDates[0], 'Both')
Opts.PlotHist('Volume')
Opts.PlotHist('OpenInt')
Opts.PlotHist('Both')
"""