# =============================================================================
# MARKET SNIPER - VIX OPTIMIZATION
# =============================================================================
# Tests different VIX ranges to find optimal crash protection
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
# VIX RANGES TO TEST
# =============================================================================
VIX_CONFIGS = [
    {'name': 'Wide (20-50)', 'min': 20, 'max': 50},
    {'name': 'Moderate (20-40)', 'min': 20, 'max': 40},
    {'name': 'Conservative (20-35)', 'min': 20, 'max': 35},
    {'name': 'Tight (20-30)', 'min': 20, 'max': 30},
    {'name': 'Sweet Spot (22-38)', 'min': 22, 'max': 38},
    {'name': 'Higher Floor (25-40)', 'min': 25, 'max': 40},
    {'name': 'Recovery Only (18-28)', 'min': 18, 'max': 28},
]

# =============================================================================
# TICKERS (smaller set for faster testing)
# =============================================================================
TICKERS = [
    # Top 150 most liquid stocks
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
    # MidCaps
    'ALLY', 'BHF', 'CF', 'CLF', 'DKS', 'EAT', 'GL', 'HRI', 'JBL', 'KBH',
    'LAD', 'MHO', 'MTH', 'ORI', 'RH', 'RS', 'SAIA', 'TOL', 'TPH', 'URBN',
]

TICKERS = sorted(list(set(TICKERS)))
print(f"Total tickers for optimization: {len(TICKERS)}")

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
vix_lookup = {date.strftime('%Y-%m-%d'): float(row['Close']) for date, row in vix.iterrows()}

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
# RUN BACKTEST FOR A VIX CONFIG
# =============================================================================
def run_backtest(vix_min, vix_max):
    """Run backtest with given VIX range"""
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
            vix_val = vix_lookup.get(date_str, 15)

            # VIX FILTER with ceiling
            if not (vix_min <= vix_val <= vix_max):
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

    # Overall stats
    total_pnl = df['pnl'].sum()
    win_rate = (df['return_pct'] > 0).mean() * 100
    avg_return = df['return_pct'].mean()
    num_trades = len(df)

    # Yearly breakdown
    yearly = df.groupby('year').agg({
        'pnl': 'sum',
        'return_pct': ['count', 'mean', lambda x: (x > 0).mean() * 100]
    })
    yearly.columns = ['pnl', 'trades', 'avg_ret', 'win_rate']

    # Crash years
    crash_2020 = yearly.loc[2020, 'pnl'] if 2020 in yearly.index else 0
    crash_2022 = yearly.loc[2022, 'pnl'] if 2022 in yearly.index else 0

    # Max drawdown (simplified - worst year)
    worst_year_pnl = yearly['pnl'].min()

    # Risk-adjusted
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
print("VIX RANGE OPTIMIZATION")
print(f"Testing {len(VIX_CONFIGS)} configurations...")
print(f"{'='*70}")

results = []

for config in VIX_CONFIGS:
    print(f"\nTesting {config['name']}...")
    signals = run_backtest(config['min'], config['max'])
    analysis = analyze_results(signals, config['name'])
    if analysis:
        results.append(analysis)
        print(f"  Trades: {analysis['num_trades']} | WR: {analysis['win_rate']:.1f}% | P&L: ${analysis['total_pnl']:+,.0f}")
        print(f"  2020: ${analysis['crash_2020']:+,.0f} | 2022: ${analysis['crash_2022']:+,.0f}")

# =============================================================================
# RESULTS COMPARISON
# =============================================================================
print(f"\n{'='*70}")
print("OPTIMIZATION RESULTS")
print(f"{'='*70}")

# Sort by different metrics
print("\n--- BY TOTAL P&L ---")
sorted_pnl = sorted(results, key=lambda x: x['total_pnl'], reverse=True)
print(f"{'Config':<25} {'Trades':<8} {'WR%':<8} {'Total P&L':<15} {'2020':<12} {'2022':<12}")
print("-" * 80)
for r in sorted_pnl:
    print(f"{r['name']:<25} {r['num_trades']:<8} {r['win_rate']:<8.1f} ${r['total_pnl']:<+14,.0f} ${r['crash_2020']:<+11,.0f} ${r['crash_2022']:<+11,.0f}")

print("\n--- BY CRASH PROTECTION (2020 + 2022 combined) ---")
sorted_crash = sorted(results, key=lambda x: x['crash_2020'] + x['crash_2022'], reverse=True)
print(f"{'Config':<25} {'Crash Loss':<15} {'Total P&L':<15} {'Trades':<8}")
print("-" * 70)
for r in sorted_crash:
    crash_total = r['crash_2020'] + r['crash_2022']
    print(f"{r['name']:<25} ${crash_total:<+14,.0f} ${r['total_pnl']:<+14,.0f} {r['num_trades']:<8}")

print("\n--- BY RISK-ADJUSTED (P&L / Worst Year) ---")
sorted_sharpe = sorted(results, key=lambda x: x['sharpe_proxy'], reverse=True)
print(f"{'Config':<25} {'Ratio':<10} {'Total P&L':<15} {'Worst Year':<12}")
print("-" * 70)
for r in sorted_sharpe:
    print(f"{r['name']:<25} {r['sharpe_proxy']:<10.2f} ${r['total_pnl']:<+14,.0f} ${r['worst_year']:<+11,.0f}")

# =============================================================================
# BEST CONFIGS SUMMARY
# =============================================================================
print(f"\n{'='*70}")
print("RECOMMENDED CONFIGURATIONS")
print(f"{'='*70}")

best_pnl = sorted_pnl[0]
best_crash = sorted_crash[0]
best_sharpe = sorted_sharpe[0]

print(f"\nBest Total Returns: {best_pnl['name']}")
print(f"  P&L: ${best_pnl['total_pnl']:+,.0f} | Trades: {best_pnl['num_trades']} | WR: {best_pnl['win_rate']:.1f}%")

print(f"\nBest Crash Protection: {best_crash['name']}")
print(f"  2020+2022 Loss: ${best_crash['crash_2020'] + best_crash['crash_2022']:+,.0f} | Total P&L: ${best_crash['total_pnl']:+,.0f}")

print(f"\nBest Risk-Adjusted: {best_sharpe['name']}")
print(f"  Ratio: {best_sharpe['sharpe_proxy']:.2f} | P&L: ${best_sharpe['total_pnl']:+,.0f} | Worst Year: ${best_sharpe['worst_year']:+,.0f}")

# =============================================================================
# YEARLY COMPARISON CHART
# =============================================================================
print(f"\n{'='*70}")
print("YEARLY COMPARISON")
print(f"{'='*70}")

# Get SPY annual returns
spy_df['year'] = spy_df.index.year
spy_annual = {}
for year in spy_df['year'].unique():
    yd = spy_df[spy_df['year'] == year]['Close']
    if len(yd) > 1:
        spy_annual[year] = (yd.iloc[-1] - yd.iloc[0]) / yd.iloc[0] * 100

years = sorted(set(spy_annual.keys()) & set(range(2019, 2026)))

print(f"\n{'Year':<6}", end="")
for r in results[:4]:  # Top 4 configs
    print(f"{r['name'][:15]:<18}", end="")
print(f"{'SPY':<10}")

print("-" * 90)
for year in years:
    print(f"{year:<6}", end="")
    for r in results[:4]:
        if year in r['yearly'].index:
            pnl = r['yearly'].loc[year, 'pnl']
            print(f"${pnl:<+17,.0f}", end="")
        else:
            print(f"{'N/A':<18}", end="")
    spy_ret = spy_annual.get(year, 0)
    print(f"{spy_ret:+.1f}%")

# =============================================================================
# VISUALIZATION
# =============================================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Total P&L comparison
ax1 = axes[0, 0]
names = [r['name'] for r in sorted_pnl]
pnls = [r['total_pnl'] for r in sorted_pnl]
colors = ['green' if p > 0 else 'red' for p in pnls]
ax1.barh(names, pnls, color=colors)
ax1.set_xlabel('Total P&L ($)')
ax1.set_title('Total P&L by VIX Config')
ax1.axvline(x=0, color='black', linewidth=0.5)

# 2. Crash performance
ax2 = axes[0, 1]
crash_2020 = [r['crash_2020'] for r in results]
crash_2022 = [r['crash_2022'] for r in results]
x = np.arange(len(results))
width = 0.35
ax2.bar(x - width/2, crash_2020, width, label='2020', color='blue', alpha=0.7)
ax2.bar(x + width/2, crash_2022, width, label='2022', color='orange', alpha=0.7)
ax2.set_ylabel('P&L ($)')
ax2.set_title('Crash Year Performance')
ax2.set_xticks(x)
ax2.set_xticklabels([r['name'][:10] for r in results], rotation=45, ha='right')
ax2.legend()
ax2.axhline(y=0, color='black', linewidth=0.5)

# 3. Win rate vs Trades
ax3 = axes[1, 0]
trades = [r['num_trades'] for r in results]
win_rates = [r['win_rate'] for r in results]
ax3.scatter(trades, win_rates, s=100, c=pnls, cmap='RdYlGn')
for i, r in enumerate(results):
    ax3.annotate(r['name'][:8], (trades[i], win_rates[i]), fontsize=8)
ax3.set_xlabel('Number of Trades')
ax3.set_ylabel('Win Rate (%)')
ax3.set_title('Win Rate vs Trade Volume')

# 4. Risk-adjusted ranking
ax4 = axes[1, 1]
sharpes = [r['sharpe_proxy'] for r in sorted_sharpe]
names_sharpe = [r['name'] for r in sorted_sharpe]
ax4.barh(names_sharpe, sharpes, color='purple', alpha=0.7)
ax4.set_xlabel('Risk-Adjusted Ratio')
ax4.set_title('Risk-Adjusted Performance')

plt.tight_layout()
plt.savefig('vix_optimization.png', dpi=150)
plt.show()

print("\nChart saved to vix_optimization.png")
