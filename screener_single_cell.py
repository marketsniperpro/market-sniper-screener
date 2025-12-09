# =============================================================================
# MARKET SNIPER SCREENER - SINGLE CELL VERSION
# =============================================================================
# Copy this entire code into ONE cell in Google Colab and run it
# =============================================================================

!pip install yfinance pandas numpy -q

import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION - CHANGE THESE
# =============================================================================
STOP_LOSS_PCT = 15.0
TAKE_PROFIT_PCT = 50.0
USE_TRAILING = True
TRAIL_ACTIVATION_PCT = 15.0
TRAIL_DISTANCE_PCT = 10.0
MAX_HOLD_DAYS = 120

USE_VIX_FILTER = False        # <-- FALSE = more signals, TRUE = only high fear
VIX_MIN = 25
VIX_MAX = 50

USE_VOLUME_FILTER = True
VOLUME_SURGE_MULT = 1.3

ACCOUNT_SIZE = 100000
RISK_PER_TRADE_PCT = 1.0

START_DATE = '2018-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')

# Other settings
MIN_MARKET_CAP = 1e9
MIN_BARS = 500
RSI_OVERSOLD = 35
RSI_SIGNAL = 45
RSI_LOOKBACK = 5
ADX_MIN = 20
MIN_BELOW_HIGH_PCT = 25.0
MAX_BELOW_HIGH_PCT = 50.0
MAX_FROM_SMA_PCT = 12.0
SMA_SLOPE_DAYS = 20
VOLUME_AVG_DAYS = 50
MAX_PE = 60
MIN_FUNDAMENTAL_CHECKS = 1
MIN_GAP_DAYS = 30
MAX_POSITION_PCT = 15.0

# =============================================================================
# TICKERS
# =============================================================================
TICKERS = [
    'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEP',
    'AFL', 'AIG', 'AMAT', 'AMD', 'AMGN', 'AMP', 'AMT', 'AMZN', 'ANET', 'AON',
    'APD', 'APH', 'AVGO', 'AXP', 'AZO', 'BA', 'BAC', 'BDX', 'BIIB', 'BK',
    'BKNG', 'BLK', 'BMY', 'BSX', 'C', 'CAT', 'CB', 'CCI', 'CDNS', 'CEG',
    'CHTR', 'CI', 'CL', 'CMCSA', 'CME', 'CMG', 'CNC', 'COF', 'COP', 'COST',
    'CRM', 'CSCO', 'CSX', 'CTAS', 'CVS', 'CVX', 'D', 'DD', 'DE', 'DHR',
    'DIS', 'DLR', 'DOV', 'DOW', 'DUK', 'ECL', 'EL', 'ELV', 'EMR', 'EOG',
    'EQIX', 'ETN', 'EW', 'EXC', 'F', 'FANG', 'FCX', 'FDX', 'FI', 'FICO',
    'GD', 'GE', 'GEHC', 'GILD', 'GIS', 'GLW', 'GM', 'GOOG', 'GOOGL', 'GPN',
    'GS', 'GWW', 'HAL', 'HCA', 'HD', 'HLT', 'HON', 'HPQ', 'HUM', 'IBM',
    'ICE', 'IDXX', 'INTC', 'INTU', 'ISRG', 'ITW', 'JCI', 'JNJ', 'JPM', 'KDP',
    'KEY', 'KLAC', 'KMB', 'KO', 'KR', 'LEN', 'LHX', 'LIN', 'LLY', 'LMT',
    'LOW', 'LRCX', 'LULU', 'LUV', 'MA', 'MAR', 'MCD', 'MCHP', 'MCK', 'MCO',
    'MDLZ', 'MDT', 'MET', 'META', 'MMC', 'MMM', 'MNST', 'MO', 'MPC', 'MRK',
    'MRNA', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MU', 'NDAQ', 'NEE', 'NFLX',
    'NKE', 'NOC', 'NOW', 'NSC', 'NTRS', 'NUE', 'NVDA', 'NVR', 'ORCL', 'ORLY',
    'OXY', 'PANW', 'PAYX', 'PCAR', 'PEP', 'PFE', 'PG', 'PGR', 'PH', 'PLD',
    'PM', 'PNC', 'PPG', 'PRU', 'PSA', 'PSX', 'PYPL', 'QCOM', 'REGN', 'RJF',
    'RMD', 'ROK', 'ROP', 'ROST', 'RSG', 'RTX', 'SBAC', 'SBUX', 'SCHW', 'SHW',
    'SLB', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STZ', 'SYK', 'SYY',
    'T', 'TDG', 'TEL', 'TFC', 'TGT', 'TJX', 'TMO', 'TMUS', 'TROW', 'TRV',
    'TSLA', 'TT', 'TXN', 'TYL', 'UNH', 'UNP', 'UPS', 'URI', 'USB', 'V',
    'VLO', 'VMC', 'VRSN', 'VRTX', 'VZ', 'WAB', 'WBA', 'WBD', 'WELL', 'WFC',
    'WM', 'WMB', 'WMT', 'WRB', 'XEL', 'XOM', 'XYL', 'YUM', 'ZBH', 'ZTS',
    # Growth
    'ABNB', 'AFRM', 'AI', 'BILL', 'COIN', 'CRWD', 'DDOG', 'DOCU', 'FTNT',
    'HUBS', 'MDB', 'NET', 'OKTA', 'PLTR', 'RBLX', 'ROKU', 'SHOP', 'SNAP',
    'SNOW', 'SOFI', 'SPOT', 'SQ', 'TTD', 'TWLO', 'U', 'UBER', 'UPST', 'ZM', 'ZS',
    # Biotech
    'ALNY', 'ARGX', 'BNTX', 'CRSP', 'DXCM', 'EXAS', 'INCY', 'IONS', 'JAZZ',
    'MDGL', 'NBIX', 'REGN', 'SRPT', 'UTHR', 'VRTX',
    # Semis
    'ASML', 'ENPH', 'FSLR', 'LSCC', 'MRVL', 'MPWR', 'NXPI', 'ON', 'SEDG', 'SMCI',
    # Energy
    'APA', 'AR', 'BKR', 'CHK', 'CHRD', 'CTRA', 'DVN', 'EQT', 'HAL', 'HES',
    'KMI', 'MRO', 'OKE', 'OVV', 'SLB', 'TRGP', 'VLO', 'WMB', 'XOM',
    # Financials
    'ACGL', 'AFL', 'AIG', 'ALL', 'ALLY', 'AON', 'AXP', 'BAC', 'BK', 'BLK',
    'BRO', 'BX', 'C', 'CB', 'CFG', 'CINF', 'COF', 'DFS', 'GS', 'HBAN',
    'JPM', 'KKR', 'MET', 'MMC', 'MS', 'PFG', 'PGR', 'PNC', 'SCHW', 'TFC',
    'TROW', 'TRV', 'USB', 'WFC',
    # Industrials
    'AXON', 'BLDR', 'CAT', 'CMI', 'DE', 'EMR', 'ETN', 'FAST', 'FDX', 'GE',
    'GWW', 'HON', 'ITW', 'JCI', 'LMT', 'NOC', 'ODFL', 'PCAR', 'RTX', 'UNP',
    'UPS', 'URI', 'WAB', 'WM',
    # Consumer
    'AMZN', 'BKNG', 'COST', 'CVNA', 'DKS', 'DPZ', 'ETSY', 'HD', 'KMX', 'LEN',
    'LOW', 'LULU', 'MAR', 'MCD', 'NCLH', 'NKE', 'ORLY', 'RCL', 'RH', 'ROST',
    'SBUX', 'TGT', 'TJX', 'TSLA', 'ULTA', 'WMT', 'WYNN', 'YUM',
    # Materials
    'AA', 'ALB', 'CF', 'CLF', 'FCX', 'GOLD', 'LIN', 'MLM', 'NEM', 'NUE',
    'SCCO', 'SHW', 'STLD', 'VMC',
]
TICKERS = sorted(list(set(TICKERS)))
print(f"Total tickers: {len(TICKERS)}")

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
# DATA
# =============================================================================
print("\nDownloading VIX data...")
vix = yf.download('^VIX', start=START_DATE, end=END_DATE, progress=False)
if isinstance(vix.columns, pd.MultiIndex):
    vix.columns = [col[0] for col in vix.columns]
vix_lookup = {date.strftime('%Y-%m-%d'): float(row['Close']) for date, row in vix.iterrows()}
print(f"VIX data: {len(vix_lookup)} days")

print("Downloading SPY data...")
spy_df = yf.download('SPY', start=START_DATE, end=END_DATE, progress=False)
if isinstance(spy_df.columns, pd.MultiIndex):
    spy_df.columns = [col[0] for col in spy_df.columns]
spy_df['year'] = spy_df.index.year
spy_annual = {}
for year in spy_df['year'].unique():
    yd = spy_df[spy_df['year'] == year]['Close']
    if len(yd) > 1:
        spy_annual[year] = (yd.iloc[-1] - yd.iloc[0]) / yd.iloc[0] * 100

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
            return {'return_pct': (close[-1] - entry_price) / entry_price * 100,
                    'exit_day': day, 'exit_reason': 'data_end', 'trailing_activated': trailing_active}

        day_high, day_low = high[idx], low[idx]
        if day_high > highest_high:
            highest_high = day_high

        if USE_TRAILING and not trailing_active and day_high >= activation_price:
            trailing_active = True
        if trailing_active:
            trailing_stop = max(trailing_stop, highest_high * (1 - TRAIL_DISTANCE_PCT / 100))

        current_stop = trailing_stop if trailing_active else stop_price

        if day_low <= current_stop:
            return {'return_pct': (current_stop - entry_price) / entry_price * 100,
                    'exit_day': day, 'exit_reason': 'trail_stop' if trailing_active else 'stop',
                    'trailing_activated': trailing_active}
        if day_high >= tp_price:
            return {'return_pct': TAKE_PROFIT_PCT, 'exit_day': day, 'exit_reason': 'target',
                    'trailing_activated': trailing_active}

    return {'return_pct': (close[entry_idx + MAX_HOLD_DAYS] - entry_price) / entry_price * 100,
            'exit_day': MAX_HOLD_DAYS, 'exit_reason': 'max_days', 'trailing_activated': trailing_active}

# =============================================================================
# SCANNER
# =============================================================================
def scan_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if (info.get('marketCap', 0) or 0) < MIN_MARKET_CAP:
            return [], 'low_cap'

        # Fundamentals check
        checks = []
        pe = info.get('trailingPE') or info.get('forwardPE')
        if pe: checks.append(0 < pe < MAX_PE)
        if len(checks) > 0 and sum(checks) < MIN_FUNDAMENTAL_CHECKS:
            return [], 'bad_fund'

        df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
        if df is None or len(df) < MIN_BARS:
            return [], 'no_data'
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        close, high, low, volume = df['Close'].values, df['High'].values, df['Low'].values, df['Volume'].values
        dates = df.index

        close_s, high_s, low_s, vol_s = pd.Series(close), pd.Series(high), pd.Series(low), pd.Series(volume)
        rsi = calc_rsi(close_s, 14).values
        adx, plus_di, minus_di = calc_adx(high_s, low_s, close_s, 14)
        adx = adx.values
        sma_200 = close_s.rolling(200).mean().values
        sma_slope = ((pd.Series(sma_200) - pd.Series(sma_200).shift(SMA_SLOPE_DAYS)) / pd.Series(sma_200).shift(SMA_SLOPE_DAYS) * 100).values
        high_52w = high_s.rolling(252).max().values
        vol_avg = vol_s.rolling(VOLUME_AVG_DAYS).mean().values

        signals = []
        last_idx = -999

        for i in range(260, len(df) - MAX_HOLD_DAYS - 5):
            if i - last_idx < MIN_GAP_DAYS:
                continue

            date_str = dates[i].strftime('%Y-%m-%d')
            vix_val = vix_lookup.get(date_str, 20)

            if USE_VIX_FILTER and not (VIX_MIN <= vix_val <= VIX_MAX):
                continue

            price = close[i]
            if np.isnan(sma_200[i]) or np.isnan(high_52w[i]) or np.isnan(adx[i]):
                continue

            pct_below = (high_52w[i] - price) / high_52w[i] * 100
            if not (MIN_BELOW_HIGH_PCT <= pct_below <= MAX_BELOW_HIGH_PCT):
                continue

            pct_sma = abs(price - sma_200[i]) / sma_200[i] * 100
            if pct_sma > MAX_FROM_SMA_PCT or price < sma_200[i] * 0.97:
                continue

            if not np.isnan(sma_slope[i]) and sma_slope[i] < 0:
                continue

            rsi_sig = any(i-j-1 >= 0 and (rsi[i-j-1] <= RSI_SIGNAL and rsi[i-j] > RSI_SIGNAL or rsi[i-j-1] <= RSI_OVERSOLD)
                        for j in range(1, RSI_LOOKBACK + 1))
            if not rsi_sig or adx[i] < ADX_MIN:
                continue

            if USE_VOLUME_FILTER:
                if np.isnan(vol_avg[i]) or vol_avg[i] == 0 or volume[i] / vol_avg[i] < VOLUME_SURGE_MULT:
                    continue

            trade = execute_trade(close, high, low, i, price)
            risk_dollars = ACCOUNT_SIZE * (RISK_PER_TRADE_PCT / 100)
            position = min(risk_dollars / (STOP_LOSS_PCT / 100), ACCOUNT_SIZE * MAX_POSITION_PCT / 100)

            signals.append({
                'ticker': ticker, 'date': date_str, 'entry': round(price, 2),
                'vix': round(vix_val, 1), 'sector': info.get('sector', 'Unknown'),
                'return_pct': round(trade['return_pct'], 2), 'exit_day': trade['exit_day'],
                'exit_reason': trade['exit_reason'], 'trailing_activated': trade['trailing_activated'],
                'position': round(position, 0), 'pnl': round(position * trade['return_pct'] / 100, 0)
            })
            last_idx = i

        return signals, 'success'
    except:
        return [], 'error'

# =============================================================================
# RUN SCAN
# =============================================================================
print(f"\n{'='*70}")
print(f"MARKET SNIPER SCREENER")
print(f"VIX Filter: {'ON' if USE_VIX_FILTER else 'OFF'}")
print(f"{'='*70}")

all_signals = []
stats = {'success': 0, 'no_data': 0, 'error': 0, 'low_cap': 0, 'bad_fund': 0}
start_time = time.time()

for i, ticker in enumerate(TICKERS):
    if (i + 1) % 50 == 0:
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed * 60 if elapsed > 0 else 0
        print(f"  [{i+1:4d}/{len(TICKERS)}] Signals: {len(all_signals):4d} | {rate:.0f}/min")

    signals, status = scan_stock(ticker)
    stats[status] = stats.get(status, 0) + 1
    all_signals.extend(signals)

    if (i + 1) % 100 == 0:
        time.sleep(1)

print(f"\nCompleted in {(time.time()-start_time)/60:.1f} min | Signals: {len(all_signals)}")

# =============================================================================
# RESULTS
# =============================================================================
if all_signals:
    df = pd.DataFrame(all_signals)
    ret = df['return_pct']
    wins = ret > 0

    print(f"\n{'='*70}")
    print("PERFORMANCE")
    print(f"{'='*70}")
    print(f"Trades: {len(ret)} | Win Rate: {wins.mean()*100:.1f}% | Avg Return: {ret.mean():+.2f}%")
    print(f"Avg Win: +{ret[wins].mean():.1f}% | Avg Loss: {ret[~wins].mean():.1f}%")
    print(f"Total P&L: ${df['pnl'].sum():+,.0f} | Avg Hold: {df['exit_day'].mean():.0f} days")

    # Exit breakdown
    print(f"\n{'='*70}")
    print("EXIT BREAKDOWN")
    print(f"{'='*70}")
    for reason in ['stop', 'trail_stop', 'target', 'max_days']:
        sub = df[df['exit_reason'] == reason]
        if len(sub) > 0:
            print(f"  {reason:12s}: {len(sub):4d} ({len(sub)/len(df)*100:5.1f}%) | {sub['return_pct'].mean():+.1f}%")

    # By year
    print(f"\n{'='*70}")
    print("BY YEAR VS SPY")
    print(f"{'='*70}")
    df['year'] = pd.to_datetime(df['date']).dt.year
    print(f"{'Year':<6} {'Trades':<7} {'WinRate':<8} {'PnL':<12} {'SPY':<8}")
    for year in sorted(df['year'].unique()):
        yd = df[df['year'] == year]
        wr = (yd['return_pct'] > 0).mean() * 100
        pnl = yd['pnl'].sum()
        spy = spy_annual.get(year, 0)
        print(f"{year:<6} {len(yd):<7} {wr:<8.1f} ${pnl:<+11,.0f} {spy:<+.1f}%")

    print(f"\nTOTAL: ${df['pnl'].sum():+,.0f}")
    spy_total = sum(100000 * spy_annual.get(y, 0) / 100 for y in df['year'].unique())
    print(f"SPY B&H same period: ${spy_total:+,.0f}")

    # Overlap analysis
    print(f"\n{'='*70}")
    print("TRADE OVERLAP ANALYSIS")
    print(f"{'='*70}")
    df['entry_date'] = pd.to_datetime(df['date'])
    df['exit_date'] = df['entry_date'] + pd.to_timedelta(df['exit_day'], unit='D')
    df = df.sort_values('entry_date').reset_index(drop=True)

    max_concurrent = 0
    for _, row in df.iterrows():
        active = df[(df['entry_date'] <= row['entry_date']) & (df['exit_date'] > row['entry_date'])]
        max_concurrent = max(max_concurrent, len(active))

    print(f"Max concurrent positions: {max_concurrent}")
    print(f"Capital needed: ${max_concurrent * 6667:,.0f}")
    if max_concurrent <= 5:
        print("LOW OVERLAP - Can take all trades!")
    elif max_concurrent <= 10:
        print("MODERATE - May need to skip some")
    else:
        print("HIGH OVERLAP - Will skip many trades")

    # Save
    df.to_csv('screener_results.csv', index=False)
    print(f"\nSaved to screener_results.csv")
    try:
        from google.colab import files
        files.download('screener_results.csv')
    except:
        pass
else:
    print("No signals found.")
