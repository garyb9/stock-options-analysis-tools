from OptsAnalysis import OptsAnalysis

Opts = OptsAnalysis()
Opts.BuildFromWeb('CLF')

for date in Opts.GetExpirationDates():
    Opts.PlotHistByDate(date, 'Both')

Opts.PlotTimelineWithErrors()