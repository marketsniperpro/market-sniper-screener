# =============================================================================
# MARKET SNIPER - SMART VIX (Buy on Stabilization, Not Freefall)
# =============================================================================
# Instead of just VIX ceiling, detect when crash is stabilizing:
# - VIX is elevated (fear present)
# - BUT VIX is dropping from recent peak (panic subsiding)
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
# SMART VIX CONFIGS TO TEST
# =============================================================================
VIX_CONFIGS = [
    # Original - no ceiling
    {
        'name': 'Original (20-50)',
        'min': 20, 'max': 50,
        'require_stabilization': False,
    },
    # Simple ceiling
    {
        'name': 'Ceiling (20-35)',
        'min': 20, 'max': 35,
        'require_stabilization': False,
    },
    # SMART: VIX dropping from 5-day peak
    {
        'name': 'Smart 5d Drop 10%',
        'min': 20, 'max': 60,
        'require_stabilization': True,
        'lookback_days': 5,
        'drop_from_peak_pct': 10,
    },
    # SMART: VIX dropping from 10-day peak
    {
        'name': 'Smart 10d Drop 15%',
        'min': 20, 'max': 60,
        'require_stabilization': True,
        'lookback_days': 10,
        'drop_from_peak_pct': 15,
    },
    # SMART: VIX dropping from 10-day peak (tighter)
    {
        'name': 'Smart 10d Drop 20%',
        'min': 20, 'max': 60,
        'require_stabilization': True,
        'lookback_days': 10,
        'drop_from_peak_pct': 20,
    },
    # SMART: Stricter - must drop significantly
    {
        'name': 'Smart 15d Drop 25%',
        'min': 20, 'max': 80,  # Allow entry even when VIX was very high
        'require_stabilization': True,
        'lookback_days': 15,
        'drop_from_peak_pct': 25,
    },
    # SMART + Ceiling combo
    {
        'name': 'Smart+Cap (20-40, 10d 15%)',
        'min': 20, 'max': 40,
        'require_stabilization': True,
        'lookback_days': 10,
        'drop_from_peak_pct': 15,
    },
    # Conservative stabilization
    {
        'name': 'Very Smart (5d 20%)',
        'min': 18, 'max': 50,
        'require_stabilization': True,
        'lookback_days': 5,
        'drop_from_peak_pct': 20,
    },
]

# =============================================================================
# TICKERS - Dynamic fetching from official sources
# =============================================================================
import requests
from io import StringIO

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# 'fast'   = ~500 stocks  (~5-8 min per config)
# 'medium' = ~900 stocks  (~10-15 min per config)
SCAN_MODE = 'medium'

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

def get_all_tickers(mode='medium'):
    print("=" * 50)
    print(f"Fetching tickers (mode: {mode})...")
    print("=" * 50)
    all_tickers = []
    if mode == 'fast':
        all_tickers.extend(get_sp500_tickers())
    else:  # medium
        all_tickers.extend(get_sp500_tickers())
        time.sleep(0.5)
        all_tickers.extend(get_sp400_tickers())
    tickers = sorted(list(set(all_tickers)))
    tickers = [t for t in tickers if t and isinstance(t, str) and 1 <= len(t) <= 5]
    print(f"Total tickers: {len(tickers)}")
    print("=" * 50)
    return tickers

TICKERS = get_all_tickers(SCAN_MODE)

# Fallback if fetching fails
if len(TICKERS) < 100:
    print("⚠️ Fetch failed, using fallback list...")
    TICKERS = [
        'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'AIG', 'ALL', 'AMAT', 'AMD', 'AMGN',
        'AMZN', 'ANET', 'AON', 'AXP', 'BA', 'BAC', 'BK', 'BKNG', 'BLK', 'BMY',
        'BRK-B', 'C', 'CAT', 'CHTR', 'CI', 'CL', 'CMCSA', 'COF', 'COP', 'COST',
        'CRM', 'CSCO', 'CVS', 'CVX', 'D', 'DE', 'DHI', 'DHR', 'DIS', 'DOW',
        'DUK', 'EMR', 'EOG', 'EXC', 'F', 'FCX', 'FDX', 'GD', 'GE', 'GILD',
        'GM', 'GOOG', 'GS', 'HD', 'HON', 'IBM', 'INTC', 'ISRG', 'JNJ', 'JPM',
        'KO', 'LEN', 'LIN', 'LLY', 'LMT', 'LOW', 'MA', 'MCD', 'MDLZ', 'MDT',
        'MET', 'META', 'MMM', 'MO', 'MPC', 'MRK', 'MS', 'MSFT', 'NEE', 'NFLX',
        'NKE', 'NVDA', 'ORCL', 'OXY', 'PEP', 'PFE', 'PG', 'PM', 'PYPL', 'QCOM',
        'RTX', 'SBUX', 'SCHW', 'SLB', 'SO', 'SPG', 'T', 'TGT', 'TMO', 'TSLA',
        'TXN', 'UNH', 'UNP', 'UPS', 'USB', 'V', 'VLO', 'VZ', 'WFC', 'WMT', 'XOM',
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
    return adx.fillna(0)

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
    return score >= 4

# =============================================================================
# DATA LOADING
# =============================================================================
print("\nDownloading VIX data...")
vix = yf.download('^VIX', start=START_DATE, end=END_DATE, progress=False)
if isinstance(vix.columns, pd.MultiIndex):
    vix.columns = [col[0] for col in vix.columns]

# Create VIX lookup with date -> close
vix_lookup = {date.strftime('%Y-%m-%d'): float(row['Close']) for date, row in vix.iterrows()}

# Create VIX peak lookup (for stabilization detection)
vix['peak_5d'] = vix['Close'].rolling(5).max()
vix['peak_10d'] = vix['Close'].rolling(10).max()
vix['peak_15d'] = vix['Close'].rolling(15).max()
vix['drop_from_5d'] = (vix['peak_5d'] - vix['Close']) / vix['peak_5d'] * 100
vix['drop_from_10d'] = (vix['peak_10d'] - vix['Close']) / vix['peak_10d'] * 100
vix['drop_from_15d'] = (vix['peak_15d'] - vix['Close']) / vix['peak_15d'] * 100

vix_data = {date.strftime('%Y-%m-%d'): {
    'close': float(row['Close']),
    'peak_5d': float(row['peak_5d']) if not pd.isna(row['peak_5d']) else float(row['Close']),
    'peak_10d': float(row['peak_10d']) if not pd.isna(row['peak_10d']) else float(row['Close']),
    'peak_15d': float(row['peak_15d']) if not pd.isna(row['peak_15d']) else float(row['Close']),
    'drop_5d': float(row['drop_from_5d']) if not pd.isna(row['drop_from_5d']) else 0,
    'drop_10d': float(row['drop_from_10d']) if not pd.isna(row['drop_from_10d']) else 0,
    'drop_15d': float(row['drop_from_15d']) if not pd.isna(row['drop_from_15d']) else 0,
} for date, row in vix.iterrows()}

print("Downloading SPY data...")
spy_df = yf.download('SPY', start=START_DATE, end=END_DATE, progress=False)
if isinstance(spy_df.columns, pd.MultiIndex):
    spy_df.columns = [col[0] for col in spy_df.columns]

# Pre-load all stock data
print("Pre-loading stock data...")
stock_data = {}
stock_info = {}

for i, ticker in enumerate(TICKERS):
    if (i + 1) % 30 == 0:
        print(f"  Loading [{i+1}/{len(TICKERS)}]...")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if (info.get('marketCap', 0) or 0) < MIN_MARKET_CAP:
            continue
        if USE_FUNDAMENTAL_FILTER and not check_fundamentals(info):
            continue

        df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
        if df is not None and len(df) >= MIN_BARS:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
            stock_data[ticker] = df
            stock_info[ticker] = info
    except:
        pass

    if (i + 1) % 50 == 0:
        time.sleep(1)

print(f"Loaded {len(stock_data)} stocks")

# =============================================================================
# TRADE EXECUTION
# =============================================================================
def execute_trade(close, high, low, entry_idx, entry_price):
    stop_price = entry_price * (1 - STOP_LOSS_PCT / 100)
    tp_price = entry_price * (1 + TAKE_PROFIT_PCT / 100)
    activation_price = entry_price * (1 + TRAIL_ACTIVATION_PCT / 100)
    highest_high = entry_price
    trailing_active = False
    trailing_stop = stop_price

    for day in range(1, MAX_HOLD_DAYS + 1):
        idx = entry_idx + day
        if idx >= len(close):
            return {'return_pct': (close[-1] - entry_price) / entry_price * 100, 'exit_day': day}

        day_high, day_low = high[idx], low[idx]
        if day_high > highest_high:
            highest_high = day_high

        if USE_TRAILING and not trailing_active and day_high >= activation_price:
            trailing_active = True
        if trailing_active:
            trailing_stop = max(trailing_stop, highest_high * (1 - TRAIL_DISTANCE_PCT / 100))

        current_stop = trailing_stop if trailing_active else stop_price

        if day_low <= current_stop:
            return {'return_pct': (current_stop - entry_price) / entry_price * 100, 'exit_day': day}
        if day_high >= tp_price:
            return {'return_pct': TAKE_PROFIT_PCT, 'exit_day': day}

    return {'return_pct': (close[entry_idx + MAX_HOLD_DAYS] - entry_price) / entry_price * 100, 'exit_day': MAX_HOLD_DAYS}

# =============================================================================
# SMART VIX CHECK
# =============================================================================
def check_vix_condition(date_str, config):
    """Check if VIX conditions are met for entry"""
    if date_str not in vix_data:
        return False

    v = vix_data[date_str]
    vix_val = v['close']

    # Basic range check
    if not (config['min'] <= vix_val <= config['max']):
        return False

    # If stabilization required
    if config.get('require_stabilization', False):
        lookback = config.get('lookback_days', 10)
        drop_required = config.get('drop_from_peak_pct', 15)

        # Get the drop from peak
        if lookback == 5:
            drop = v['drop_5d']
        elif lookback == 15:
            drop = v['drop_15d']
        else:
            drop = v['drop_10d']

        # Must have dropped at least X% from recent peak
        if drop < drop_required:
            return False

    return True

# =============================================================================
# RUN BACKTEST
# =============================================================================
def run_backtest(config):
    """Run backtest with given config"""
    all_signals = []

    for ticker, df in stock_data.items():
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values
        dates = df.index

        close_s = pd.Series(close)
        high_s = pd.Series(high)
        low_s = pd.Series(low)
        vol_s = pd.Series(volume)

        rsi = calc_rsi(close_s, 14).values
        adx = calc_adx(high_s, low_s, close_s, 14).values
        sma_200 = close_s.rolling(200).mean().values
        sma_slope = ((pd.Series(sma_200) - pd.Series(sma_200).shift(SMA_SLOPE_DAYS)) / pd.Series(sma_200).shift(SMA_SLOPE_DAYS) * 100).values
        high_52w = high_s.rolling(252).max().values
        vol_avg = vol_s.rolling(VOLUME_AVG_DAYS).mean().values

        last_idx = -999

        for i in range(260, len(df) - MAX_HOLD_DAYS - 5):
            if i - last_idx < MIN_GAP_DAYS:
                continue

            date_str = dates[i].strftime('%Y-%m-%d')

            # SMART VIX CHECK
            if not check_vix_condition(date_str, config):
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

            trade = execute_trade(close, high, low, i, price)
            risk_dollars = STARTING_CAPITAL * (RISK_PER_TRADE_PCT / 100)
            position = min(risk_dollars / (STOP_LOSS_PCT / 100), STARTING_CAPITAL * MAX_POSITION_PCT / 100)

            vix_val = vix_data.get(date_str, {}).get('close', 0)

            all_signals.append({
                'ticker': ticker,
                'date': date_str,
                'entry': price,
                'vix': vix_val,
                'return_pct': trade['return_pct'],
                'exit_day': trade['exit_day'],
                'pnl': position * trade['return_pct'] / 100,
                'year': pd.to_datetime(date_str).year
            })
            last_idx = i

    return all_signals

def analyze_results(signals, name):
    """Analyze backtest results"""
    if not signals:
        return None

    df = pd.DataFrame(signals)

    total_pnl = df['pnl'].sum()
    win_rate = (df['return_pct'] > 0).mean() * 100
    avg_return = df['return_pct'].mean()
    num_trades = len(df)

    yearly = df.groupby('year').agg({
        'pnl': 'sum',
        'return_pct': ['count', 'mean', lambda x: (x > 0).mean() * 100]
    })
    yearly.columns = ['pnl', 'trades', 'avg_ret', 'win_rate']

    crash_2020 = yearly.loc[2020, 'pnl'] if 2020 in yearly.index else 0
    crash_2022 = yearly.loc[2022, 'pnl'] if 2022 in yearly.index else 0

    worst_year_pnl = yearly['pnl'].min()
    sharpe_proxy = total_pnl / abs(worst_year_pnl) if worst_year_pnl != 0 else total_pnl

    return {
        'name': name,
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'num_trades': num_trades,
        'crash_2020': crash_2020,
        'crash_2022': crash_2022,
        'worst_year': worst_year_pnl,
        'sharpe_proxy': sharpe_proxy,
        'yearly': yearly
    }

# =============================================================================
# RUN OPTIMIZATION
# =============================================================================
print(f"\n{'='*70}")
print("SMART VIX OPTIMIZATION")
print("Buy on stabilization, not freefall")
print(f"Testing {len(VIX_CONFIGS)} configurations...")
print(f"{'='*70}")

results = []

for config in VIX_CONFIGS:
    print(f"\nTesting {config['name']}...")
    signals = run_backtest(config)
    analysis = analyze_results(signals, config['name'])
    if analysis:
        results.append(analysis)
        print(f"  Trades: {analysis['num_trades']} | WR: {analysis['win_rate']:.1f}% | P&L: ${analysis['total_pnl']:+,.0f}")
        print(f"  2020: ${analysis['crash_2020']:+,.0f} | 2022: ${analysis['crash_2022']:+,.0f}")

# =============================================================================
# RESULTS
# =============================================================================
print(f"\n{'='*70}")
print("RESULTS COMPARISON")
print(f"{'='*70}")

print("\n--- SORTED BY CRASH PROTECTION (2020 + 2022) ---")
sorted_crash = sorted(results, key=lambda x: x['crash_2020'] + x['crash_2022'], reverse=True)
print(f"{'Config':<28} {'2020':<12} {'2022':<12} {'Crash Sum':<12} {'Total P&L':<12}")
print("-" * 80)
for r in sorted_crash:
    crash_sum = r['crash_2020'] + r['crash_2022']
    print(f"{r['name']:<28} ${r['crash_2020']:<+11,.0f} ${r['crash_2022']:<+11,.0f} ${crash_sum:<+11,.0f} ${r['total_pnl']:<+11,.0f}")

print("\n--- SORTED BY TOTAL P&L ---")
sorted_pnl = sorted(results, key=lambda x: x['total_pnl'], reverse=True)
print(f"{'Config':<28} {'Total P&L':<12} {'WR%':<8} {'Trades':<8} {'Avg Ret':<10}")
print("-" * 70)
for r in sorted_pnl:
    print(f"{r['name']:<28} ${r['total_pnl']:<+11,.0f} {r['win_rate']:<8.1f} {r['num_trades']:<8} {r['avg_return']:<+10.2f}")

print("\n--- SORTED BY RISK-ADJUSTED ---")
sorted_sharpe = sorted(results, key=lambda x: x['sharpe_proxy'], reverse=True)
print(f"{'Config':<28} {'Ratio':<10} {'Total P&L':<12} {'Worst Yr':<12}")
print("-" * 65)
for r in sorted_sharpe:
    print(f"{r['name']:<28} {r['sharpe_proxy']:<10.2f} ${r['total_pnl']:<+11,.0f} ${r['worst_year']:<+11,.0f}")

# =============================================================================
# BEST CONFIG
# =============================================================================
print(f"\n{'='*70}")
print("RECOMMENDATION")
print(f"{'='*70}")

# Find best balance (good crash protection + good returns)
# Score = Total P&L + (crash_2020 + crash_2022) * 2  (weight crash protection more)
scored = [(r, r['total_pnl'] + (r['crash_2020'] + r['crash_2022']) * 2) for r in results]
best = max(scored, key=lambda x: x[1])

print(f"\nBest Balanced Config: {best[0]['name']}")
print(f"  Total P&L: ${best[0]['total_pnl']:+,.0f}")
print(f"  Win Rate: {best[0]['win_rate']:.1f}%")
print(f"  2020 P&L: ${best[0]['crash_2020']:+,.0f}")
print(f"  2022 P&L: ${best[0]['crash_2022']:+,.0f}")
print(f"  Trades: {best[0]['num_trades']}")

# Original for comparison
orig = [r for r in results if 'Original' in r['name']][0]
print(f"\nVs Original (20-50):")
print(f"  Total P&L: ${orig['total_pnl']:+,.0f}")
print(f"  2020 P&L: ${orig['crash_2020']:+,.0f}")
print(f"  2022 P&L: ${orig['crash_2022']:+,.0f}")

improvement_crash = (best[0]['crash_2020'] + best[0]['crash_2022']) - (orig['crash_2020'] + orig['crash_2022'])
improvement_total = best[0]['total_pnl'] - orig['total_pnl']

print(f"\nImprovement:")
print(f"  Crash years: ${improvement_crash:+,.0f} better")
print(f"  Total P&L: ${improvement_total:+,.0f}")

# =============================================================================
# VISUALIZATION
# =============================================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Crash performance comparison
ax1 = axes[0, 0]
names = [r['name'][:15] for r in results]
crash_2020 = [r['crash_2020'] for r in results]
crash_2022 = [r['crash_2022'] for r in results]
x = np.arange(len(results))
width = 0.35
ax1.bar(x - width/2, crash_2020, width, label='2020 (COVID)', color='blue', alpha=0.7)
ax1.bar(x + width/2, crash_2022, width, label='2022 (Bear)', color='orange', alpha=0.7)
ax1.set_ylabel('P&L ($)')
ax1.set_title('Crash Year Performance')
ax1.set_xticks(x)
ax1.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
ax1.legend()
ax1.axhline(y=0, color='black', linewidth=0.5)

# 2. Total P&L
ax2 = axes[0, 1]
sorted_by_pnl = sorted(results, key=lambda x: x['total_pnl'], reverse=True)
pnls = [r['total_pnl'] for r in sorted_by_pnl]
names_pnl = [r['name'][:15] for r in sorted_by_pnl]
colors = ['green' if 'Smart' in n else 'gray' for n in names_pnl]
ax2.barh(names_pnl, pnls, color=colors)
ax2.set_xlabel('Total P&L ($)')
ax2.set_title('Total P&L (Green = Smart VIX)')
ax2.axvline(x=0, color='black', linewidth=0.5)

# 3. Win rate vs Trades scatter
ax3 = axes[1, 0]
trades = [r['num_trades'] for r in results]
win_rates = [r['win_rate'] for r in results]
crash_sums = [r['crash_2020'] + r['crash_2022'] for r in results]
scatter = ax3.scatter(trades, win_rates, s=100, c=crash_sums, cmap='RdYlGn', vmin=min(crash_sums), vmax=max(crash_sums))
for i, r in enumerate(results):
    ax3.annotate(r['name'][:8], (trades[i], win_rates[i]), fontsize=7)
ax3.set_xlabel('Number of Trades')
ax3.set_ylabel('Win Rate (%)')
ax3.set_title('Win Rate vs Trades (Color = Crash Performance)')
plt.colorbar(scatter, ax=ax3, label='Crash P&L')

# 4. Risk-adjusted
ax4 = axes[1, 1]
sorted_sharpe = sorted(results, key=lambda x: x['sharpe_proxy'], reverse=True)
sharpes = [r['sharpe_proxy'] for r in sorted_sharpe]
names_sharpe = [r['name'][:15] for r in sorted_sharpe]
colors_sharpe = ['green' if 'Smart' in n else 'gray' for n in names_sharpe]
ax4.barh(names_sharpe, sharpes, color=colors_sharpe)
ax4.set_xlabel('Risk-Adjusted Ratio')
ax4.set_title('Risk-Adjusted Performance')

plt.tight_layout()
plt.savefig('vix_smart_optimization.png', dpi=150)
plt.show()

print("\nChart saved to vix_smart_optimization.png")
