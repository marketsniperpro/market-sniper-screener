"""
Dynamic Ticker Fetcher - Gets current US market tickers from multiple sources
No hardcoding - always fetches fresh data
"""

import pandas as pd
import requests
from io import StringIO
import time

def get_sp500_tickers():
    """Fetch current S&P 500 constituents from Wikipedia"""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
        print(f"✓ S&P 500: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ S&P 500 fetch failed: {e}")
        return []

def get_sp400_tickers():
    """Fetch current S&P 400 MidCap constituents from Wikipedia"""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
        tables = pd.read_html(url)
        df = tables[0]
        # Column might be 'Symbol' or 'Ticker'
        col = 'Symbol' if 'Symbol' in df.columns else 'Ticker Symbol'
        tickers = df[col].str.replace('.', '-', regex=False).tolist()
        print(f"✓ S&P 400: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ S&P 400 fetch failed: {e}")
        return []

def get_sp600_tickers():
    """Fetch current S&P 600 SmallCap constituents from Wikipedia"""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
        tables = pd.read_html(url)
        df = tables[0]
        col = 'Symbol' if 'Symbol' in df.columns else 'Ticker symbol'
        tickers = df[col].str.replace('.', '-', regex=False).tolist()
        print(f"✓ S&P 600: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ S&P 600 fetch failed: {e}")
        return []

def get_nasdaq100_tickers():
    """Fetch current NASDAQ 100 constituents from Wikipedia"""
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        # Find the table with ticker symbols
        for table in tables:
            if 'Ticker' in table.columns or 'Symbol' in table.columns:
                col = 'Ticker' if 'Ticker' in table.columns else 'Symbol'
                tickers = table[col].str.replace('.', '-', regex=False).tolist()
                print(f"✓ NASDAQ 100: {len(tickers)} tickers")
                return tickers
        return []
    except Exception as e:
        print(f"✗ NASDAQ 100 fetch failed: {e}")
        return []

def get_nasdaq_traded():
    """
    Fetch ALL NASDAQ-traded stocks from official NASDAQ FTP
    Most comprehensive source - includes 5000+ actively traded US stocks
    """
    try:
        url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
        response = requests.get(url, timeout=30)
        df = pd.read_csv(StringIO(response.text), sep='|')

        # Filter: common stocks only, actively traded
        df = df[
            (df['ETF'] == 'N') &
            (df['Test Issue'] == 'N') &
            (df['NextShares'] == 'N') &
            (df['Symbol'].notna())
        ]

        # Remove warrants, units, preferred (symbols with special chars)
        df = df[~df['Symbol'].str.contains(r'[\$\^\.\+\-]', regex=True, na=False)]

        # Only keep symbols 1-5 chars
        df = df[df['Symbol'].str.len() <= 5]

        tickers = df['Symbol'].tolist()
        print(f"✓ NASDAQ Traded: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ NASDAQ Traded fetch failed: {e}")
        return []

def get_nyse_listed():
    """Fetch NYSE-listed stocks from official NASDAQ FTP"""
    try:
        url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
        response = requests.get(url, timeout=30)
        df = pd.read_csv(StringIO(response.text), sep='|')

        # Filter for NYSE stocks
        df = df[
            (df['Exchange'] == 'N') &  # NYSE
            (df['ETF'] == 'N') &
            (df['Test Issue'] == 'N') &
            (df['ACT Symbol'].notna())
        ]

        # Clean symbols
        df = df[~df['ACT Symbol'].str.contains(r'[\$\^\.\+]', regex=True, na=False)]
        df = df[df['ACT Symbol'].str.len() <= 5]

        tickers = df['ACT Symbol'].tolist()
        print(f"✓ NYSE Listed: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ NYSE Listed fetch failed: {e}")
        return []

def get_finviz_tickers(min_price=5, min_volume=500000, min_market_cap=300):
    """
    Fetch tickers from Finviz with basic filters
    min_market_cap in millions (300 = $300M+)
    """
    try:
        # Finviz screener URL with filters
        # cap_small = $300M-$2B, cap_mid = $2B-$10B, cap_large = $10B+
        url = f"https://finviz.com/export.ashx?v=111&f=cap_smallover,sh_avgvol_o500,sh_price_o5"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            df = pd.read_csv(StringIO(response.text))
            tickers = df['Ticker'].tolist()
            print(f"✓ Finviz Screener: {len(tickers)} tickers")
            return tickers
        else:
            print(f"✗ Finviz returned status {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Finviz fetch failed: {e}")
        return []

def get_all_us_tickers(
    include_sp500=True,
    include_sp400=True,
    include_sp600=True,
    include_nasdaq100=True,
    include_full_market=False,  # Set True for full US market (5000+)
    include_finviz=True,
    min_market_cap_millions=300
):
    """
    Get comprehensive US stock ticker list from multiple sources

    Default settings give ~1500 quality stocks (S&P indices)
    Set include_full_market=True for full US market (5000+ stocks)
    """
    print("=" * 50)
    print("Fetching current US market tickers...")
    print("=" * 50)

    all_tickers = []

    if include_full_market:
        # Full market from official NASDAQ sources
        all_tickers.extend(get_nasdaq_traded())
        time.sleep(1)
        all_tickers.extend(get_nyse_listed())
        time.sleep(1)
    else:
        # S&P indices for quality stocks
        if include_sp500:
            all_tickers.extend(get_sp500_tickers())
            time.sleep(1)

        if include_sp400:
            all_tickers.extend(get_sp400_tickers())
            time.sleep(1)

        if include_sp600:
            all_tickers.extend(get_sp600_tickers())
            time.sleep(1)

        if include_nasdaq100:
            all_tickers.extend(get_nasdaq100_tickers())
            time.sleep(1)

        if include_finviz:
            all_tickers.extend(get_finviz_tickers(min_market_cap=min_market_cap_millions))

    # Deduplicate and clean
    tickers = sorted(list(set(all_tickers)))

    # Remove any empty or invalid
    tickers = [t for t in tickers if t and isinstance(t, str) and 1 <= len(t) <= 5]

    print("=" * 50)
    print(f"Total unique tickers: {len(tickers)}")
    print("=" * 50)

    return tickers


def get_quality_tickers():
    """
    Get a quality-filtered list of ~1500 liquid US stocks
    S&P 500 + S&P 400 + S&P 600 + NASDAQ 100
    Good balance of coverage vs scan time
    """
    return get_all_us_tickers(
        include_sp500=True,
        include_sp400=True,
        include_sp600=True,
        include_nasdaq100=True,
        include_full_market=False,
        include_finviz=True
    )


def get_full_market_tickers():
    """
    Get ALL tradeable US stocks (5000+)
    From official NASDAQ + NYSE sources
    Warning: Scanning this many takes a long time
    """
    return get_all_us_tickers(include_full_market=True)


# Test if run directly
if __name__ == "__main__":
    print("\n### Testing Quality Tickers (S&P indices + Finviz) ###\n")
    quality = get_quality_tickers()
    print(f"\nSample: {quality[:20]}")

    print("\n### Testing Full Market (includes all NASDAQ) ###\n")
    # full = get_full_market_tickers()  # Uncomment to test
