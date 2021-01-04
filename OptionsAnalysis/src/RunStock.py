from OptsAnalysis import OptsAnalysis

Opts = OptsAnalysis()
Opts.BuildFromWeb('pltr')
Opts.PlotHistByDate(Opts.GetExpirationDates()[0], 'Volume')
Opts.PlotHistByDate(Opts.GetExpirationDates()[0], 'Both')


Opts.BuildFromWeb('nio')
Opts.PlotHistByDate(Opts.GetExpirationDates()[0], 'Volume')
Opts.PlotHistByDate(Opts.GetExpirationDates()[0], 'Both')
