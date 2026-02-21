"""SEC EDGAR filings: get URLs, parse tables, export to Excel."""

from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sec_edgar_downloader import Downloader

from sec_analysis.params import SUPPORTED_FILINGS


class SEC_Object:
    """Holds metadata and extracted tables for one filing."""

    def __init__(self) -> None:
        self.name = ""
        self.ticker = ""
        self.filling = ""
        self.period = ""
        self.url = ""
        self.code = ""
        self.df_table_dict: dict[str, pd.DataFrame] = {}


class SEC_Analysis:
    """Fetch SEC filing URLs for a ticker and extract financial tables."""

    def __init__(self, ticker: str, filings: list[str]) -> None:
        if not ticker:
            raise ValueError("No ticker given")
        if not filings:
            raise ValueError(
                "Filing types should be a list of at least one of:",
                list(SUPPORTED_FILINGS),
            )
        self.ticker = str(ticker).strip().upper().lstrip("0")
        self.fillings = filings
        self.urls: dict[str, Any] = {}
        self.master_dict: dict[str, Any] = {}

    def get_urls(
        self,
        num_filings_to_download: int | None = None,
        after_date: int | None = None,
        before_date: int | None = None,
        include_amends: bool = False,
        download: bool = False,
    ) -> dict[str, Any]:
        """Fetch filing URLs from SEC EDGAR."""
        dl = Downloader()
        for filing_type in self.fillings:
            print("Getting", filing_type, "of", self.ticker)
            self.urls[filing_type] = dl.get(
                filing_type=filing_type,
                ticker_or_cik=self.ticker,
                num_filings_to_download=num_filings_to_download,
                after_date=after_date,
                before_date=before_date,
                include_amends=include_amends,
                download=download,
            )
        print("Done")
        return self.urls

    def get_tables_to_dict(self, soup: BeautifulSoup) -> dict[str, pd.DataFrame]:
        """Extract cash flow, balance sheet, income statement tables from filing HTML."""
        document_texts: list[str] = []
        for doc in soup.find_all("document"):
            type_el = doc.find("type")
            if type_el and type_el.find(text=True, recursive=False):
                type_str = type_el.find(text=True, recursive=False).strip()
                if type_str == "XML":
                    text_el = doc.find("text")
                    if text_el:
                        document_texts.append(str(text_el.extract()))
        df_table_dict: dict[str, pd.DataFrame] = {}
        for html_doc in document_texts:
            doc_soup = BeautifulSoup(html_doc, "html.parser")
            rows: list[list[str]] = []
            for table_row in doc_soup.find_all("tr"):
                headers = [el.get_text(strip=True) for el in table_row.find_all("th")]
                data = [el.get_text(strip=True) for el in table_row.find_all("td")]
                for idx in range(1, len(data)):
                    val = data[idx]
                    if "$" in val:
                        data[idx] = val.strip("$")
                    if val.startswith("(") and val.endswith(")"):
                        data[idx] = "-" + val.strip("()")
                if headers:
                    rows.append(headers)
                if data:
                    if data[0] == "X":
                        break
                    rows.append(data)
            if not rows:
                continue
            table_df = pd.DataFrame(rows)
            if table_df.empty:
                continue
            table_name = str(table_df.iloc[0, 0]).lower()
            cash_flow = all(s in table_name for s in ["consolidated", "cash", "flow"])
            balance = all(s in table_name for s in ["consolidated", "balance", "sheet"])
            income = all(s in table_name for s in ["consolidated", "income", "statement"])
            if cash_flow or balance or income:
                df_table_dict[table_df.iloc[0, 0]] = table_df
        return df_table_dict

    def explore_urls(self) -> None:
        """Fetch each filing URL and parse tables into SEC_Object."""
        if not self.urls:
            raise RuntimeError("No urls found. Call get_urls() first.")
        for key, lst_val in self.urls.items():
            for value in lst_val:
                resp = requests.get(value.url)
                soup = BeautifulSoup(resp.content, "lxml")
                obj = SEC_Object()
                obj.ticker = self.ticker
                obj.filling = key
                obj.code = value.filename.removesuffix(".txt")
                obj.url = value.url
                obj.df_table_dict = self.get_tables_to_dict(soup)
                for line in soup.get_text().split("\n"):
                    if "CONFORMED PERIOD OF REPORT" in line:
                        parts = line.split("\t")
                        if parts:
                            obj.period = parts[-1][:3]
                        break

    def write_to_xlsx(
        self,
        df_table_dict: dict[str, pd.DataFrame],
        ticker: str,
        write_dir: str | Path,
    ) -> str:
        """Write extracted tables to an Excel file. Returns path to file."""
        write_dir = Path(write_dir)
        write_dir.mkdir(parents=True, exist_ok=True)
        path = write_dir / f"{ticker}.xlsx"
        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            start_row = 0
            for _name, df in df_table_dict.items():
                df.to_excel(writer, sheet_name=ticker, startrow=start_row, startcol=0)
                start_row += df.shape[0] + 5
        return str(path)
