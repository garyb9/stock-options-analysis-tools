import os
from pathlib import Path
import pandas as pd
from sec_edgar_downloader import Downloader
import xlsxwriter


def download_fillings_for_ticker(dl, ticker, fillings, include_amends=False):
    for filing_type in fillings:
        print("Downloading " + filing_type + " of " + ticker)
        dl.get(filing_type, ticker, include_amends=include_amends)  # including amends such as 10-k/A
    print("Done")


def find_sec_fillings_by_year(dir, ticker, year):
    resPaths = []
    dir += r"\\" + ticker
    pathlist = Path(dir).glob('**/*.txt')
    for path in pathlist:
        print("SEC file found - " + str(path))
        file = open(path, "r")
        for line in file.readlines():
            if ("CONFORMED PERIOD OF REPORT" in line) and (year in line):
                resPaths.append(path)
                break
        file.close()
    return resPaths


def Quarter_Column(month):
    Quarters = [0, 3, 6, 9, 12]
    if month <= Quarters[1]:
        return ["Q1", 0]
    if Quarters[1] < month <= Quarters[2]:
        return ["Q2", 2]
    if Quarters[2] < month <= Quarters[3]:
        return ["Q3", 4]
    if Quarters[3] < month <= Quarters[4]:
        return ["Q4", 6]


def write_to_xlsx(secPaths, ticker, writeDir):
    CompanyName = ''
    excelFile = writeDir + 'cash_flow_calc.xlsx'
    workbook = xlsxwriter.Workbook(excelFile)
    worksheet = workbook.add_worksheet()
    for path in secPaths:
        amend = False
        Q, C = '', 0
        R = 1
        file = open(path, "r")
        tags = ['\n', '\t', ' ', ':']
        for line in file.readlines():
            if "CONFORMED SUBMISSION TYPE" in line and "10-K/A" in line: amend = True; break  # TODO temp pass for amends such as 10-K/A
            if "CONFORMED PERIOD OF REPORT" in line:
                for tag in tags:
                    line = line.replace("CONFORMED PERIOD OF REPORT", '').replace(tag, '')
                month = int(line[4:6])
                Q, C = Quarter_Column(month)
                continue
            if "COMPANY CONFORMED NAME" in line:
                if CompanyName == '':
                    for tag in tags:
                        CompanyName = line.replace("COMPANY CONFORMED NAME", '').replace(tag, '')
                    worksheet.write(0, 0, ticker)
                    worksheet.write(0, 2, CompanyName)
                continue
            #if "stock outstanding" in line:
            #    print(line)
        if amend: continue  # TODO temp pass for amends such as 10-K/A
        worksheet.write(R, C, Q)
        file.close()
    workbook.close()
    os.startfile(excelFile)


def main():
    ticker = "XLNX"
    fillings = ['10-K']
    baseDir = r'data'
    dl = Downloader(baseDir)
    saveDir = str(dl.download_folder) + r"\sec_edgar_filings" + r'\\' + ticker
    if os.path.isdir(saveDir):
        print("Found SEC fillings dir in - " + saveDir)
    else:
        print("Downloading to - " + saveDir)
        download_fillings_for_ticker(dl, ticker, fillings)
    secPaths = find_sec_fillings_by_year(saveDir, ticker, "2019")
    '''
    
    writeDir = saveDir + r"\\" + ticker + r"\\"
    write_to_xlsx(secPaths, ticker, writeDir)
    '''

if __name__ == "__main__":
    main()
