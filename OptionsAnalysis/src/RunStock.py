from OptsAnalysis import OptsAnalysis

Opts = OptsAnalysis()
Opts.BuildFromWeb('PLTR')

Opts.PlotTimelineWithErrors()

for date in Opts.GetExpirationDates():
    Opts.PlotHistByDate(date, 'Both')
