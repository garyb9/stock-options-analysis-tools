from OptsAnalysis import OptsAnalysis

# NIO
Opts = OptsAnalysis()
Opts.BuildFromWeb('NIO')

for date in Opts.GetExpirationDates():
    Opts.PlotHistByDate(date, 'Both')
