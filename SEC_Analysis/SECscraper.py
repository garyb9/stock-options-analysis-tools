import os
import requests
import utils
import pandas as pd
from bs4 import BeautifulSoup
import xlsxwriter
from sec_edgar_downloader import Downloader
import SEC_Analysis as SEC

def main():
    start = utils.start_timer()

    baseDir = r'data'
    ticker = 'XLNX'
    fillings = ['10-K', "10-Q"]
    # urls = get_url_fillings_for_ticker(ticker, fillings)

    # url = r"https://www.sec.gov/Archives/edgar/data/743988/000074398820000020/0000743988-20-000020.txt"
    # df_table_dict = get_tables_to_dict(url)

    # write_to_xlsx(df_table_dict, ticker, baseDir)
    sec = SEC.SEC_Analysis(ticker, fillings)
    urls = sec.get_urls(after_date=20200101,before_date=20200507)
    sec.explore_urls()

if __name__ == "__main__":
    main()