# =============================================================================
# MARKET SNIPER SCREENER - SHOWCASE VERSION
# =============================================================================
# For embedding in app - combines technical reversal + fundamental quality
# Produces fewer, higher-conviction signals to display to users
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
# CONFIGURATION
# =============================================================================
STOP_LOSS_PCT = 15.0
TAKE_PROFIT_PCT = 50.0
USE_TRAILING = True
TRAIL_ACTIVATION_PCT = 15.0
TRAIL_DISTANCE_PCT = 10.0
MAX_HOLD_DAYS = 120

# VIX FILTER - Market fear timing
USE_VIX_FILTER = True
VIX_MIN = 20
VIX_MAX = 50

# VOLUME
USE_VOLUME_FILTER = True
VOLUME_SURGE_MULT = 1.2

ACCOUNT_SIZE = 100000
RISK_PER_TRADE_PCT = 1.0

START_DATE = '2018-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')

# TECHNICAL PARAMETERS
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

# =============================================================================
# FUNDAMENTAL FILTERS (NEW - from original idea)
# =============================================================================
USE_FUNDAMENTAL_FILTER = True

# P/E Ratio: Below industry median, or < 25 for growth
MAX_PE_RATIO = 30              # Forward or trailing P/E below this
PE_PREFER_BELOW = 20           # Prefer below this for showcase

# PEG Ratio: Balance P/E with growth
MAX_PEG_RATIO = 2.0            # PEG < 1 is ideal, < 2 acceptable

# Price-to-Book: Asset value check
MAX_PRICE_TO_BOOK = 5.0        # Below 2 is ideal for value

# Return on Equity: Quality filter
MIN_ROE = 8.0                  # ROE >= 10% is ideal

# Debt-to-Equity: Risk filter
MAX_DEBT_EQUITY = 2.0          # Below 1 is low debt, below 2 acceptable

# Free Cash Flow: Must be positive
REQUIRE_POSITIVE_FCF = True

# =============================================================================
# TICKERS
# =============================================================================
TICKERS = [
    # S&P 500
    'A', 'AAL', 'AAP', 'AAPL', 'ABBV', 'ABC', 'ABMD', 'ABT', 'ACGL', 'ACN',
    'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEE', 'AEP', 'AES', 'AFL', 'AIG',
    'AIZ', 'AJG', 'AKAM', 'ALB', 'ALGN', 'ALK', 'ALL', 'ALLE', 'AMAT', 'AMCR',
    'AMD', 'AME', 'AMGN', 'AMP', 'AMT', 'AMZN', 'ANET', 'ANSS', 'AON', 'AOS',
    'APA', 'APD', 'APH', 'APTV', 'ARE', 'ATO', 'AVB', 'AVGO', 'AVY', 'AWK',
    'AXP', 'AZO', 'BA', 'BAC', 'BALL', 'BAX', 'BBWI', 'BBY', 'BDX', 'BEN',
    'BG', 'BIIB', 'BIO', 'BK', 'BKNG', 'BKR', 'BLK', 'BMY', 'BR', 'BRK-B',
    'BRO', 'BSX', 'BWA', 'BXP', 'C', 'CAG', 'CAH', 'CARR', 'CAT', 'CB',
    'CBOE', 'CBRE', 'CCI', 'CCL', 'CDAY', 'CDNS', 'CDW', 'CE', 'CEG', 'CF',
    'CFG', 'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLX', 'CMA', 'CMCSA',
    'CME', 'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COO', 'COP', 'COST',
    'CPB', 'CPRT', 'CPT', 'CRL', 'CRM', 'CSCO', 'CSGP', 'CSX', 'CTAS', 'CTLT',
    'CTRA', 'CTSH', 'CTVA', 'CVS', 'CVX', 'CZR', 'D', 'DAL', 'DD', 'DE',
    'DFS', 'DG', 'DGX', 'DHI', 'DHR', 'DIS', 'DLR', 'DLTR', 'DOV', 'DOW',
    'DPZ', 'DRI', 'DTE', 'DUK', 'DVA', 'DVN', 'DXC', 'DXCM', 'EA', 'EBAY',
    'ECL', 'ED', 'EFX', 'EIX', 'EL', 'ELV', 'EMN', 'EMR', 'ENPH', 'EOG',
    'EPAM', 'EQIX', 'EQR', 'EQT', 'ES', 'ESS', 'ETN', 'ETR', 'ETSY', 'EVRG',
    'EW', 'EXC', 'EXPD', 'EXPE', 'EXR', 'F', 'FANG', 'FAST', 'FBHS', 'FCX',
    'FDS', 'FDX', 'FE', 'FFIV', 'FI', 'FICO', 'FIS', 'FISV', 'FITB', 'FLT',
    'FMC', 'FOX', 'FOXA', 'FRT', 'FSLR', 'FTNT', 'FTV', 'GD', 'GE', 'GEHC',
    'GEN', 'GILD', 'GIS', 'GL', 'GLW', 'GM', 'GNRC', 'GOOG', 'GOOGL', 'GPC',
    'GPN', 'GRMN', 'GS', 'GWW', 'HAL', 'HAS', 'HBAN', 'HCA', 'HD', 'HES',
    'HIG', 'HII', 'HLT', 'HOLX', 'HON', 'HPE', 'HPQ', 'HRL', 'HSIC', 'HST',
    'HSY', 'HUBB', 'HUM', 'HWM', 'IBM', 'ICE', 'IDXX', 'IEX', 'IFF', 'ILMN',
    'INCY', 'INTC', 'INTU', 'INVH', 'IP', 'IPG', 'IQV', 'IR', 'IRM', 'ISRG',
    'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JCI', 'JKHY', 'JNJ', 'JNPR', 'JPM',
    'K', 'KDP', 'KEY', 'KEYS', 'KHC', 'KIM', 'KLAC', 'KMB', 'KMI', 'KMX',
    'KO', 'KR', 'KVUE', 'L', 'LDOS', 'LEN', 'LH', 'LHX', 'LIN', 'LKQ', 'LLY',
    'LMT', 'LNC', 'LNT', 'LOW', 'LRCX', 'LULU', 'LUV', 'LVS', 'LW', 'LYB',
    'LYV', 'MA', 'MAA', 'MAR', 'MAS', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ',
    'MDT', 'MET', 'META', 'MGM', 'MHK', 'MKC', 'MKTX', 'MLM', 'MMC', 'MMM',
    'MNST', 'MO', 'MOH', 'MOS', 'MPC', 'MPWR', 'MRK', 'MRNA', 'MRO', 'MS',
    'MSCI', 'MSFT', 'MSI', 'MTB', 'MTCH', 'MTD', 'MU', 'NCLH', 'NDAQ', 'NDSN',
    'NEE', 'NEM', 'NFLX', 'NI', 'NKE', 'NOC', 'NOW', 'NRG', 'NSC', 'NTAP',
    'NTRS', 'NUE', 'NVDA', 'NVR', 'NWL', 'NWS', 'NWSA', 'NXPI', 'O', 'ODFL',
    'OGN', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OTIS', 'OXY', 'PANW', 'PARA',
    'PAYC', 'PAYX', 'PCAR', 'PCG', 'PEAK', 'PEG', 'PEP', 'PFE', 'PFG', 'PG',
    'PGR', 'PH', 'PHM', 'PKG', 'PKI', 'PLD', 'PM', 'PNC', 'PNR', 'PNW',
    'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PVH', 'PWR', 'PXD',
    'PYPL', 'QCOM', 'QRVO', 'RCL', 'RE', 'REG', 'REGN', 'RF', 'RHI', 'RJF',
    'RL', 'RMD', 'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX', 'RVTY', 'SBAC',
    'SBUX', 'SCHW', 'SEDG', 'SEE', 'SHW', 'SJM', 'SLB', 'SNA', 'SNPS', 'SO',
    'SPG', 'SPGI', 'SRE', 'STE', 'STLD', 'STT', 'STX', 'STZ', 'SWK', 'SWKS',
    'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TDG', 'TDY', 'TECH', 'TEL', 'TER',
    'TFC', 'TFX', 'TGT', 'TJX', 'TMO', 'TMUS', 'TPR', 'TRGP', 'TRMB', 'TROW',
    'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTWO', 'TXN', 'TXT', 'TYL', 'UAL',
    'UDR', 'UHS', 'ULTA', 'UNH', 'UNP', 'UPS', 'URI', 'USB', 'V', 'VFC',
    'VICI', 'VLO', 'VMC', 'VNO', 'VRSK', 'VRSN', 'VRTX', 'VTR', 'VTRS', 'VZ',
    'WAB', 'WAT', 'WBA', 'WBD', 'WDC', 'WEC', 'WELL', 'WFC', 'WHR', 'WM',
    'WMB', 'WMT', 'WRB', 'WRK', 'WST', 'WTW', 'WY', 'WYNN', 'XEL', 'XOM',
    'XRAY', 'XYL', 'YUM', 'ZBH', 'ZBRA', 'ZION', 'ZTS',

    # S&P 400 MidCap (selected)
    'ACIW', 'ACM', 'AEO', 'AFG', 'AGCO', 'AIT', 'ALKS', 'ALLY', 'AMKR', 'AMN',
    'AN', 'ANF', 'AR', 'ARCB', 'ARW', 'ASB', 'ASH', 'ASGN', 'ATI', 'ATR',
    'AYI', 'BC', 'BCO', 'BDC', 'BERY', 'BHF', 'BJ', 'BLD', 'BOOT', 'BRKR',
    'BTU', 'BWXT', 'BYD', 'CAL', 'CALM', 'CASY', 'CBT', 'CC', 'CEIX', 'CHE',
    'CHDN', 'CHK', 'CHRD', 'CIEN', 'CLF', 'CLH', 'CMC', 'CNK', 'CNO', 'COHR',
    'COLM', 'CPE', 'CRC', 'CRK', 'CRUS', 'CUZ', 'CW', 'DAR', 'DCI', 'DDS',
    'DECK', 'DEI', 'DKS', 'DLB', 'DY', 'EAT', 'EGP', 'EHC', 'ELAN', 'ELF',
    'ELS', 'ENSG', 'EPR', 'EQH', 'ESNT', 'EVR', 'EXEL', 'EXLS', 'EXP', 'FAF',
    'FCFS', 'FHN', 'FIVE', 'FIX', 'FL', 'FLO', 'FLS', 'FND', 'FOXF', 'FR',

    # Growth / Tech (selected)
    'ABNB', 'CRWD', 'DDOG', 'FTNT', 'HUBS', 'MDB', 'NET', 'OKTA', 'PLTR',
    'SHOP', 'SNOW', 'SPOT', 'SQ', 'TTD', 'UBER', 'ZS',

    # Quality Large Caps
    'ASML', 'BABA', 'TSM', 'V', 'MA', 'UNH', 'JNJ', 'PG', 'HD', 'MRK',
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

def calc_macd(close, fast=12, slow=26, signal=9):
    """MACD indicator for trend confirmation"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

# =============================================================================
# FUNDAMENTAL ANALYSIS
# =============================================================================
def check_fundamentals(info):
    """
    Check if stock passes fundamental quality filters.
    Returns (pass: bool, score: int, details: dict)
    """
    if not USE_FUNDAMENTAL_FILTER:
        return True, 10, {}

    score = 0
    details = {}
    reasons = []

    # P/E Ratio
    pe = info.get('forwardPE') or info.get('trailingPE')
    if pe and pe > 0:
        details['pe'] = pe
        if pe <= PE_PREFER_BELOW:
            score += 3
            reasons.append(f"Low P/E ({pe:.1f})")
        elif pe <= MAX_PE_RATIO:
            score += 1
            reasons.append(f"OK P/E ({pe:.1f})")
        else:
            reasons.append(f"High P/E ({pe:.1f})")
    else:
        details['pe'] = None

    # PEG Ratio
    peg = info.get('pegRatio')
    if peg and peg > 0:
        details['peg'] = peg
        if peg < 1:
            score += 3
            reasons.append(f"Great PEG ({peg:.2f})")
        elif peg <= MAX_PEG_RATIO:
            score += 1
            reasons.append(f"OK PEG ({peg:.2f})")
        else:
            reasons.append(f"High PEG ({peg:.2f})")
    else:
        details['peg'] = None

    # Price-to-Book
    pb = info.get('priceToBook')
    if pb and pb > 0:
        details['pb'] = pb
        if pb < 2:
            score += 2
            reasons.append(f"Low P/B ({pb:.2f})")
        elif pb <= MAX_PRICE_TO_BOOK:
            score += 1
            reasons.append(f"OK P/B ({pb:.2f})")
        else:
            reasons.append(f"High P/B ({pb:.2f})")
    else:
        details['pb'] = None

    # Return on Equity
    roe = info.get('returnOnEquity')
    if roe:
        roe_pct = roe * 100
        details['roe'] = roe_pct
        if roe_pct >= 15:
            score += 3
            reasons.append(f"Strong ROE ({roe_pct:.1f}%)")
        elif roe_pct >= MIN_ROE:
            score += 1
            reasons.append(f"OK ROE ({roe_pct:.1f}%)")
        else:
            reasons.append(f"Weak ROE ({roe_pct:.1f}%)")
    else:
        details['roe'] = None

    # Debt-to-Equity
    de = info.get('debtToEquity')
    if de:
        de_ratio = de / 100 if de > 10 else de  # Handle percentage vs ratio
        details['de'] = de_ratio
        if de_ratio < 0.5:
            score += 2
            reasons.append(f"Low debt ({de_ratio:.2f})")
        elif de_ratio <= MAX_DEBT_EQUITY:
            score += 1
            reasons.append(f"OK debt ({de_ratio:.2f})")
        else:
            reasons.append(f"High debt ({de_ratio:.2f})")
    else:
        details['de'] = None

    # Free Cash Flow
    fcf = info.get('freeCashflow')
    if fcf:
        details['fcf'] = fcf
        if fcf > 0:
            score += 2
            if fcf > 1e9:
                reasons.append(f"Strong FCF (${fcf/1e9:.1f}B)")
            else:
                reasons.append(f"Positive FCF (${fcf/1e6:.0f}M)")
        elif REQUIRE_POSITIVE_FCF:
            score -= 2
            reasons.append(f"Negative FCF")
    else:
        details['fcf'] = None

    # Earnings growth
    eg = info.get('earningsGrowth')
    if eg and eg > 0:
        details['earnings_growth'] = eg * 100
        if eg > 0.20:
            score += 2
            reasons.append(f"Strong growth ({eg*100:.0f}%)")
        elif eg > 0:
            score += 1
            reasons.append(f"Growing ({eg*100:.0f}%)")
    else:
        details['earnings_growth'] = None

    # Pass if score >= 5 (out of max ~18)
    passed = score >= 5
    details['score'] = score
    details['reasons'] = reasons

    return passed, score, details

# =============================================================================
# DATA
# =============================================================================
print("\nDownloading VIX data...")
vix = yf.download('^VIX', start=START_DATE, end=END_DATE, progress=False)
if isinstance(vix.columns, pd.MultiIndex):
    vix.columns = [col[0] for col in vix.columns]
vix_lookup = {date.strftime('%Y-%m-%d'): float(row['Close']) for date, row in vix.iterrows()}
print(f"VIX data: {len(vix_lookup)} days")
high_fear = sum(1 for v in vix_lookup.values() if VIX_MIN <= v <= VIX_MAX)
print(f"Fear days (VIX {VIX_MIN}-{VIX_MAX}): {high_fear} ({high_fear/len(vix_lookup)*100:.1f}%)")

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

        # Market cap filter
        if (info.get('marketCap', 0) or 0) < MIN_MARKET_CAP:
            return [], 'low_cap', None

        # Fundamental quality check (NEW)
        passed_fundamentals, fund_score, fund_details = check_fundamentals(info)
        if not passed_fundamentals:
            return [], 'failed_fundamentals', fund_details

        df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
        if df is None or len(df) < MIN_BARS:
            return [], 'no_data', None
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

        # MACD (NEW)
        macd_line, signal_line, histogram = calc_macd(close_s)
        macd_line, signal_line, histogram = macd_line.values, signal_line.values, histogram.values

        signals = []
        last_idx = -999

        for i in range(260, len(df) - MAX_HOLD_DAYS - 5):
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

            # MACD confirmation (NEW) - histogram turning positive or crossover
            macd_bullish = (histogram[i] > 0) or (i > 0 and histogram[i-1] < 0 and histogram[i] > histogram[i-1])
            # Allow signal even without MACD confirmation, but track it
            macd_confirmed = macd_bullish

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
                'position': round(position, 0), 'pnl': round(position * trade['return_pct'] / 100, 0),
                # Fundamental data for display
                'fund_score': fund_score,
                'pe': fund_details.get('pe'),
                'peg': fund_details.get('peg'),
                'roe': fund_details.get('roe'),
                'de': fund_details.get('de'),
                'macd_confirmed': macd_confirmed,
            })
            last_idx = i

        return signals, 'success', fund_details
    except Exception as e:
        return [], 'error', None

# =============================================================================
# RUN
# =============================================================================
print(f"\n{'='*70}")
print(f"MARKET SNIPER - SHOWCASE VERSION")
print(f"Technical + Fundamental Quality Filters")
print(f"VIX: {VIX_MIN}-{VIX_MAX} | Below High: {MIN_BELOW_HIGH_PCT}-{MAX_BELOW_HIGH_PCT}%")
print(f"{'='*70}")

all_signals = []
stats = {'success': 0, 'no_data': 0, 'error': 0, 'low_cap': 0, 'failed_fundamentals': 0}
start_time = time.time()

for i, ticker in enumerate(TICKERS):
    if (i + 1) % 100 == 0:
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed * 60 if elapsed > 0 else 0
        eta = (len(TICKERS) - i - 1) / rate if rate > 0 else 0
        print(f"  [{i+1:4d}/{len(TICKERS)}] Signals: {len(all_signals):4d} | {rate:.0f}/min | ETA: {eta:.0f}min")

    signals, status, _ = scan_stock(ticker)
    stats[status] = stats.get(status, 0) + 1
    all_signals.extend(signals)

    if (i + 1) % 150 == 0:
        time.sleep(2)

print(f"\nDone in {(time.time()-start_time)/60:.1f} min | Signals: {len(all_signals)}")
print(f"Stats: {stats}")
years = len(set(pd.to_datetime([s['date'] for s in all_signals]).year)) if all_signals else 1
print(f"Signals per year: {len(all_signals)/years:.0f}")

# =============================================================================
# RESULTS
# =============================================================================
if all_signals:
    df = pd.DataFrame(all_signals)
    ret = df['return_pct']
    wins = ret > 0

    print(f"\n{'='*70}")
    print("PERFORMANCE (SHOWCASE)")
    print(f"{'='*70}")
    print(f"Trades: {len(ret)} | Win Rate: {wins.mean()*100:.1f}%")
    print(f"Avg Return: {ret.mean():+.2f}% | Avg Win: +{ret[wins].mean():.1f}% | Avg Loss: {ret[~wins].mean():.1f}%")
    print(f"Total P&L: ${df['pnl'].sum():+,.0f}")

    if (~wins).any() and ret[~wins].sum() != 0:
        pf = ret[wins].sum() / abs(ret[~wins].sum())
        print(f"Profit Factor: {pf:.2f}")

    # Fundamental score analysis
    print(f"\n{'='*70}")
    print("FUNDAMENTAL QUALITY BREAKDOWN")
    print(f"{'='*70}")
    print(f"Avg Fundamental Score: {df['fund_score'].mean():.1f}")
    high_quality = df[df['fund_score'] >= 8]
    if len(high_quality) > 0:
        hq_wins = high_quality['return_pct'] > 0
        print(f"High Quality (score>=8): {len(high_quality)} trades, {hq_wins.mean()*100:.1f}% WR, ${high_quality['pnl'].sum():+,.0f} P&L")

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
    print("BY YEAR")
    print(f"{'='*70}")
    df['year'] = pd.to_datetime(df['date']).dt.year
    print(f"{'Year':<6} {'Trades':<7} {'WinRate':<8} {'AvgRet':<9} {'PnL':<12} {'SPY':<8}")
    print("-"*60)
    for year in sorted(df['year'].unique()):
        yd = df[df['year'] == year]
        wr = (yd['return_pct'] > 0).mean() * 100
        avg = yd['return_pct'].mean()
        pnl = yd['pnl'].sum()
        spy = spy_annual.get(year, 0)
        print(f"{year:<6} {len(yd):<7} {wr:<8.1f} {avg:<+9.2f} ${pnl:<+11,.0f} {spy:<+.1f}%")

    print(f"\nTOTAL P&L: ${df['pnl'].sum():+,.0f}")

    # By Sector
    print(f"\n{'='*70}")
    print("BY SECTOR")
    print(f"{'='*70}")
    sector_stats = df.groupby('sector').agg({
        'return_pct': ['count', 'mean', lambda x: (x > 0).mean() * 100],
        'pnl': 'sum',
        'fund_score': 'mean'
    }).round(2)
    sector_stats.columns = ['Trades', 'AvgRet', 'WinRate', 'PnL', 'FundScore']
    sector_stats = sector_stats.sort_values('PnL', ascending=False)
    print(sector_stats.to_string())

    # Sample showcase picks (for app display)
    print(f"\n{'='*70}")
    print("SAMPLE SHOWCASE PICKS (Recent High-Quality)")
    print(f"{'='*70}")
    showcase = df.sort_values(['fund_score', 'date'], ascending=[False, False]).head(10)
    for _, row in showcase.iterrows():
        pe_str = f"P/E:{row['pe']:.1f}" if pd.notna(row['pe']) else "P/E:N/A"
        roe_str = f"ROE:{row['roe']:.0f}%" if pd.notna(row['roe']) else "ROE:N/A"
        print(f"  {row['ticker']:5s} | {row['date']} | Entry: ${row['entry']:.2f} | {row['return_pct']:+.1f}% | {pe_str} | {roe_str} | Score: {row['fund_score']}")

    # Save
    df.to_csv('showcase_results.csv', index=False)
    print(f"\nSaved to showcase_results.csv")
    try:
        from google.colab import files
        files.download('showcase_results.csv')
    except:
        pass
else:
    print("No signals found.")
