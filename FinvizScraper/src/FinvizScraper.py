import os
import re
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import datetime
import dateutil.parser as parser

class FinvizScraper:
    """A :class:`FinvizScraper` object.
    """
    class NewsObject:
        def __init__(self, date=None, time=None, string=None, link=None):
            self.date = date
            self.time = time
            self.string = string
            self.link = link

    def __init__(self, ticker):
        """Constructor for the :class:`FinvizScraper` class."""
        if ticker:
            self.ticker = str(ticker).strip().upper().lstrip("0")
        else:
            raise Exception("No ticker given")  # TODO add ticker search

        baseURL = r'https://finviz.com/quote.ashx?t='
        tickerURl = baseURL + self.ticker.upper()
        resp = requests.get(tickerURl, headers={"User-Agent": "Mozilla/5.0"})  # passing user agent for granting access
        if not resp.ok:
            raise Exception("Response Error - " + resp.reason)
        soup = BeautifulSoup(resp.content, 'html.parser')
        self.params = self._ScrapeParams(soup)
        self.news = self._ScrapeNews(soup)

    def _ScrapeParams(self, soup):
        params = {}
        for table in soup.find_all("table", {"class": "snapshot-table2"}):
            for table_row in table.find_all('tr'):
                key = ""
                for count, table_col in enumerate(table_row.find_all('td')):
                    value = table_col.string
                    if not count % 2:
                        key = value
                    else:
                        # some keys like 'EPS next Y' have two separate values, one of them is a percentage
                        if '%' in value:
                            if '%' not in key:
                                key += ' %'
                        if key in params.keys():
                            key += ' %'
                        params[key] = value
        return params

    def _ScrapeNews(self, soup):
        news = []
        for table in soup.find_all("table", {"class": "fullview-news-outer"}):
            lastDate = ""
            for table_row in table.find_all('tr'):
                newsObj = self.NewsObject()
                for count, table_col in enumerate(table_row.find_all('td')):
                    if not count % 2:
                        value = table_col.string.split(' ')
                        if len(value) == 2:
                            newsObj.date = parser.parse(value[0]).strftime('%d/%m/%Y')
                            newsObj.time = parser.parse(value[1]).strftime('%I:%M%p')
                        else:
                            newsObj.date = lastDate
                            newsObj.time = parser.parse(value[0]).strftime('%I:%M%p')
                        lastDate = newsObj.date
                    else:
                        newsObj.string = table_col.text
                        for link in table_col.find_all('a', href=True):
                            newsObj.link = link['href']
                news.append(newsObj)
        return news

    def GetKeys(self):
        return list(self.params.keys())

    def PrintKeys(self):
        # 12 rows, 6 columns
        np.set_printoptions(edgeitems=30, linewidth=100000,
                            formatter=dict(float=lambda x: "%.3g" % x))
        print(np.array(list(self.params.keys())).reshape(12, 6).transpose())

def main():
    TQQQ = FinvizScraper('TQQQ')
    for news in TQQQ.news:
        print(news.date, news.string, news.link)

if __name__ == "__main__":
    main()