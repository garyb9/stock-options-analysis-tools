import os
import re
import requests
import pandas as pd
from dateutil.parser import parse
from bs4 import BeautifulSoup
from sec_edgar_downloader import Downloader
from SEC_Params import SUPPORTED_FILINGS


class SEC_Object:
    """A :class:`SEC_Object` object.
    """
    def __init__(self):
        self.name = ""
        self.ticker = ""
        self.filling = ""
        self.period = ""
        self.url = ""
        self.code = ""
        self.df_table_dict = {}


class SEC_Analysis:
    """A :class:`SEC_Analysis` object.
    """
    def __init__(self, ticker, fillings):
        """Constructor for the :class:`SEC_Analysis` class."""
        if ticker:
            self.ticker = str(ticker).strip().upper().lstrip("0")
        else:
            raise Exception("No ticker given")  # TODO add ticker search

        if fillings:
            self.fillings = fillings
        else:
            raise Exception("Filling types should be a list consisting of at least one supported filling type: ", SUPPORTED_FILINGS)

        self.urls = {}
        self.master_dict = {}

    def get_urls(self, num_filings_to_download=None, after_date=None, before_date=None, include_amends=False, download=False):
        dl = Downloader()
        for filing_type in self.fillings:
            print("Getting " + filing_type + " of " + self.ticker)
            # urls[filing_type] = dl.get(filing_type, self.ticker, include_amends=include_amends, download=False)
            self.urls[filing_type] = dl.get(filing_type=filing_type, ticker_or_cik=self.ticker, num_filings_to_download=num_filings_to_download,
                                            after_date=after_date, before_date=before_date, include_amends=include_amends, download=download)

        print("Done")
        return self.urls

    def get_tables_to_dict(self, soup):
        document_texts = []

        for filing_document in soup.find_all('document'):
            if 'XML' == filing_document.type.find(text=True, recursive=False).strip():  # document id
                document_texts.append(str(filing_document.find('text').extract()))

        df_table_dict = {}
        for html_doc_text in document_texts:
            doc_soup = BeautifulSoup(html_doc_text, "html.parser")

            table_df = pd.DataFrame()
            for table_row in doc_soup.find_all('tr'):
                headers = [element.get_text(strip=True) for element in table_row.find_all('th')]
                data = [element.get_text(strip=True) for element in table_row.find_all('td')]

                for idx, val in enumerate(data):
                    if idx:  # not the first column
                        if '$' in val:  # stripping dollar signs for excel parsing
                            data[idx] = val.strip('$')
                        if val.startswith('(') and val.endswith(')'):  # negative value
                            data[idx] = '-' + val.strip('(').strip(')')

                if headers:
                    table_df = table_df.append([headers], ignore_index=True)
                if data:
                    if data[0] == 'X':
                        break
                    else:
                        table_df = table_df.append([data], ignore_index=True)

            cash_flow_substrings = ["consolidated", "cash", "flow"]
            balance_sheet_substrings = ["consolidated", "balance", "sheet"]
            income_statement_substrings = ["consolidated", "income", "statement"]
            if not table_df.empty:
                table_name = table_df[0][0]
                if all([substring in table_name.lower() for substring in cash_flow_substrings]) or \
                        all([substring in table_name.lower() for substring in balance_sheet_substrings]) or \
                        all([substring in table_name.lower() for substring in income_statement_substrings]):
                    df_table_dict[table_name] = table_df

        return df_table_dict

    def is_date(string, fuzzy=False):
        """
        Return whether the string can be interpreted as a date.

        :param string: str, string to check for date
        :param fuzzy: bool, ignore unknown tokens in string if True
        """
        try:
            parse(string, fuzzy=fuzzy)
            return True

        except ValueError:
            return False

    def explore_urls(self):
        if not self.urls:
            raise Exception("No urls found. forgot get_urls()?")
        for key, lstval in self.urls.items():
            for value in lstval:
                response = requests.get(value.url)
                soup = BeautifulSoup(response.content, 'lxml')

                obj = SEC_Object()
                obj.ticker = self.ticker
                obj.filling = key
                obj.code = value.filename.strip(".txt")
                obj.url = value.url
                obj.df_table_dict = self.get_tables_to_dict(soup)
                for text in soup.text.split('\n'):
                    if "CONFORMED PERIOD OF REPORT" in text:
                        period = text.split('\t')[-1]
                        obj.period = period[0:3]
                        break

    def write_to_xlsx(self, df_table_dict, ticker, writeDir):
        excelFile = writeDir + r'\\' + ticker + '.xlsx'
        sheet_name = ticker
        writer = pd.ExcelWriter(excelFile, engine='xlsxwriter')
        writer.sheets[sheet_name] = writer.book.add_worksheet(sheet_name)

        prev_df_shape = 1
        for key, df in df_table_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, startrow=prev_df_shape, startcol=0)
            prev_df_shape += df.shape[0] + 5

        writer.save()
        os.startfile(excelFile)

