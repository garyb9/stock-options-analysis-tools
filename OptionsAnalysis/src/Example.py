import numpy as np
from OptsAnalysis import OptsAnalysis

# PLTR (Palantir) example
filePath = r'../data/pltr.xls'
Opts = OptsAnalysis(filePath)
print(Opts.ticker + " Expiration Dates available:")
expDates = Opts.GetExpirationDates()
print(expDates)

Opts.PlotHistByDate(expDates[0], 'Volume')
Opts.PlotHistByDate(expDates[0], 'Open Int')
Opts.PlotVolumeOpenIntHistByDate(expDates[0])
Opts.PlotHistCumulative('Volume')
Opts.PlotHistCumulative('Open Int')
Opts.PlotVolumeOpenIntHistCumulative()

# NIO (Palantir) example
filePath = r'../data/nio.xls'
Opts = OptsAnalysis(filePath)
print(Opts.ticker + " Expiration Dates available:")
expDates = Opts.GetExpirationDates()
print(expDates)

Opts.PlotHistByDate(expDates[0], 'Volume')
Opts.PlotHistByDate(expDates[0], 'Open Int')
Opts.PlotVolumeOpenIntHistByDate(expDates[0])
Opts.PlotHistCumulative('Volume')
Opts.PlotHistCumulative('Open Int')
Opts.PlotVolumeOpenIntHistCumulative()
