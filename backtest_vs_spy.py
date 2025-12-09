# =============================================================================
# MARKET SNIPER - BACKTEST WITH SPY COMPARISON
# =============================================================================
# Shows: Closed trades, Active positions, Equity curve vs SPY
# =============================================================================

!pip install yfinance pandas numpy matplotlib -q

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================
STOP_LOSS_PCT = 15.0
TAKE_PROFIT_PCT = 50.0
USE_TRAILING = True
TRAIL_ACTIVATION_PCT = 15.0
TRAIL_DISTANCE_PCT = 10.0
MAX_HOLD_DAYS = 120

USE_VIX_FILTER = True
VIX_MIN = 20
VIX_MAX = 50

USE_VOLUME_FILTER = True
VOLUME_SURGE_MULT = 1.2

STARTING_CAPITAL = 100000
RISK_PER_TRADE_PCT = 1.0

START_DATE = '2019-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')

# Technical parameters
MIN_MARKET_CAP = 1e9
MIN_BARS = 500
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
MIN_ROE = 8.0
MAX_DEBT_EQUITY = 2.0

# =============================================================================
# DYNAMIC TICKER FETCHING - Always gets current market constituents
# =============================================================================
import requests
from io import StringIO

# Headers to prevent blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def get_nasdaq_traded():
    """
    Fetch ALL NASDAQ-traded stocks from official NASDAQ FTP
    PRIMARY SOURCE - Most reliable, updated daily
    """
    try:
        url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
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
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text), sep='|')

        # Filter for NYSE stocks (and AMEX/ARCA)
        df = df[
            (df['ETF'] == 'N') &
            (df['Test Issue'] == 'N') &
            (df['ACT Symbol'].notna())
        ]

        # Clean symbols
        df = df[~df['ACT Symbol'].str.contains(r'[\$\^\.\+]', regex=True, na=False)]
        df = df[df['ACT Symbol'].str.len() <= 5]

        tickers = df['ACT Symbol'].tolist()
        print(f"✓ NYSE/Other Listed: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ NYSE Listed fetch failed: {e}")
        return []

def get_sp500_tickers():
    """Fetch current S&P 500 from Wikipedia (backup)"""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url, storage_options={'User-Agent': HEADERS['User-Agent']})
        tickers = tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        print(f"✓ S&P 500: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"✗ S&P 500 failed: {e}")
        return []

# =============================================================================
# SCAN MODE - Choose how many stocks to scan
# =============================================================================
# 'fast'   = ~500 stocks  (~5-8 min)   - S&P 500 large caps
# 'medium' = ~900 stocks  (~10-15 min) - S&P 500 + S&P 400 mid caps
# 'full'   = ~6000 stocks (~60+ min)   - Entire US market
SCAN_MODE = 'medium'  # <-- CHANGE THIS

def get_sp400_tickers():
    """Fetch S&P 400 MidCap from Wikipedia"""
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

def get_all_tickers(mode='medium'):
    """Fetch tickers based on scan mode"""
    print("=" * 50)
    print(f"Scan mode: {mode.upper()}")
    print("=" * 50)

    all_tickers = []

    if mode == 'fast':
        # S&P 500 only
        all_tickers.extend(get_sp500_tickers())
    elif mode == 'medium':
        # S&P 500 + 400 MidCap
        all_tickers.extend(get_sp500_tickers())
        time.sleep(0.5)
        all_tickers.extend(get_sp400_tickers())
    else:  # 'full'
        # Entire US market
        all_tickers.extend(get_nasdaq_traded())
        time.sleep(0.5)
        all_tickers.extend(get_nyse_listed())

    # Deduplicate and clean
    tickers = sorted(list(set(all_tickers)))
    tickers = [t for t in tickers if t and isinstance(t, str) and 1 <= len(t) <= 5]

    print(f"Total tickers: {len(tickers)}")
    print("=" * 50)
    return tickers

# Fetch tickers based on scan mode
TICKERS = get_all_tickers(SCAN_MODE)

# Fallback list if ALL dynamic fetching fails
if len(TICKERS) < 100:
    print("⚠️ Dynamic fetch failed, using fallback list (~500 stocks)...")
    TICKERS = [
        # S&P 500 Large Cap
        'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'ADI', 'ADP', 'ADSK', 'AEP', 'AFL',
        'AIG', 'AMAT', 'AMD', 'AMGN', 'AMZN', 'ANET', 'AON', 'APD', 'APH', 'AVGO',
        'AXP', 'AZO', 'BA', 'BAC', 'BDX', 'BIIB', 'BK', 'BKNG', 'BLK', 'BMY',
        'BRK-B', 'BSX', 'C', 'CAT', 'CB', 'CDNS', 'CEG', 'CHTR', 'CI', 'CL',
        'CMCSA', 'CME', 'CMG', 'COF', 'COP', 'COST', 'CRM', 'CSCO', 'CSX', 'CTAS',
        'CVS', 'CVX', 'D', 'DD', 'DE', 'DHI', 'DHR', 'DIS', 'DLR', 'DOW',
        'DUK', 'DVN', 'DXCM', 'EA', 'EBAY', 'ECL', 'EL', 'EMR', 'ENPH', 'EOG',
        'EQIX', 'EW', 'EXC', 'F', 'FANG', 'FAST', 'FCX', 'FDX', 'FI', 'FICO',
        'FISV', 'FTNT', 'GD', 'GE', 'GEHC', 'GILD', 'GIS', 'GLW', 'GM', 'GOOG',
        'GOOGL', 'GPN', 'GS', 'GWW', 'HAL', 'HD', 'HES', 'HLT', 'HON', 'HPQ',
        'HSY', 'HUM', 'IBM', 'ICE', 'IDXX', 'INTC', 'INTU', 'ISRG', 'ITW', 'JCI',
        'JBHT', 'JNJ', 'JPM', 'KDP', 'KEY', 'KHC', 'KLAC', 'KMB', 'KO', 'KR',
        'LRCX', 'LEN', 'LIN', 'LLY', 'LMT', 'LOW', 'LULU', 'LVS', 'LYB', 'MA',
        'MAR', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MET', 'META', 'MGM',
        'MMC', 'MMM', 'MNST', 'MO', 'MPC', 'MRK', 'MRNA', 'MS', 'MSCI', 'MSFT',
        'MSI', 'MTB', 'MU', 'NDAQ', 'NEE', 'NEM', 'NFLX', 'NKE', 'NOC', 'NOW',
        'NSC', 'NTAP', 'NVDA', 'NVR', 'NXPI', 'O', 'ODFL', 'OKE', 'OMC', 'ON',
        'ORCL', 'ORLY', 'OXY', 'PANW', 'PAYX', 'PCAR', 'PEG', 'PEP', 'PFE', 'PG',
        'PGR', 'PH', 'PHM', 'PLD', 'PM', 'PNC', 'PPG', 'PRU', 'PSA', 'PSX',
        'PXD', 'PYPL', 'QCOM', 'RCL', 'REGN', 'RF', 'RJF', 'ROK', 'ROP', 'ROST',
        'RSG', 'RTX', 'SBUX', 'SCHW', 'SHW', 'SLB', 'SNPS', 'SO', 'SPG', 'SPGI',
        'SRE', 'STT', 'STZ', 'SYF', 'SYK', 'SYY', 'T', 'TDG', 'TEL', 'TFC',
        'TGT', 'TJX', 'TMO', 'TMUS', 'TRGP', 'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN',
        'TT', 'TTWO', 'TXN', 'TYL', 'UAL', 'UNH', 'UNP', 'UPS', 'URI', 'USB',
        'V', 'VICI', 'VLO', 'VMC', 'VRSK', 'VRTX', 'VZ', 'WBA', 'WBD', 'WELL',
        'WFC', 'WM', 'WMB', 'WMT', 'WRB', 'WST', 'XEL', 'XOM', 'XYL', 'YUM',
        'ZBH', 'ZBRA', 'ZTS',
        # Mid Cap Growth
        'ABNB', 'AXON', 'BILL', 'BLDR', 'CPRT', 'CRWD', 'DASH', 'DDOG', 'DECK',
        'DOCU', 'ENSG', 'EXAS', 'EXP', 'FND', 'GDDY', 'GNRC', 'HUBS', 'INSP',
        'LNTH', 'MANH', 'MEDP', 'MDB', 'MPWR', 'MSTR', 'MUSA', 'NET', 'NTRA',
        'OLED', 'ONTO', 'PCTY', 'PLTR', 'PODD', 'POOL', 'PSTG', 'RH', 'SAIA',
        'SMCI', 'SNOW', 'SQ', 'TECH', 'TER', 'TOST', 'TPL', 'TREX', 'TTD', 'TW',
        'UBER', 'ULTA', 'VEEV', 'WIX', 'ZS',
        # Energy & Materials
        'ALB', 'APA', 'AR', 'BKR', 'CF', 'CLF', 'CNX', 'CTRA', 'DVN', 'EQT',
        'FANG', 'HAL', 'HES', 'KMI', 'MOS', 'MPC', 'MRO', 'NOV', 'NUE', 'OKE',
        'OVV', 'OXY', 'RRC', 'SCCO', 'SLB', 'STLD', 'TRGP', 'VLO', 'WMB', 'XOM',
        # Financials
        'ACGL', 'AFL', 'AIG', 'ALL', 'ALLY', 'AON', 'AXP', 'BAC', 'BK', 'BLK',
        'BRO', 'C', 'CB', 'CINF', 'CMA', 'COF', 'DFS', 'FITB', 'GS', 'HBAN',
        'HIG', 'IBKR', 'ICE', 'JPM', 'KEY', 'L', 'MET', 'MMC', 'MS', 'MTB',
        'NTRS', 'PFG', 'PGR', 'PNC', 'PRU', 'RF', 'RJF', 'SCHW', 'STT', 'SYF',
        'TFC', 'TROW', 'TRV', 'USB', 'WFC', 'WRB', 'ZION',
        # REITs
        'AMT', 'ARE', 'AVB', 'CCI', 'DLR', 'EQIX', 'EQR', 'ESS', 'EXR', 'INVH',
        'IRM', 'MAA', 'O', 'PLD', 'PSA', 'SBAC', 'SPG', 'UDR', 'VICI', 'WELL',
    ]
    TICKERS = sorted(list(set(TICKERS)))
    print(f"Fallback tickers: {len(TICKERS)}")

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

def check_fundamentals(info):
    score = 0
    pe = info.get('forwardPE') or info.get('trailingPE')
    if pe and 0 < pe <= MAX_PE_RATIO:
        score += 2
    roe = info.get('returnOnEquity')
    if roe and roe * 100 >= MIN_ROE:
        score += 2
    de = info.get('debtToEquity')
    if de:
        de_ratio = de / 100 if de > 10 else de
        if de_ratio <= MAX_DEBT_EQUITY:
            score += 2
    fcf = info.get('freeCashflow')
    if fcf and fcf > 0:
        score += 2
    return score >= 4, score, {'pe': pe, 'roe': roe * 100 if roe else None}

# =============================================================================
# DATA
# =============================================================================
print("\nDownloading VIX data...")
vix = yf.download('^VIX', start=START_DATE, end=END_DATE, progress=False)
if isinstance(vix.columns, pd.MultiIndex):
    vix.columns = [col[0] for col in vix.columns]
vix_lookup = {date.strftime('%Y-%m-%d'): float(row['Close']) for date, row in vix.iterrows()}

print("Downloading SPY data for comparison...")
spy_df = yf.download('SPY', start=START_DATE, end=END_DATE, progress=False)
if isinstance(spy_df.columns, pd.MultiIndex):
    spy_df.columns = [col[0] for col in spy_df.columns]

# =============================================================================
# TRADE EXECUTION
# =============================================================================
def execute_trade(close, high, low, entry_idx, entry_price, dates):
    """Execute trade and return result with exit date"""
    stop_price = entry_price * (1 - STOP_LOSS_PCT / 100)
    tp_price = entry_price * (1 + TAKE_PROFIT_PCT / 100)
    activation_price = entry_price * (1 + TRAIL_ACTIVATION_PCT / 100)
    highest_high = entry_price
    trailing_active = False
    trailing_stop = stop_price

    for day in range(1, MAX_HOLD_DAYS + 1):
        idx = entry_idx + day
        if idx >= len(close):
            # Still open - no exit yet
            return {
                'return_pct': (close[-1] - entry_price) / entry_price * 100,
                'exit_day': day,
                'exit_reason': 'still_open',
                'exit_date': None,
                'exit_price': close[-1],
                'trailing_activated': trailing_active
            }

        day_high, day_low = high[idx], low[idx]
        if day_high > highest_high:
            highest_high = day_high

        if USE_TRAILING and not trailing_active and day_high >= activation_price:
            trailing_active = True
        if trailing_active:
            trailing_stop = max(trailing_stop, highest_high * (1 - TRAIL_DISTANCE_PCT / 100))

        current_stop = trailing_stop if trailing_active else stop_price

        if day_low <= current_stop:
            return {
                'return_pct': (current_stop - entry_price) / entry_price * 100,
                'exit_day': day,
                'exit_reason': 'trail_stop' if trailing_active else 'stop',
                'exit_date': dates[idx].strftime('%Y-%m-%d'),
                'exit_price': current_stop,
                'trailing_activated': trailing_active
            }
        if day_high >= tp_price:
            return {
                'return_pct': TAKE_PROFIT_PCT,
                'exit_day': day,
                'exit_reason': 'target',
                'exit_date': dates[idx].strftime('%Y-%m-%d'),
                'exit_price': tp_price,
                'trailing_activated': trailing_active
            }

    exit_price = close[entry_idx + MAX_HOLD_DAYS]
    return {
        'return_pct': (exit_price - entry_price) / entry_price * 100,
        'exit_day': MAX_HOLD_DAYS,
        'exit_reason': 'max_days',
        'exit_date': dates[entry_idx + MAX_HOLD_DAYS].strftime('%Y-%m-%d'),
        'exit_price': exit_price,
        'trailing_activated': trailing_active
    }

# =============================================================================
# SCANNER
# =============================================================================
def scan_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if (info.get('marketCap', 0) or 0) < MIN_MARKET_CAP:
            return [], 'low_cap'

        passed_fundamentals, fund_score, fund_details = check_fundamentals(info)
        if USE_FUNDAMENTAL_FILTER and not passed_fundamentals:
            return [], 'failed_fundamentals'

        df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
        if df is None or len(df) < MIN_BARS:
            return [], 'no_data'
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        close, high, low, volume = df['Close'].values, df['High'].values, df['Low'].values, df['Volume'].values
        dates = df.index

        close_s, high_s, low_s, vol_s = pd.Series(close), pd.Series(high), pd.Series(low), pd.Series(volume)
        rsi = calc_rsi(close_s, 14).values
        adx, _, _ = calc_adx(high_s, low_s, close_s, 14)
        adx = adx.values
        sma_200 = close_s.rolling(200).mean().values
        sma_slope = ((pd.Series(sma_200) - pd.Series(sma_200).shift(SMA_SLOPE_DAYS)) / pd.Series(sma_200).shift(SMA_SLOPE_DAYS) * 100).values
        high_52w = high_s.rolling(252).max().values
        vol_avg = vol_s.rolling(VOLUME_AVG_DAYS).mean().values

        signals = []
        last_idx = -999

        for i in range(260, len(df)):
            if i - last_idx < MIN_GAP_DAYS:
                continue

            date_str = dates[i].strftime('%Y-%m-%d')
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

            trade = execute_trade(close, high, low, i, price, dates)
            risk_dollars = STARTING_CAPITAL * (RISK_PER_TRADE_PCT / 100)
            position = min(risk_dollars / (STOP_LOSS_PCT / 100), STARTING_CAPITAL * MAX_POSITION_PCT / 100)

            signals.append({
                'ticker': ticker,
                'entry_date': date_str,
                'entry_price': round(price, 2),
                'exit_date': trade['exit_date'],
                'exit_price': round(trade['exit_price'], 2),
                'vix': round(vix_val, 1),
                'sector': info.get('sector', 'Unknown'),
                'return_pct': round(trade['return_pct'], 2),
                'exit_day': trade['exit_day'],
                'exit_reason': trade['exit_reason'],
                'position': round(position, 0),
                'pnl': round(position * trade['return_pct'] / 100, 0),
                'pe': fund_details.get('pe'),
                'roe': fund_details.get('roe'),
            })
            last_idx = i

        return signals, 'success'
    except Exception as e:
        return [], 'error'

# =============================================================================
# RUN SCANNER
# =============================================================================
print(f"\n{'='*70}")
print(f"MARKET SNIPER - BACKTEST vs SPY")
print(f"Period: {START_DATE} to {END_DATE}")
print(f"{'='*70}")

all_signals = []
start_time = time.time()

for i, ticker in enumerate(TICKERS):
    if (i + 1) % 50 == 0:
        print(f"  [{i+1:4d}/{len(TICKERS)}] Signals: {len(all_signals):4d}")

    signals, status = scan_stock(ticker)
    all_signals.extend(signals)

    if (i + 1) % 100 == 0:
        time.sleep(1)

print(f"\nDone in {(time.time()-start_time)/60:.1f} min")

# =============================================================================
# SEPARATE CLOSED vs ACTIVE
# =============================================================================
df = pd.DataFrame(all_signals)
df['entry_date'] = pd.to_datetime(df['entry_date'])

# Closed trades (have exit date)
closed = df[df['exit_reason'] != 'still_open'].copy()
closed['exit_date'] = pd.to_datetime(closed['exit_date'])

# Active positions (still open)
active = df[df['exit_reason'] == 'still_open'].copy()

print(f"\n{'='*70}")
print("TRADE SUMMARY")
print(f"{'='*70}")
print(f"Total signals: {len(df)}")
print(f"Closed trades: {len(closed)}")
print(f"Active positions: {len(active)}")

# =============================================================================
# CLOSED TRADES ANALYSIS
# =============================================================================
if len(closed) > 0:
    ret = closed['return_pct']
    wins = ret > 0

    print(f"\n{'='*70}")
    print("CLOSED TRADES PERFORMANCE")
    print(f"{'='*70}")
    print(f"Trades: {len(ret)} | Win Rate: {wins.mean()*100:.1f}%")
    print(f"Avg Return: {ret.mean():+.2f}%")
    print(f"Avg Win: +{ret[wins].mean():.1f}% | Avg Loss: {ret[~wins].mean():.1f}%")
    print(f"Total P&L: ${closed['pnl'].sum():+,.0f}")

    if (~wins).any() and ret[~wins].sum() != 0:
        pf = ret[wins].sum() / abs(ret[~wins].sum())
        print(f"Profit Factor: {pf:.2f}")

# =============================================================================
# ACTIVE POSITIONS
# =============================================================================
if len(active) > 0:
    print(f"\n{'='*70}")
    print("CURRENTLY ACTIVE POSITIONS")
    print(f"{'='*70}")
    print(f"{'Ticker':<8} {'Entry Date':<12} {'Entry $':<10} {'Current %':<10} {'Days':<6}")
    print("-" * 50)

    for _, row in active.sort_values('entry_date', ascending=False).iterrows():
        days_held = (datetime.now() - row['entry_date']).days
        print(f"{row['ticker']:<8} {row['entry_date'].strftime('%Y-%m-%d'):<12} ${row['entry_price']:<9.2f} {row['return_pct']:+.1f}%{'':<5} {days_held:<6}")

    print(f"\nActive positions P&L: ${active['pnl'].sum():+,.0f}")

# =============================================================================
# EQUITY CURVE vs SPY
# =============================================================================
print(f"\n{'='*70}")
print("EQUITY CURVE vs SPY BUY & HOLD")
print(f"{'='*70}")

# Build equity curve from closed trades
equity_events = []
for _, trade in closed.iterrows():
    equity_events.append({
        'date': trade['exit_date'],
        'pnl': trade['pnl']
    })

equity_df = pd.DataFrame(equity_events)
if len(equity_df) > 0:
    equity_df = equity_df.sort_values('date')
    equity_df['cumulative_pnl'] = equity_df['pnl'].cumsum()
    equity_df['equity'] = STARTING_CAPITAL + equity_df['cumulative_pnl']

# SPY buy and hold
spy_start = spy_df['Close'].iloc[0]
spy_end = spy_df['Close'].iloc[-1]
spy_return = (spy_end - spy_start) / spy_start * 100
spy_final = STARTING_CAPITAL * (1 + spy_return / 100)

# Strategy final (closed + active unrealized)
strategy_closed_pnl = closed['pnl'].sum() if len(closed) > 0 else 0
strategy_active_pnl = active['pnl'].sum() if len(active) > 0 else 0
strategy_total_pnl = strategy_closed_pnl + strategy_active_pnl
strategy_final = STARTING_CAPITAL + strategy_total_pnl

print(f"\nStarting Capital: ${STARTING_CAPITAL:,.0f}")
print(f"\nSPY Buy & Hold:")
print(f"  Return: {spy_return:+.1f}%")
print(f"  Final: ${spy_final:,.0f}")

print(f"\nMarket Sniper Strategy:")
print(f"  Closed P&L: ${strategy_closed_pnl:+,.0f}")
print(f"  Active P&L: ${strategy_active_pnl:+,.0f} (unrealized)")
print(f"  Total P&L: ${strategy_total_pnl:+,.0f}")
print(f"  Return: {strategy_total_pnl/STARTING_CAPITAL*100:+.1f}%")
print(f"  Final: ${strategy_final:,.0f}")

# Winner?
print(f"\n{'='*70}")
if strategy_total_pnl > (spy_final - STARTING_CAPITAL):
    print(f"STRATEGY BEATS SPY by ${strategy_total_pnl - (spy_final - STARTING_CAPITAL):,.0f}")
else:
    print(f"SPY BEATS STRATEGY by ${(spy_final - STARTING_CAPITAL) - strategy_total_pnl:,.0f}")
print(f"{'='*70}")

# =============================================================================
# YEARLY COMPARISON
# =============================================================================
print(f"\n{'='*70}")
print("YEARLY COMPARISON: Strategy vs SPY")
print(f"{'='*70}")

closed['year'] = closed['exit_date'].dt.year
spy_df['year'] = spy_df.index.year

print(f"{'Year':<6} {'Strategy P&L':<15} {'Strategy %':<12} {'SPY %':<10} {'Winner':<10}")
print("-" * 60)

years = sorted(closed['year'].unique())
for year in years:
    # Strategy P&L for year
    year_closed = closed[closed['year'] == year]
    year_pnl = year_closed['pnl'].sum()
    year_pct = year_pnl / STARTING_CAPITAL * 100

    # SPY return for year
    spy_year = spy_df[spy_df['year'] == year]['Close']
    if len(spy_year) > 1:
        spy_pct = (spy_year.iloc[-1] - spy_year.iloc[0]) / spy_year.iloc[0] * 100
    else:
        spy_pct = 0

    winner = "STRATEGY" if year_pct > spy_pct else "SPY"
    print(f"{year:<6} ${year_pnl:<+14,.0f} {year_pct:<+12.1f} {spy_pct:<+10.1f} {winner:<10}")

# =============================================================================
# PLOT EQUITY CURVE
# =============================================================================
if len(equity_df) > 0:
    print(f"\n{'='*70}")
    print("EQUITY CURVE CHART")
    print(f"{'='*70}")

    fig, ax = plt.subplots(figsize=(12, 6))

    # Strategy equity curve
    ax.plot(equity_df['date'], equity_df['equity'], label='Market Sniper', linewidth=2, color='blue')

    # SPY equity curve
    spy_equity = spy_df.copy()
    spy_equity['equity'] = STARTING_CAPITAL * (spy_equity['Close'] / spy_equity['Close'].iloc[0])
    ax.plot(spy_equity.index, spy_equity['equity'], label='SPY Buy & Hold', linewidth=2, color='gray', alpha=0.7)

    # Starting capital line
    ax.axhline(y=STARTING_CAPITAL, color='black', linestyle='--', alpha=0.3, label='Starting Capital')

    ax.set_xlabel('Date')
    ax.set_ylabel('Portfolio Value ($)')
    ax.set_title('Market Sniper Strategy vs SPY Buy & Hold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('equity_curve.png', dpi=150)
    plt.show()

    print("\nChart saved to equity_curve.png")

# =============================================================================
# SAVE RESULTS
# =============================================================================
df.to_csv('backtest_results.csv', index=False)
print(f"\nResults saved to backtest_results.csv")

try:
    from google.colab import files
    files.download('backtest_results.csv')
    files.download('equity_curve.png')
except:
    pass
