# Stock-Options-Analysis-Tools

Graphical and statistical analysis utilities for the stock market, options, derivatives, and finance.

- **Python:** 3.12+
- **License:** [AGPL-3.0-or-later](LICENSE)

## Install

From the repo root:

```bash
pip install -e ".[dev]"
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install -e ".[dev]"
```

## Quick start

### Options analysis (recommended: yfinance)

```python
from options_analysis import OptsAnalysis

opts = OptsAnalysis()
opts.BuildFromYFinance("PLTR")
opts.PrintExpirationDates()
exp_dates = opts.GetExpirationDates()
if exp_dates:
    opts.PlotHistByDate(exp_dates[0], "Both")
```

### From a TradeStation export file

```python
opts = OptsAnalysis()
opts.BuildFromTS("data/pltr.xlsx")  # or .xls / .csv
opts.PlotHist("Volume")
```

### Example scripts

```bash
python scripts/example_web.py    # yfinance: PLTR, first expiration
python scripts/example_ts.py    # TradeStation file from data/
python scripts/run_stock.py     # PLTR + NIO from web
```

## Features / modules

| Module | Description |
| ------ | ----------- |
| **options_analysis** | Load options chains from multiple sources; aggregate by strike (volume / open interest); weighted mean & std; histograms and timeline plots. |
| **stock_data** | Load ticker CSV data, split by date; correlation with a reference ticker; optional Finviz news for outlier dates. |
| **sec_analysis** | SEC EDGAR filings (8-K, 10-K, 10-Q); fetch URLs, extract tables, export to Excel. |
| **finviz_scraper** | Scrape Finviz quote page for snapshot params and news. |

## Options data sources

Options analysis supports several data sources through a single interface:

| Source | Type | API key | Notes |
| ------ | ---- | ------- | ----- |
| **TradeStation file** | Local | No | Export to `.xls`, `.xlsx`, or `.csv`; file name = `<ticker>.<ext>`. |
| **yfinance** | Remote | No | Recommended; programmatic, no scraping. `BuildFromYFinance(ticker)`. |
| **Yahoo (scrape)** | Remote | No | Fallback; HTML can change. `BuildFromWeb(ticker)`. |
| **Market Data (marketdata.app)** | Remote | Yes (free tier) | 100 req/day, 24h delayed; optional adapter. |

Additional sources (e.g. OpenBB, Polygon) can be added as adapters returning the same `OptionsSourceResult` shape.

## Development

- **Tests:** `pytest` (from repo root, with `PYTHONPATH=src` if not installed: `PYTHONPATH=src pytest`).
- **Lint / format:** [Ruff](https://docs.astral.sh/ruff/) — `ruff check src tests scripts` and `ruff format src tests scripts`.
- **Types:** [mypy](https://mypy-lang.org/) — `mypy src`.
- **Optional:** [pre-commit](https://pre-commit.com/) — install hooks so Ruff and mypy run on commit (see below).

### Pre-commit (optional)

```bash
pip install pre-commit
pre-commit install
```

A `.pre-commit-config.yaml` is provided to run Ruff and mypy.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
