from OptsAnalysis import OptsAnalysis

Opts = OptsAnalysis()
Opts.BuildFromWeb('pltr')
#filePath = r'../data/pltr.xls'
# Opts.BuildFromTS(filePath)

#Opts.PlotTimelineWithErrors()

Opts.PlotHistByDate(Opts.GetExpirationDates()[0], 'Volume')
Opts.PlotHistByDate(Opts.GetExpirationDates()[0], 'Both')

"""
for date in Opts.GetExpirationDates():
    Opts.PlotHistByDate(date, 'Both')
"""

