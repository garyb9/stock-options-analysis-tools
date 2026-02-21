"""Yahoo Finance HTML scrape source (fallback when yfinance unavailable)."""

from datetime import datetime
from threading import Lock, Thread

import pandas as pd
import requests
from bs4 import BeautifulSoup

from options_analysis.sources.base import OptionsSourceResult
from shared.utils import get_timer, start_timer


def _parse_yahoo_options_page(
    ticker: str, date_code: str, verbose: bool = True
) -> tuple[str, dict[str, pd.DataFrame]]:
    """Fetch one expiration's options from Yahoo options page. Returns (date_str, {calls, puts})."""
    url = f"https://finance.yahoo.com/quote/{ticker}/options?date={date_code}"
    if verbose:
        print("Getting Options Data from:", url)
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if not resp.ok:
        raise RuntimeError(f"Response Error - {resp.reason}")
    soup = BeautifulSoup(resp.content, "html.parser")
    opts_dict: dict[str, pd.DataFrame] = {"calls": pd.DataFrame(), "puts": pd.DataFrame()}
    for table in soup.find_all("table"):
        first_row: list[str] = []
        thead = table.find("thead")
        if thead:
            tr = thead.find("tr")
            if tr:
                for th in tr.find_all("th"):
                    first_row.append(th.get_text(strip=True))
        replacements = {"Open Interest": "OpenInt", "Implied Volatility": "ImpVol"}
        first_row = [replacements.get(x, x) for x in first_row]
        rows: list[list[str]] = []
        for tbody in table.find_all("tbody"):
            for tr in tbody.find_all("tr"):
                rows.append([td.get_text(strip=True) for td in tr.find_all("td")])
        if not first_row or not rows:
            continue
        df = pd.DataFrame(data=rows, columns=first_row)
        table_classes = table.get("class") or []
        if "calls" in table_classes:
            opts_dict["calls"] = df
        if "puts" in table_classes:
            opts_dict["puts"] = df
    return date_code, opts_dict


def load_yahoo_scrape(ticker: str, verbose: bool = True) -> OptionsSourceResult:
    """Scrape Yahoo Finance options pages for ticker (multi-threaded)."""
    ticker = str(ticker).strip().upper().lstrip("0")
    base_url = f"https://finance.yahoo.com/quote/{ticker}/options"
    if verbose:
        print("Getting Dates from:", base_url)
    resp = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"})
    if not resp.ok:
        raise RuntimeError(f"Response Error - {resp.reason}")
    soup = BeautifulSoup(resp.content, "html.parser")
    date_codes: list[tuple[str, str]] = []
    dates_list: list[str] = []
    for opt in soup.find_all("option"):
        value = opt.get("value")
        text = opt.get_text(strip=True)
        if not value or not text:
            continue
        try:
            dt = datetime.strptime(text, "%B %d, %Y")
            date_str = dt.strftime("%d/%m/%Y")
            date_codes.append((value, date_str))
            dates_list.append(date_str)
        except ValueError:
            continue
    if verbose:
        print("Done")

    big_dict: dict[str, dict[str, pd.DataFrame]] = {}
    mutex = Lock()

    def worker(dc: tuple[str, str]) -> None:
        start = start_timer()
        try:
            code, date_str = dc
            _, opts = _parse_yahoo_options_page(ticker, code, verbose=verbose)
            with mutex:
                big_dict[date_str] = opts
                if verbose:
                    print(
                        "Request for",
                        date_str,
                        "ended after",
                        get_timer(start),
                        "seconds",
                    )
        except Exception as e:
            with mutex:
                if verbose:
                    print("Request failed for", dc, ":", e)

    threads = [Thread(target=worker, args=(dc,)) for dc in date_codes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return OptionsSourceResult(ticker=ticker, dates=dates_list, big_dict=big_dict)


class YahooScrapeSource:
    """Options data by scraping Yahoo Finance HTML (fallback)."""

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose

    def fetch(self, ticker: str) -> OptionsSourceResult:
        """Scrape options for symbol."""
        return load_yahoo_scrape(ticker, verbose=self.verbose)
