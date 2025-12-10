# =============================================================================
# VIX SCREENER - STOP MODE OPTIMIZATION
# =============================================================================
# Tests all combinations of stop modes and entry timing to find the best
# Run in Google Colab: Takes ~40-60 min for full optimization
# =============================================================================

!pip install yfinance pandas numpy -q

import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================
START_DATE = '2019-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
STARTING_CAPITAL = 100000
RISK_PER_TRADE_PCT = 1.0
MAX_POSITION_PCT = 15.0
MAX_HOLD_DAYS = 120
USE_TRAILING = True

# VIX Filter
VIX_MIN = 20
VIX_MAX = 35

# Technical
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
MIN_MARKET_CAP = 1e9
MIN_BARS = 500
VOLUME_SURGE_MULT = 1.2

# Fixed stop settings
FIXED_STOP_PCT = 15.0
FIXED_TP_PCT = 50.0
FIXED_TRAIL_PCT = 10.0

# ATR settings
ATR_STOP_MULT = 2.5
ATR_TRAIL_MULT = 2.0

# Pivot settings
PIVOT_LOOKBACK = 20
PIVOT_BUFFER_PCT = 1.0

# Hybrid settings
HYBRID_ATR_BUFFER = 0.5

# Dynamic stop bounds
MIN_STOP_PCT = 5.0
MAX_STOP_PCT = 25.0
REWARD_RISK_RATIO = 3.0

# =============================================================================
# COMBINATIONS TO TEST
# =============================================================================
STOP_MODES = ['fixed', 'atr', 'pivot', 'hybrid']
ENTRY_TIMINGS = ['same_day', 'next_open', 'next_close']

# Use 'fast' for quicker optimization, 'medium' for full test
SCAN_MODE = 'fast'  # ~500 tickers, ~5 min per combination

# =============================================================================
# TICKER FETCHING
# =============================================================================
import requests
from io import StringIO

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_sp500_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url, storage_options={'User-Agent': HEADERS['User-Agent']})
        return tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
    except:
        return []

def get_sp400_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
        tables = pd.read_html(url, storage_options={'User-Agent': HEADERS['User-Agent']})
        df = tables[0]
        col = 'Symbol' if 'Symbol' in df.columns else 'Ticker Symbol'
        return df[col].str.replace('.', '-', regex=False).tolist()
    except:
        return []

def get_tickers(mode='fast'):
    tickers = get_sp500_tickers()
    if mode == 'medium':
        tickers.extend(get_sp400_tickers())
    tickers = sorted(list(set(tickers)))

    if len(tickers) < 100:
        # Fallback
        tickers = ['AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'AMD', 'AMGN', 'AMZN', 'AVGO', 'AXP',
                   'BA', 'BAC', 'BK', 'BKNG', 'BLK', 'BMY', 'C', 'CAT', 'CL', 'CMCSA',
                   'COP', 'COST', 'CRM', 'CSCO', 'CVS', 'CVX', 'DE', 'DHR', 'DIS', 'DOW',
                   'EMR', 'F', 'FDX', 'GD', 'GE', 'GILD', 'GM', 'GOOG', 'GS', 'HD',
                   'HON', 'IBM', 'INTC', 'INTU', 'ISRG', 'JNJ', 'JPM', 'KO', 'LIN', 'LLY',
                   'LMT', 'LOW', 'MA', 'MCD', 'MDLZ', 'MDT', 'META', 'MMM', 'MO', 'MRK',
                   'MS', 'MSFT', 'NEE', 'NFLX', 'NKE', 'NOW', 'NVDA', 'ORCL', 'PEP', 'PFE',
                   'PG', 'PM', 'QCOM', 'RTX', 'SBUX', 'SO', 'T', 'TGT', 'TMO', 'TMUS',
                   'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'V', 'VZ', 'WFC', 'WMT', 'XOM']
    return tickers

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

def calc_atr(high, low, close, length=14):
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, min_periods=length, adjust=False).mean().fillna(0)

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

def find_swing_low(low_prices, idx, lookback=20):
    start = max(0, idx - lookback)
    window = low_prices[start:idx]
    if len(window) < 5:
        return low_prices[idx]
    swing_lows = []
    for i in range(2, len(window) - 2):
        if (window[i] < window[i-1] and window[i] < window[i-2] and
            window[i] < window[i+1] and window[i] < window[i+2]):
            swing_lows.append(window[i])
    return min(swing_lows) if swing_lows else min(window)

def calc_dynamic_stop(entry_price, atr_value, low_prices, idx, mode):
    if mode == 'fixed':
        return FIXED_STOP_PCT, FIXED_TP_PCT, FIXED_TRAIL_PCT

    elif mode == 'atr':
        stop_distance = atr_value * ATR_STOP_MULT
        stop_pct = (stop_distance / entry_price) * 100
        trail_pct = (atr_value * ATR_TRAIL_MULT / entry_price) * 100

    elif mode == 'pivot':
        swing_low = find_swing_low(low_prices, idx, PIVOT_LOOKBACK)
        stop_price = swing_low * (1 - PIVOT_BUFFER_PCT / 100)
        stop_pct = ((entry_price - stop_price) / entry_price) * 100
        trail_pct = stop_pct * 0.7

    elif mode == 'hybrid':
        swing_low = find_swing_low(low_prices, idx, PIVOT_LOOKBACK)
        atr_buffer = atr_value * HYBRID_ATR_BUFFER
        stop_price = swing_low - atr_buffer
        stop_pct = ((entry_price - stop_price) / entry_price) * 100
        trail_pct = (atr_value * ATR_TRAIL_MULT / entry_price) * 100

    else:
        return FIXED_STOP_PCT, FIXED_TP_PCT, FIXED_TRAIL_PCT

    stop_pct = max(MIN_STOP_PCT, min(MAX_STOP_PCT, stop_pct))
    trail_pct = max(MIN_STOP_PCT * 0.5, min(MAX_STOP_PCT * 0.7, trail_pct))
    tp_pct = stop_pct * REWARD_RISK_RATIO

    return round(stop_pct, 1), round(tp_pct, 1), round(trail_pct, 1)

# =============================================================================
# TRADE EXECUTION
# =============================================================================
def execute_trade(close, high, low, entry_idx, entry_price, dates, stop_pct, tp_pct, trail_pct):
    stop_price = entry_price * (1 - stop_pct / 100)
    tp_price = entry_price * (1 + tp_pct / 100)
    activation_price = entry_price * (1 + stop_pct / 100)
    highest_high = entry_price
    trailing_active = False
    trailing_stop = stop_price

    for day in range(1, MAX_HOLD_DAYS + 1):
        idx = entry_idx + day
        if idx >= len(close):
            return {'return_pct': (close[-1] - entry_price) / entry_price * 100, 'exit_reason': 'still_open'}

        day_high, day_low = high[idx], low[idx]
        if day_high > highest_high:
            highest_high = day_high

        if USE_TRAILING and not trailing_active and day_high >= activation_price:
            trailing_active = True
        if trailing_active:
            trailing_stop = max(trailing_stop, highest_high * (1 - trail_pct / 100))

        current_stop = trailing_stop if trailing_active else stop_price

        if day_low <= current_stop:
            return {'return_pct': (current_stop - entry_price) / entry_price * 100, 'exit_reason': 'stop'}
        if day_high >= tp_price:
            return {'return_pct': tp_pct, 'exit_reason': 'target'}

    exit_price = close[entry_idx + MAX_HOLD_DAYS]
    return {'return_pct': (exit_price - entry_price) / entry_price * 100, 'exit_reason': 'max_days'}

# =============================================================================
# RUN BACKTEST FOR ONE CONFIGURATION
# =============================================================================
def run_backtest(tickers, vix_lookup, stop_mode, entry_timing, stock_cache):
    signals = []

    for ticker in tickers:
        try:
            if ticker not in stock_cache:
                continue

            df, info = stock_cache[ticker]
            close = df['Close'].values
            high = df['High'].values
            low = df['Low'].values
            open_prices = df['Open'].values
            volume = df['Volume'].values
            dates = df.index

            close_s = pd.Series(close)
            high_s = pd.Series(high)
            low_s = pd.Series(low)
            vol_s = pd.Series(volume)

            rsi = calc_rsi(close_s, 14).values
            adx, _, _ = calc_adx(high_s, low_s, close_s, 14)
            adx = adx.values
            atr = calc_atr(high_s, low_s, close_s, 14).values
            sma_200 = close_s.rolling(200).mean().values
            sma_slope = ((pd.Series(sma_200) - pd.Series(sma_200).shift(SMA_SLOPE_DAYS)) / pd.Series(sma_200).shift(SMA_SLOPE_DAYS) * 100).values
            high_52w = high_s.rolling(252).max().values
            vol_avg = vol_s.rolling(VOLUME_AVG_DAYS).mean().values

            last_idx = -999

            for i in range(260, len(df)):
                if i - last_idx < MIN_GAP_DAYS:
                    continue

                date_str = dates[i].strftime('%Y-%m-%d')
                vix_val = vix_lookup.get(date_str, 15)

                if not (VIX_MIN <= vix_val <= VIX_MAX):
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

                if np.isnan(vol_avg[i]) or vol_avg[i] == 0 or volume[i] / vol_avg[i] < VOLUME_SURGE_MULT:
                    continue

                # Entry timing
                if entry_timing == 'same_day':
                    entry_idx = i
                    entry_price = close[i]
                elif entry_timing == 'next_open':
                    if i + 1 >= len(df):
                        continue
                    entry_idx = i + 1
                    entry_price = open_prices[i + 1]
                else:  # next_close
                    if i + 1 >= len(df):
                        continue
                    entry_idx = i + 1
                    entry_price = close[i + 1]

                # Dynamic stop
                atr_val = atr[entry_idx] if not np.isnan(atr[entry_idx]) else entry_price * 0.02
                stop_pct, tp_pct, trail_pct = calc_dynamic_stop(entry_price, atr_val, low, entry_idx, stop_mode)

                trade = execute_trade(close, high, low, entry_idx, entry_price, dates, stop_pct, tp_pct, trail_pct)

                risk_dollars = STARTING_CAPITAL * (RISK_PER_TRADE_PCT / 100)
                position = min(risk_dollars / (stop_pct / 100), STARTING_CAPITAL * MAX_POSITION_PCT / 100)
                pnl = position * trade['return_pct'] / 100

                signals.append({
                    'return_pct': trade['return_pct'],
                    'pnl': pnl,
                    'exit_reason': trade['exit_reason'],
                    'stop_pct': stop_pct,
                })
                last_idx = i

        except Exception as e:
            continue

    return signals

# =============================================================================
# MAIN OPTIMIZATION
# =============================================================================
print("=" * 70)
print("VIX SCREENER - STOP MODE OPTIMIZATION")
print("=" * 70)

# Get tickers
print(f"\nFetching tickers (mode: {SCAN_MODE})...")
TICKERS = get_tickers(SCAN_MODE)
print(f"Tickers: {len(TICKERS)}")

# Download VIX
print("\nDownloading VIX data...")
vix = yf.download('^VIX', start=START_DATE, end=END_DATE, progress=False)
if isinstance(vix.columns, pd.MultiIndex):
    vix.columns = [col[0] for col in vix.columns]
vix_lookup = {date.strftime('%Y-%m-%d'): float(row['Close']) for date, row in vix.iterrows()}

# Pre-download all stock data (cache to avoid re-downloading for each config)
print("\nDownloading stock data (this takes a few minutes)...")
stock_cache = {}
for i, ticker in enumerate(TICKERS):
    if (i + 1) % 50 == 0:
        print(f"  [{i+1}/{len(TICKERS)}] Downloaded")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if (info.get('marketCap', 0) or 0) < MIN_MARKET_CAP:
            continue
        df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
        if df is None or len(df) < MIN_BARS:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        stock_cache[ticker] = (df, info)
    except:
        continue
    if (i + 1) % 100 == 0:
        time.sleep(1)

print(f"Cached {len(stock_cache)} stocks")

# Run all combinations
print("\n" + "=" * 70)
print("RUNNING OPTIMIZATION")
print("=" * 70)

results = []
total_combos = len(STOP_MODES) * len(ENTRY_TIMINGS)
combo_num = 0

for stop_mode in STOP_MODES:
    for entry_timing in ENTRY_TIMINGS:
        combo_num += 1
        print(f"\n[{combo_num}/{total_combos}] Testing: {stop_mode.upper()} + {entry_timing.upper()}...")

        start_time = time.time()
        signals = run_backtest(TICKERS, vix_lookup, stop_mode, entry_timing, stock_cache)
        elapsed = time.time() - start_time

        if len(signals) == 0:
            print(f"  No signals found")
            continue

        # Calculate metrics
        df_signals = pd.DataFrame(signals)
        closed = df_signals[df_signals['exit_reason'] != 'still_open']

        if len(closed) == 0:
            print(f"  No closed trades")
            continue

        total_trades = len(closed)
        wins = (closed['return_pct'] > 0).sum()
        win_rate = wins / total_trades * 100
        total_pnl = closed['pnl'].sum()
        avg_return = closed['return_pct'].mean()
        avg_stop = closed['stop_pct'].mean()

        results.append({
            'stop_mode': stop_mode,
            'entry_timing': entry_timing,
            'trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_return': avg_return,
            'avg_stop': avg_stop,
        })

        print(f"  Trades: {total_trades} | Win Rate: {win_rate:.1f}% | P&L: ${total_pnl:+,.0f} | Avg Stop: {avg_stop:.1f}%")

# =============================================================================
# RESULTS SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("OPTIMIZATION RESULTS - SORTED BY P&L")
print("=" * 70)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('total_pnl', ascending=False)

print(f"\n{'Stop Mode':<10} {'Entry':<12} {'Trades':<8} {'Win %':<8} {'Total P&L':<12} {'Avg Ret':<8} {'Avg Stop':<8}")
print("-" * 70)

for _, row in results_df.iterrows():
    print(f"{row['stop_mode']:<10} {row['entry_timing']:<12} {row['trades']:<8} {row['win_rate']:.1f}%{'':<3} ${row['total_pnl']:>+10,.0f} {row['avg_return']:>+6.1f}% {row['avg_stop']:>6.1f}%")

# Best configuration
best = results_df.iloc[0]
print("\n" + "=" * 70)
print(f"BEST CONFIGURATION: {best['stop_mode'].upper()} + {best['entry_timing'].upper()}")
print(f"  Total P&L: ${best['total_pnl']:+,.0f}")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"  Avg Stop: {best['avg_stop']:.1f}%")
print("=" * 70)

# Save results
results_df.to_csv('stop_optimization_results.csv', index=False)
print("\nResults saved to stop_optimization_results.csv")

try:
    from google.colab import files
    files.download('stop_optimization_results.csv')
except:
    pass
