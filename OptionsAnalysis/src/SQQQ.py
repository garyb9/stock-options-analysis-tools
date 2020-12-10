from OptsAnalysis import OptsAnalysis

# SQQQ
Opts = OptsAnalysis()
Opts.BuildFromWeb('SQQQ')

for date in Opts.GetExpirationDates():
    Opts.PlotHistByDate(date, 'Both')
