import numpy as np
from OptsAnalysis import OptsAnalysis

# PLTR (Palantir) example
Opts = OptsAnalysis()
Opts.BuildFromWeb("PLTR")
Opts.PrintExpirationDates()

expDates = Opts.GetExpirationDates()
Opts.PlotHistByDate(expDates[0], 'Volume')
Opts.PlotHistByDate(expDates[0], 'OpenInt')
Opts.PlotHistByDate(expDates[0], 'Both')