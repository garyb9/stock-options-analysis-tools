"""Scrape Finviz quote page for snapshot params and news."""

from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser


@dataclass
class NewsItem:
    """Single news row from Finviz."""

    date: str
    time: str
    string: str
    link: str


class FinvizScraper:
    """Scrape finviz.com quote page for a ticker (params + news)."""

    def __init__(self, ticker: str) -> None:
        if not ticker:
            raise ValueError("No ticker given")
        self.ticker = str(ticker).strip().upper().lstrip("0")
        url = f"https://finviz.com/quote.ashx?t={self.ticker}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if not resp.ok:
            raise RuntimeError(f"Response Error - {resp.reason}")
        soup = BeautifulSoup(resp.content, "html.parser")
        self.params = self._scrape_params(soup)
        self.news = self._scrape_news(soup)

    def _scrape_params(self, soup: BeautifulSoup) -> dict[str, str]:
        params: dict[str, str] = {}
        for table in soup.find_all("table", class_="snapshot-table2"):
            for row in table.find_all("tr"):
                key = ""
                for i, col in enumerate(row.find_all("td")):
                    val = col.get_text(strip=True) if col.string is None else col.string
                    if val is None:
                        val = ""
                    if i % 2 == 0:
                        key = val
                    else:
                        if "%" in val and "%" not in key:
                            key = key + " %"
                        if key in params:
                            key = key + " %"
                        params[key] = val
        return params

    def _scrape_news(self, soup: BeautifulSoup) -> list[NewsItem]:
        news: list[NewsItem] = []
        last_date = ""
        for table in soup.find_all("table", class_="fullview-news-outer"):
            for row in table.find_all("tr"):
                item = NewsItem(date="", time="", string="", link="")
                for i, col in enumerate(row.find_all("td")):
                    if i % 2 == 0:
                        parts = col.get_text(strip=True).split()
                        if len(parts) == 2:
                            item.date = dateutil_parser.parse(parts[0]).strftime("%d/%m/%Y")
                            item.time = dateutil_parser.parse(parts[1]).strftime("%I:%M%p")
                        else:
                            item.date = last_date
                            item.time = dateutil_parser.parse(parts[0]).strftime("%I:%M%p")
                        last_date = item.date
                    else:
                        item.string = col.get_text(strip=True)
                        a = col.find("a", href=True)
                        if a:
                            item.link = a["href"]
                news.append(item)
        return news

    def get_keys(self) -> list[str]:
        return list(self.params.keys())

    def print_keys(self) -> None:
        keys = list(self.params.keys())
        n = len(keys)
        cols = 6
        rows = (n + cols - 1) // cols
        for r in range(rows):
            row = keys[r * cols : (r + 1) * cols]
            print(row)
