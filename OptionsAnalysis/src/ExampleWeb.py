import numpy as np
from OptsAnalysis import OptsAnalysis

# PLTR (Palantir) example
Opts = OptsAnalysis()
Opts.BuildFromWeb("PLTR")
Opts.PrintExpirationDates()