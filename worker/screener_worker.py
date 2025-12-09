"""
MARKET SNIPER - Supabase Worker
Runs via GitHub Actions, pushes signals to Supabase
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime, timedelta
from supabase import create_client, Client
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# SUPABASE CONFIG
# =============================================================================
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')  # Use service key for writes

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================================================================
# SCREENER CONFIG
# =============================================================================
STOP_LOSS_PCT = 15.0
TAKE_PROFIT_PCT = 50.0
USE_TRAILING = True
TRAIL_ACTIVATION_PCT = 15.0
TRAIL_DISTANCE_PCT = 10.0
MAX_HOLD_DAYS = 120

USE_VIX_FILTER = True
VIX_MIN = 20
VIX_MAX = 35  # Optimized for crash protection

USE_VOLUME_FILTER = True
VOLUME_SURGE_MULT = 1.2

ACCOUNT_SIZE = 100000
RISK_PER_TRADE_PCT = 1.0

# Lookback for new signals (only scan recent data)
LOOKBACK_DAYS = 30

# Technical parameters
MIN_MARKET_CAP = 1e9
MIN_BARS = 260
RSI_OVERSOLD = 35
RSI_SIGNAL = 45
RSI_LOOKBACK = 5
ADX_MIN = 18
MIN_BELOW_HIGH_PCT = 20.0
MAX_BELOW_HIGH_PCT = 55.0
MAX_FROM_SMA_PCT = 15.0
SMA_SLOPE_DAYS = 20
VOLUME_AVG_DAYS = 50
MIN_GAP_DAYS = 20
MAX_POSITION_PCT = 15.0

# Fundamental filters
USE_FUNDAMENTAL_FILTER = True
MAX_PE_RATIO = 30
PE_PREFER_BELOW = 20
MAX_PEG_RATIO = 2.0
MAX_PRICE_TO_BOOK = 5.0
MIN_ROE = 8.0
MAX_DEBT_EQUITY = 2.0
REQUIRE_POSITIVE_FCF = True

# =============================================================================
# DYNAMIC TICKER FETCHING
# =============================================================================
import requests
from io import StringIO

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

def get_sp500_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url, storage_options={'User-Agent': HEADERS['User-Agent']})
        tickers = tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        print(f"✓ S&P 500: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ S&P 500 failed: {e}")
        return []

def get_sp400_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
        tables = pd.read_html(url, storage_options={'User-Agent': HEADERS['User-Agent']})
        df = tables[0]
        col = 'Symbol' if 'Symbol' in df.columns else 'Ticker Symbol'
        tickers = df[col].str.replace('.', '-', regex=False).tolist()
        print(f"✓ S&P 400: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ S&P 400 failed: {e}")
        return []

def get_tickers():
    print("Fetching tickers...")
    all_tickers = []
    all_tickers.extend(get_sp500_tickers())
    time.sleep(0.5)
    all_tickers.extend(get_sp400_tickers())
    tickers = sorted(list(set(all_tickers)))
    tickers = [t for t in tickers if t and isinstance(t, str) and 1 <= len(t) <= 5]
    print(f"Total: {len(tickers)} tickers")
    return tickers

TICKERS = get_tickers()

# Fallback if fetching fails
if len(TICKERS) < 100:
    print("Using fallback ticker list...")
    TICKERS = [
        'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'ADP', 'AMAT', 'AMD', 'AMGN', 'AMZN',
        'AVGO', 'AXP', 'BA', 'BAC', 'BK', 'BKNG', 'BLK', 'BMY', 'BRK-B', 'C',
        'CAT', 'CHTR', 'CL', 'CMCSA', 'COF', 'COP', 'COST', 'CRM', 'CSCO', 'CVS',
        'CVX', 'DE', 'DHR', 'DIS', 'DOW', 'DUK', 'EMR', 'EXC', 'F', 'FDX',
        'GD', 'GE', 'GILD', 'GM', 'GOOG', 'GOOGL', 'GS', 'HD', 'HON', 'IBM',
        'INTC', 'INTU', 'ISRG', 'JNJ', 'JPM', 'KO', 'LIN', 'LLY', 'LMT', 'LOW',
        'MA', 'MCD', 'MDLZ', 'MDT', 'MET', 'META', 'MMM', 'MO', 'MRK', 'MS',
        'MSFT', 'NEE', 'NFLX', 'NKE', 'NOW', 'NVDA', 'ORCL', 'PEP', 'PFE', 'PG',
        'PM', 'PYPL', 'QCOM', 'RTX', 'SBUX', 'SCHW', 'SO', 'SPG', 'T', 'TGT',
        'TMO', 'TMUS', 'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'USB', 'V', 'VZ',
        'WFC', 'WMT', 'XOM',
    ]

# =============================================================================
# INDICATORS
# =============================================================================
def calc_rsi(close, length=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50)

def calc_adx(high, low, close, length=14):
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=high.index)
    atr = tr.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/length, min_periods=length, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1/length, min_periods=length, adjust=False).mean() / atr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    return adx.fillna(0), plus_di.fillna(0), minus_di.fillna(0)

# =============================================================================
# FUNDAMENTAL CHECK
# =============================================================================
def check_fundamentals(info):
    if not USE_FUNDAMENTAL_FILTER:
        return True, 10, {}

    score = 0
    details = {}

    pe = info.get('forwardPE') or info.get('trailingPE')
    if pe and pe > 0:
        details['pe'] = pe
        if pe <= PE_PREFER_BELOW:
            score += 3
        elif pe <= MAX_PE_RATIO:
            score += 1

    peg = info.get('pegRatio')
    if peg and peg > 0:
        details['peg'] = peg
        if peg < 1:
            score += 3
        elif peg <= MAX_PEG_RATIO:
            score += 1

    pb = info.get('priceToBook')
    if pb and pb > 0:
        details['pb'] = pb
        if pb < 2:
            score += 2
        elif pb <= MAX_PRICE_TO_BOOK:
            score += 1

    roe = info.get('returnOnEquity')
    if roe:
        roe_pct = roe * 100
        details['roe'] = roe_pct
        if roe_pct >= 15:
            score += 3
        elif roe_pct >= MIN_ROE:
            score += 1

    de = info.get('debtToEquity')
    if de:
        de_ratio = de / 100 if de > 10 else de
        details['de'] = de_ratio
        if de_ratio < 0.5:
            score += 2
        elif de_ratio <= MAX_DEBT_EQUITY:
            score += 1

    fcf = info.get('freeCashflow')
    if fcf:
        details['fcf'] = fcf
        if fcf > 0:
            score += 2
        elif REQUIRE_POSITIVE_FCF:
            score -= 2

    eg = info.get('earningsGrowth')
    if eg and eg > 0:
        details['earnings_growth'] = eg * 100
        if eg > 0.20:
            score += 2
        elif eg > 0:
            score += 1

    passed = score >= 5
    details['score'] = score

    return passed, score, details

# =============================================================================
# SCANNER (simplified for live signals)
# =============================================================================
def scan_for_live_signals():
    """Scan for new signals in the last LOOKBACK_DAYS"""

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    lookback_start = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')

    # Get VIX
    print("Downloading VIX data...")
    vix = yf.download('^VIX', start=start_date, end=end_date, progress=False)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = [col[0] for col in vix.columns]
    vix_lookup = {date.strftime('%Y-%m-%d'): float(row['Close']) for date, row in vix.iterrows()}

    # Get existing signals from Supabase to avoid duplicates
    existing = supabase.table('signals').select('ticker, signal_date').execute()
    existing_keys = set()
    for row in existing.data:
        existing_keys.add(f"{row['ticker']}_{row['signal_date']}")

    print(f"Existing signals in DB: {len(existing_keys)}")
    print(f"Scanning {len(TICKERS)} tickers...")

    new_signals = []
    stats = {'success': 0, 'skipped': 0, 'error': 0}

    for i, ticker in enumerate(TICKERS):
        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(TICKERS)}] New signals: {len(new_signals)}")

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if (info.get('marketCap', 0) or 0) < MIN_MARKET_CAP:
                stats['skipped'] += 1
                continue

            passed_fundamentals, fund_score, fund_details = check_fundamentals(info)
            if not passed_fundamentals:
                stats['skipped'] += 1
                continue

            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df is None or len(df) < MIN_BARS:
                stats['skipped'] += 1
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]

            close, high, low, volume = df['Close'].values, df['High'].values, df['Low'].values, df['Volume'].values
            dates = df.index

            close_s = pd.Series(close)
            high_s = pd.Series(high)
            low_s = pd.Series(low)
            vol_s = pd.Series(volume)

            rsi = calc_rsi(close_s, 14).values
            adx, _, _ = calc_adx(high_s, low_s, close_s, 14)
            adx = adx.values
            sma_200 = close_s.rolling(200).mean().values
            sma_slope = ((pd.Series(sma_200) - pd.Series(sma_200).shift(SMA_SLOPE_DAYS)) / pd.Series(sma_200).shift(SMA_SLOPE_DAYS) * 100).values
            high_52w = high_s.rolling(252).max().values
            vol_avg = vol_s.rolling(VOLUME_AVG_DAYS).mean().values

            # Only scan recent dates
            for i in range(max(260, len(df) - LOOKBACK_DAYS), len(df)):
                date_str = dates[i].strftime('%Y-%m-%d')

                # Skip if already in DB
                key = f"{ticker}_{date_str}"
                if key in existing_keys:
                    continue

                vix_val = vix_lookup.get(date_str, 15)

                if USE_VIX_FILTER and not (VIX_MIN <= vix_val <= VIX_MAX):
                    continue

                price = close[i]
                if np.isnan(sma_200[i]) or np.isnan(high_52w[i]) or np.isnan(adx[i]):
                    continue

                pct_below = (high_52w[i] - price) / high_52w[i] * 100
                if not (MIN_BELOW_HIGH_PCT <= pct_below <= MAX_BELOW_HIGH_PCT):
                    continue

                pct_sma = abs(price - sma_200[i]) / sma_200[i] * 100
                if pct_sma > MAX_FROM_SMA_PCT or price < sma_200[i] * 0.95:
                    continue

                if not np.isnan(sma_slope[i]) and sma_slope[i] < -2:
                    continue

                rsi_sig = any(i-j-1 >= 0 and (rsi[i-j-1] <= RSI_SIGNAL and rsi[i-j] > RSI_SIGNAL or rsi[i-j-1] <= RSI_OVERSOLD)
                            for j in range(1, RSI_LOOKBACK + 1))
                if not rsi_sig or adx[i] < ADX_MIN:
                    continue

                if USE_VOLUME_FILTER:
                    if np.isnan(vol_avg[i]) or vol_avg[i] == 0 or volume[i] / vol_avg[i] < VOLUME_SURGE_MULT:
                        continue

                # Signal found!
                signal = {
                    'ticker': ticker,
                    'signal_date': date_str,
                    'entry_price': round(float(price), 2),
                    'vix': round(float(vix_val), 1),
                    'rsi': round(float(rsi[i]), 1),
                    'adx': round(float(adx[i]), 1),
                    'pct_below_high': round(float(pct_below), 1),
                    'sector': info.get('sector', 'Unknown'),
                    'pe_ratio': round(float(fund_details.get('pe', 0)), 2) if fund_details.get('pe') else None,
                    'peg_ratio': round(float(fund_details.get('peg', 0)), 2) if fund_details.get('peg') else None,
                    'roe': round(float(fund_details.get('roe', 0)), 1) if fund_details.get('roe') else None,
                    'debt_equity': round(float(fund_details.get('de', 0)), 2) if fund_details.get('de') else None,
                    'fund_score': fund_score,
                    'status': 'active',
                }
                new_signals.append(signal)
                existing_keys.add(key)

            stats['success'] += 1

        except Exception as e:
            stats['error'] += 1

        if (i + 1) % 100 == 0:
            time.sleep(1)

    return new_signals, stats

# =============================================================================
# PUSH TO SUPABASE
# =============================================================================
def push_signals_to_supabase(signals):
    """Insert new signals into Supabase"""
    if not signals:
        print("No new signals to push")
        return 0

    print(f"Pushing {len(signals)} signals to Supabase...")

    # Insert in batches
    batch_size = 50
    inserted = 0

    for i in range(0, len(signals), batch_size):
        batch = signals[i:i+batch_size]
        try:
            result = supabase.table('signals').upsert(batch).execute()
            inserted += len(batch)
            print(f"  Inserted batch {i//batch_size + 1}: {len(batch)} signals")
        except Exception as e:
            print(f"  Error inserting batch: {e}")

    return inserted

def log_run(signals_found, new_signals, tickers_scanned, duration, status='success', error=None):
    """Log the screener run"""
    try:
        supabase.table('screener_runs').insert({
            'signals_found': signals_found,
            'new_signals': new_signals,
            'tickers_scanned': tickers_scanned,
            'duration_seconds': duration,
            'status': status,
            'error_message': error
        }).execute()
    except Exception as e:
        print(f"Error logging run: {e}")

# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("MARKET SNIPER - Supabase Worker")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    start_time = time.time()

    try:
        # Scan for signals
        signals, stats = scan_for_live_signals()

        print(f"\nScan complete: {stats}")
        print(f"New signals found: {len(signals)}")

        # Push to Supabase
        inserted = push_signals_to_supabase(signals)

        duration = int(time.time() - start_time)
        log_run(
            signals_found=len(signals),
            new_signals=inserted,
            tickers_scanned=len(TICKERS),
            duration=duration,
            status='success'
        )

        print(f"\nDone! Duration: {duration}s")
        print(f"Inserted {inserted} new signals")

    except Exception as e:
        duration = int(time.time() - start_time)
        log_run(0, 0, len(TICKERS), duration, 'error', str(e))
        print(f"Error: {e}")
        raise

if __name__ == '__main__':
    main()
