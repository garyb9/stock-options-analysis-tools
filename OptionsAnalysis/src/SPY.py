from OptsAnalysis import OptsAnalysis

# SPY (S&P 500 ETF) example
filePath = r'../data/spy.xls'
Opts = OptsAnalysis()
Opts.BuildFromTS(filePath)

for date in Opts.GetExpirationDates():
    Opts.PlotHistByDate(date, 'Both')

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
