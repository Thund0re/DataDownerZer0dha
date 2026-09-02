"""
Yahoo Finance Financial Data Scraper
- Ticker-only input
- Annual statements only
- Saves files in per-ticker folders
"""

import csv
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────

INPUT_FILE = "ticker.csv"
OUTPUT_DIR = "msn_financial_data"
LOG_DIR = "logs"

CONFIG = {
    "max_retries": 3,
    "delay_between_requests": 0.5,
    "delay_between_tickers": 1.0,
    "include_empty_cols": False,
    "sort_descending": True,
}

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────────────────────

log_file = Path(LOG_DIR) / f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class StatementResult:
    statement_type: str
    success: bool
    filepath: Optional[str] = None
    rows: int = 0
    columns: int = 0
    error: Optional[str] = None


@dataclass
class TickerResult:
    ticker: str
    success: bool
    company_name: Optional[str] = None
    statements: List[StatementResult] = field(default_factory=list)
    total_rows: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class SessionStats:
    total_tickers: int = 0
    successful: int = 0
    failed: int = 0
    total_rows: int = 0
    total_files: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def success_rate(self) -> float:
        return (self.successful / max(self.total_tickers, 1)) * 100


# ──────────────────────────────────────────────────────────────────────────────
# TICKER LOADING
# ──────────────────────────────────────────────────────────────────────────────

def is_valid_ticker(value: str) -> bool:
    if not value:
        return False
    value = str(value).strip().upper()
    if len(value) < 1 or len(value) > 10:
        return False
    if value.lower() in {"ticker", "symbol", "stock", "company", "name"}:
        return False
    import re
    return bool(re.match(r"^[A-Z0-9.\-]+$", value))


def load_tickers(filepath: Path) -> List[str]:
    if not filepath.exists():
        logger.error(f"Input file not found: {filepath}")
        return []

    tickers = []
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        logger.error("Ticker CSV is empty.")
        return []

    start_idx = 1 if rows and rows[0] and "ticker" in rows[0][0].lower() else 0

    for row in rows[start_idx:]:
        if not row:
            continue
        ticker = row[0].strip().upper()
        if is_valid_ticker(ticker) and ticker not in tickers:
            tickers.append(ticker)

    return tickers


def create_sample_csv(filepath: Path):
    sample = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker"])
        for t in sample:
            writer.writerow([t])
    logger.info(f"✅ Created sample file: {filepath}")


# ──────────────────────────────────────────────────────────────────────────────
# SCRAPER
# ──────────────────────────────────────────────────────────────────────────────

class YahooFinanceScraper:
    STATEMENT_CONFIG = {
        "income": {
            "name": "Income Statement",
            "annual_attr": "income_stmt",
            "filename": "income",
            "icon": "📄",
        },
        "balance": {
            "name": "Balance Sheet",
            "annual_attr": "balance_sheet",
            "filename": "balance_sheet",
            "icon": "📊",
        },
        "cashflow": {
            "name": "Cash Flow",
            "annual_attr": "cashflow",
            "filename": "cash_flow",
            "icon": "💰",
        },
    }

    def __init__(self, output_dir: str, config: Dict = None):
        self.output_dir = Path(output_dir)
        self.config = config or CONFIG
        self.stats = SessionStats()

    def _retry_with_backoff(self, func, *args, **kwargs):
        max_retries = self.config["max_retries"]
        base_delay = self.config["delay_between_requests"]
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt}/{max_retries} failed: {e}. Retry in {delay:.1f}s...")
                time.sleep(delay)

        logger.error(f"All {max_retries} attempts failed: {last_error}")
        return None

    def _clean_financial_df(self, df: pd.DataFrame, ticker: str, statement_type: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.copy().T
        df.index = pd.to_datetime(df.index, errors="coerce").strftime("%Y-%m-%d")
        df.index.name = "Date"
        df = df.reset_index()

        df.insert(0, "Ticker", ticker)
        df.insert(1, "Statement", statement_type)

        if not self.config["include_empty_cols"]:
            df = df.dropna(axis=1, how="all")

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date", ascending=not self.config["sort_descending"])
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

        return df.reset_index(drop=True)

    def _fetch_statement(self, stock: yf.Ticker, statement_key: str) -> pd.DataFrame:
        cfg = self.STATEMENT_CONFIG[statement_key]
        df = self._retry_with_backoff(getattr, stock, cfg["annual_attr"])
        if df is not None and not df.empty:
            return df
        return pd.DataFrame()

    def _save_statement(self, df: pd.DataFrame, ticker: str, statement_key: str) -> Tuple[bool, str]:
        cfg = self.STATEMENT_CONFIG[statement_key]

        ticker_dir = self.output_dir / ticker.upper()
        ticker_dir.mkdir(parents=True, exist_ok=True)

        filepath = ticker_dir / f"{ticker.upper()}_{cfg['filename']}.csv"

        try:
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            return True, str(filepath)
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")
            return False, ""

    def scrape_statement(self, stock: yf.Ticker, ticker: str, statement_key: str) -> StatementResult:
        cfg = self.STATEMENT_CONFIG[statement_key]
        result = StatementResult(statement_type=cfg["name"], success=False)

        try:
            logger.info(f"  {cfg['icon']} Fetching {cfg['name']}...")
            raw_df = self._fetch_statement(stock, statement_key)

            if raw_df.empty:
                result.error = "No data returned"
                logger.warning(f"  ⚠️ No {cfg['name']} data available")
                return result

            cleaned_df = self._clean_financial_df(raw_df, ticker, cfg["name"])

            if cleaned_df.empty:
                result.error = "Data became empty after cleaning"
                return result

            success, filepath = self._save_statement(cleaned_df, ticker, statement_key)

            if success:
                result.success = True
                result.filepath = filepath
                result.rows = len(cleaned_df)
                result.columns = len(cleaned_df.columns)
                logger.info(f"  ✅ Saved {cfg['name']}: {result.rows} rows × {result.columns} cols")
            else:
                result.error = "Failed to save file"

            time.sleep(self.config["delay_between_requests"])

        except Exception as e:
            result.error = str(e)
            logger.error(f"  ❌ Error fetching {cfg['name']}: {e}")

        return result

    def scrape_ticker(self, ticker: str) -> TickerResult:
        result = TickerResult(ticker=ticker, success=False, start_time=datetime.now())

        logger.info(f"\n{'═'*60}")
        logger.info(f"🚀 Scraping: {ticker}")
        logger.info(f"{'═'*60}")

        try:
            stock = yf.Ticker(ticker)

            info = self._retry_with_backoff(lambda: stock.info)
            if not info:
                result.error = "Could not fetch ticker info"
                logger.error(f"❌ Invalid or delisted ticker: {ticker}")
                return result

            result.company_name = info.get("shortName") or info.get("longName") or ticker
            logger.info(f"🏢 Company: {result.company_name}")

            for statement_key in self.STATEMENT_CONFIG:
                stmt_result = self.scrape_statement(stock, ticker, statement_key)
                result.statements.append(stmt_result)
                result.total_rows += stmt_result.rows

            result.success = any(s.success for s in result.statements)
            if not result.success:
                result.error = "No statements could be retrieved"

        except Exception as e:
            result.error = str(e)
            logger.error(f"❌ Unexpected error for {ticker}: {e}")

        result.end_time = datetime.now()
        return result

    def scrape_all(self, tickers: List[str]) -> List[TickerResult]:
        self.stats = SessionStats(total_tickers=len(tickers), start_time=datetime.now())
        results = []

        logger.info(f"\n{'█'*60}")
        logger.info("  STARTING SCRAPING SESSION")
        logger.info(f"  Tickers: {len(tickers)}")
        logger.info(f"  Output: {self.output_dir}")
        logger.info(f"{'█'*60}")

        for i, ticker in enumerate(tickers, 1):
            logger.info(f"\n📋 Progress: [{i}/{len(tickers)}]")
            result = self.scrape_ticker(ticker)
            results.append(result)

            if result.success:
                self.stats.successful += 1
                self.stats.total_rows += result.total_rows
                self.stats.total_files += sum(1 for s in result.statements if s.success)
            else:
                self.stats.failed += 1

            if i < len(tickers):
                time.sleep(self.config["delay_between_tickers"])

        self.stats.end_time = datetime.now()
        return results

    def print_summary(self, results: List[TickerResult]):
        rows = []
        for r in results:
            stmt_status = {s.statement_type: "✅" if s.success else "❌" for s in r.statements}
            rows.append({
                "Ticker": r.ticker,
                "Company": r.company_name or "N/A",
                "Status": "✅ Success" if r.success else "❌ Failed",
                "Income": stmt_status.get("Income Statement", "❌"),
                "Balance": stmt_status.get("Balance Sheet", "❌"),
                "Cash Flow": stmt_status.get("Cash Flow", "❌"),
                "Rows": r.total_rows,
                "Error": r.error or "",
            })

        summary_df = pd.DataFrame(rows)

        print(f"\n{'═'*80}")
        print("  📊 SCRAPING SUMMARY REPORT")
        print(f"{'═'*80}")
        print(f"\n  ⏱️  Duration: {self.stats.duration_seconds:.1f} seconds")
        print(f"  📈 Total Tickers: {self.stats.total_tickers}")
        print(f"  ✅ Successful: {self.stats.successful}")
        print(f"  ❌ Failed: {self.stats.failed}")
        print(f"  📁 Files Created: {self.stats.total_files}")
        print(f"  📊 Total Rows: {self.stats.total_rows:,}")
        print(f"  📈 Success Rate: {self.stats.success_rate:.1f}%")

        print(f"\n{'─'*80}")
        print("  DETAILED RESULTS:")
        print(f"{'─'*80}")
        print(summary_df.to_string(index=False))
        print(f"{'═'*80}\n")

        summary_path = self.output_dir / "_SCRAPING_SUMMARY.csv"
        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        logger.info(f"📊 Summary saved: {summary_path}")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              📈 YAHOO FINANCE DATA SCRAPER                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


def main():
    print_banner()

    input_path = Path(INPUT_FILE)

    if not input_path.exists():
        create_sample_csv(input_path)

    tickers = load_tickers(input_path)

    if not tickers:
        logger.error("❌ No valid tickers to process. Exiting...")
        sys.exit(1)

    print(f"\n📋 Tickers to process ({len(tickers)}):")
    print("─" * 40)
    for i, ticker in enumerate(tickers, 1):
        print(f"  {i:2d}. {ticker}")
    print("─" * 40)

    try:
        input("\nPress Enter to start scraping (Ctrl+C to cancel)...")
    except KeyboardInterrupt:
        print("\n\n🚫 Cancelled by user.")
        sys.exit(0)

    scraper = YahooFinanceScraper(output_dir=OUTPUT_DIR, config=CONFIG)
    results = scraper.scrape_all(tickers)
    scraper.print_summary(results)

    sys.exit(1 if scraper.stats.failed > 0 else 0)


if __name__ == "__main__":
    main()