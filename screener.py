# =============================================================================
# MARKET SNIPER SCREENER v2.0
# =============================================================================
# Improved stock screener with:
# - Fixed technical indicator calculations
# - Volume confirmation
# - Trend confirmation (SMA slope + price structure)
# - Relative strength vs SPY
# - Flexible VIX handling
# - Better data validation
#
# For Google Colab: Run the cell below first to install dependencies
# =============================================================================

# Uncomment for Google Colab:
# !pip install yfinance pandas numpy -q

import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class Config:
    """Screener configuration - adjust these parameters"""

    # Data settings
    MIN_MARKET_CAP: float = 1e9          # $1B minimum
    MIN_BARS: int = 500                   # Minimum historical bars needed
    START_DATE: str = '2018-01-01'
    END_DATE: str = datetime.now().strftime('%Y-%m-%d')

    # VIX filter - set USE_VIX_FILTER=False to disable
    USE_VIX_FILTER: bool = True
    VIX_MIN: float = 18                   # Lowered from 25 for more signals
    VIX_MAX: float = 40                   # Avoid extreme panic (usually too late)

    # Stop loss / Take profit
    STOP_LOSS_PCT: float = 12.0           # Tighter stop (was 15%)
    TAKE_PROFIT_PCT: float = 36.0         # 3:1 reward/risk target

    # Trailing stop
    USE_TRAILING: bool = True
    TRAIL_ACTIVATION_PCT: float = 12.0    # Start trailing at 1R (matches stop)
    TRAIL_DISTANCE_PCT: float = 8.0       # Tighter trail to lock profits

    # Time exit
    MAX_HOLD_DAYS: int = 90               # Reduced from 120

    # Position sizing
    ACCOUNT_SIZE: float = 100000
    RISK_PER_TRADE_PCT: float = 1.0
    MAX_POSITION_PCT: float = 15.0        # Max 15% in single position

    # Technical parameters
    RSI_OVERSOLD: int = 35                # RSI oversold level
    RSI_SIGNAL: int = 45                  # RSI signal level (cross above)
    RSI_LOOKBACK: int = 5                 # Days to look for RSI cross
    ADX_MIN: int = 20                     # Minimum ADX for trend (lowered from 25)
    MIN_BELOW_HIGH_PCT: float = 25.0      # Min % below 52w high (was 35)
    MAX_BELOW_HIGH_PCT: float = 50.0      # Max % below (avoid falling knives)
    MAX_FROM_SMA_PCT: float = 12.0        # Max distance from SMA200
    SMA_SLOPE_DAYS: int = 20              # Days to measure SMA slope

    # Volume confirmation
    USE_VOLUME_FILTER: bool = True
    VOLUME_SURGE_MULT: float = 1.3        # Volume must be 1.3x average
    VOLUME_AVG_DAYS: int = 50             # Average volume lookback

    # Relative strength
    USE_RS_FILTER: bool = True
    RS_LOOKBACK: int = 63                 # ~3 months for RS calculation
    RS_MIN_PERCENTILE: float = 40         # Must be above 40th percentile

    # Fundamental filters
    MAX_PE: float = 60                    # Increased to allow growth stocks
    MAX_PEG: float = 3.0
    MAX_DEBT_EQUITY: float = 3.0
    MIN_PROFIT_MARGIN: float = -0.3       # Allow some unprofitable growth
    MIN_FUNDAMENTAL_CHECKS: int = 1       # Minimum checks to pass (was 2)

    # Signal spacing
    MIN_GAP_DAYS: int = 30                # Minimum days between signals


# Default configuration
CONFIG = Config()


# =============================================================================
# TICKER UNIVERSE
# =============================================================================

TICKERS = [
    # S&P 500 Core
    'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEP',
    'AFL', 'AIG', 'AMAT', 'AMD', 'AMGN', 'AMP', 'AMT', 'AMZN', 'ANET', 'AON',
    'APD', 'APH', 'AVGO', 'AXP', 'AZO', 'BA', 'BAC', 'BDX', 'BIIB', 'BK',
    'BKNG', 'BLK', 'BMY', 'BSX', 'C', 'CAT', 'CB', 'CCI', 'CDNS', 'CEG',
    'CHTR', 'CI', 'CL', 'CMCSA', 'CME', 'CMG', 'CNC', 'COF', 'COP', 'COST',
    'CRM', 'CSCO', 'CSX', 'CTAS', 'CVS', 'CVX', 'D', 'DD', 'DE', 'DHR',
    'DIS', 'DLR', 'DOV', 'DOW', 'DUK', 'ECL', 'EL', 'ELV', 'EMR', 'EOG',
    'EQIX', 'ETN', 'EW', 'EXC', 'F', 'FANG', 'FCX', 'FDX', 'FI', 'FICO',
    'FIS', 'FISV', 'GD', 'GE', 'GEHC', 'GILD', 'GIS', 'GLW', 'GM', 'GOOG',
    'GOOGL', 'GPN', 'GS', 'GWW', 'HAL', 'HCA', 'HD', 'HLT', 'HON', 'HPQ',
    'HUM', 'IBM', 'ICE', 'IDXX', 'INTC', 'INTU', 'ISRG', 'ITW', 'JCI', 'JNJ',
    'JPM', 'KDP', 'KEY', 'KLAC', 'KMB', 'KO', 'KR', 'LEN', 'LHX', 'LIN',
    'LLY', 'LMT', 'LOW', 'LRCX', 'LULU', 'LUV', 'MA', 'MAR', 'MCD', 'MCHP',
    'MCK', 'MCO', 'MDLZ', 'MDT', 'MET', 'META', 'MMC', 'MMM', 'MNST', 'MO',
    'MPC', 'MRK', 'MRNA', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MU', 'NDAQ',
    'NEE', 'NFLX', 'NKE', 'NOC', 'NOW', 'NSC', 'NTRS', 'NUE', 'NVDA', 'NVR',
    'ORCL', 'ORLY', 'OXY', 'PANW', 'PAYX', 'PCAR', 'PEP', 'PFE', 'PG', 'PGR',
    'PH', 'PLD', 'PM', 'PNC', 'PPG', 'PRU', 'PSA', 'PSX', 'PYPL', 'QCOM',
    'REGN', 'RJF', 'RMD', 'ROK', 'ROP', 'ROST', 'RSG', 'RTX', 'SBAC', 'SBUX',
    'SCHW', 'SHW', 'SLB', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STZ',
    'SYK', 'SYY', 'T', 'TDG', 'TEL', 'TFC', 'TGT', 'TJX', 'TMO', 'TMUS',
    'TROW', 'TRV', 'TSLA', 'TT', 'TXN', 'TYL', 'UNH', 'UNP', 'UPS', 'URI',
    'USB', 'V', 'VLO', 'VMC', 'VRSN', 'VRTX', 'VZ', 'WAB', 'WBA', 'WBD',
    'WELL', 'WFC', 'WM', 'WMB', 'WMT', 'WRB', 'XEL', 'XOM', 'XYL', 'YUM',
    'ZBH', 'ZTS',

    # High Growth / Tech
    'ABNB', 'AFRM', 'AI', 'BILL', 'COIN', 'CRWD', 'DDOG', 'DOCU', 'ESTC',
    'FTNT', 'GLOB', 'GTLB', 'HUBS', 'MDB', 'MNDY', 'NET', 'NTNX', 'OKTA',
    'PCTY', 'PLTR', 'RBLX', 'ROKU', 'SHOP', 'SNAP', 'SNOW', 'SOFI', 'SPOT',
    'SQ', 'TTD', 'TWLO', 'U', 'UBER', 'UPST', 'VEEV', 'WIX', 'ZI', 'ZM', 'ZS',

    # Biotech / Healthcare
    'ALNY', 'ARGX', 'BGNE', 'BNTX', 'CRSP', 'DXCM', 'EXAS', 'INCY', 'IONS',
    'JAZZ', 'LEGN', 'MDGL', 'NBIX', 'NTLA', 'RARE', 'RPRX', 'SRPT', 'UTHR',
    'VCEL', 'VKTX', 'XENE',

    # Semiconductors
    'ALGN', 'ASML', 'CRUS', 'ENPH', 'FSLR', 'LSCC', 'MRVL', 'MPWR', 'NXPI',
    'ON', 'QRVO', 'SEDG', 'SMCI', 'SWKS', 'TER', 'WOLF',

    # Energy
    'AM', 'APA', 'AR', 'BKR', 'CHK', 'CHRD', 'CNX', 'CTRA', 'DVN', 'EQT',
    'HAL', 'HES', 'KMI', 'MRO', 'MTDR', 'NOV', 'OKE', 'OVV', 'PXD', 'RRC',
    'SLB', 'SWN', 'TRGP', 'VLO', 'WMB', 'XOM',

    # Financials
    'ACGL', 'AFG', 'AJG', 'ALL', 'ALLY', 'AON', 'APO', 'ARES', 'AXS', 'BRO',
    'BX', 'CFG', 'CG', 'CINF', 'DFS', 'ERIE', 'EVR', 'FNB', 'HBAN', 'HIG',
    'IBKR', 'KKR', 'L', 'LPLA', 'MTG', 'NMIH', 'ORI', 'PFG', 'PIPR', 'RDN',
    'RGA', 'RNR', 'SEIC', 'SF', 'SLM', 'STT', 'TROW', 'UNM', 'VOYA', 'WRB',

    # Industrials
    'AGCO', 'AXON', 'BLDR', 'CAT', 'CMI', 'EME', 'FAST', 'GNRC', 'HEI', 'HWM',
    'IEX', 'IR', 'ITT', 'J', 'JBHT', 'JBL', 'KBR', 'LDOS', 'MAS', 'MLI',
    'MOD', 'ODFL', 'OSK', 'PCAR', 'PWR', 'RBC', 'SAIA', 'SNA', 'STRL', 'TDY',
    'TTC', 'UFPI', 'WAB', 'WCC', 'XPO',

    # Consumer
    'AEO', 'ANF', 'BURL', 'CAKE', 'CHWY', 'CPRI', 'CROX', 'CVNA', 'DASH',
    'DECK', 'DKS', 'DPZ', 'ETSY', 'FIVE', 'FND', 'GPS', 'HAS', 'KMX', 'LVS',
    'LYFT', 'MAT', 'NCLH', 'OLLI', 'PTON', 'RCL', 'RH', 'SHAK', 'SKX', 'TPR',
    'TRIP', 'UA', 'ULTA', 'URBN', 'W', 'WING', 'WSM', 'WYNN',

    # Materials / Mining
    'AA', 'ALB', 'BALL', 'CCJ', 'CF', 'CLF', 'EMN', 'FMC', 'GOLD', 'IFF',
    'IP', 'KGC', 'MLM', 'MOS', 'MP', 'NEM', 'NTR', 'PKG', 'RS', 'SCCO',
    'SMG', 'STLD', 'TECK', 'VALE', 'WPM',

    # REITs
    'AMT', 'AVB', 'CCI', 'DLR', 'EQIX', 'EQR', 'EXR', 'INVH', 'IRM', 'MAA',
    'O', 'PLD', 'PSA', 'REXR', 'SBAC', 'SPG', 'STAG', 'UDR', 'VICI', 'WELL',

    # EV / Clean Energy
    'CHPT', 'ENPH', 'FSLR', 'LAC', 'LCID', 'LI', 'NIO', 'PLUG', 'QS', 'RIVN',
    'RUN', 'TSLA', 'XPEV',

    # Crypto-adjacent
    'COIN', 'MARA', 'MSTR', 'RIOT',
]

# Remove duplicates and sort
TICKERS = sorted(list(set(TICKERS)))


# =============================================================================
# TECHNICAL INDICATORS (FIXED)
# =============================================================================

def calc_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """Calculate RSI using Wilder's smoothing method (correct implementation)"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothing (equivalent to EMA with alpha = 1/length)
    avg_gain = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50)  # Fill NaN with neutral


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, min_periods=length, adjust=False).mean()


def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate ADX, +DI, -DI (fixed implementation)"""
    # True Range
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    # +DM: up_move > down_move AND up_move > 0
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=high.index)
    # -DM: down_move > up_move AND down_move > 0
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=high.index)

    # Smoothed values
    atr = tr.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

    # Directional Indicators
    plus_di = 100 * plus_dm_smooth / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm_smooth / atr.replace(0, np.nan)

    # ADX
    di_sum = plus_di + minus_di
    di_diff = (plus_di - minus_di).abs()
    dx = 100 * di_diff / di_sum.replace(0, np.nan)
    adx = dx.ewm(alpha=1/length, min_periods=length, adjust=False).mean()

    return adx.fillna(0), plus_di.fillna(0), minus_di.fillna(0)


def calc_sma(series: pd.Series, length: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=length, min_periods=length).mean()


def calc_sma_slope(sma: pd.Series, lookback: int = 20) -> pd.Series:
    """Calculate SMA slope (positive = uptrend)"""
    return (sma - sma.shift(lookback)) / sma.shift(lookback) * 100


def calc_relative_strength(stock_close: pd.Series, benchmark_close: pd.Series, lookback: int = 63) -> pd.Series:
    """Calculate relative strength vs benchmark (e.g., SPY)"""
    stock_ret = stock_close.pct_change(lookback)
    bench_ret = benchmark_close.pct_change(lookback)
    return stock_ret - bench_ret


# =============================================================================
# DATA FETCHING
# =============================================================================

def get_vix_data(start_date: str, end_date: str) -> Dict[str, float]:
    """Download VIX data and return as date lookup dict"""
    print("\nDownloading VIX data...")
    try:
        vix = yf.download('^VIX', start=start_date, end=end_date, progress=False)
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = [col[0] for col in vix.columns]

        vix_lookup = {}
        for date, row in vix.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            vix_lookup[date_str] = float(row['Close'])

        if CONFIG.USE_VIX_FILTER:
            in_range = sum(1 for v in vix_lookup.values() if CONFIG.VIX_MIN <= v <= CONFIG.VIX_MAX)
            print(f"VIX in range [{CONFIG.VIX_MIN}-{CONFIG.VIX_MAX}]: {in_range} days ({in_range/len(vix_lookup)*100:.1f}%)")

        return vix_lookup
    except Exception as e:
        print(f"Warning: Could not download VIX data: {e}")
        return {}


def get_spy_data(start_date: str, end_date: str) -> Optional[pd.Series]:
    """Download SPY data for relative strength calculation"""
    print("Downloading SPY benchmark data...")
    try:
        spy = yf.download('SPY', start=start_date, end=end_date, progress=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = [col[0] for col in spy.columns]
        return spy['Close']
    except Exception as e:
        print(f"Warning: Could not download SPY data: {e}")
        return None


def get_stock_data(ticker: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[Dict]]:
    """Download stock data and info"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Check market cap
        market_cap = info.get('marketCap', 0) or 0
        if market_cap < CONFIG.MIN_MARKET_CAP:
            return None, None

        # Download price data
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if df is None or len(df) < CONFIG.MIN_BARS:
            return None, None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # Validate data quality
        if df['Close'].isna().sum() > len(df) * 0.05:  # More than 5% missing
            return None, None

        # Forward fill small gaps (up to 3 days)
        df = df.ffill(limit=3)

        return df, info

    except Exception as e:
        return None, None


# =============================================================================
# FUNDAMENTAL ANALYSIS
# =============================================================================

def check_fundamentals(info: Dict, config: Config) -> Tuple[int, int]:
    """
    Check fundamental criteria
    Returns (checks_passed, total_checks)

    Note: This uses current fundamentals which introduces look-ahead bias
    for backtesting. In live use, this is fine.
    """
    checks = []

    # P/E ratio
    pe = info.get('trailingPE') or info.get('forwardPE')
    if pe is not None:
        checks.append(0 < pe < config.MAX_PE)

    # PEG ratio
    peg = info.get('pegRatio')
    if peg is not None:
        checks.append(0 < peg < config.MAX_PEG)

    # Debt to Equity
    de = info.get('debtToEquity')
    if de is not None:
        # Normalize if in percentage form
        de = de / 100 if de > 10 else de
        checks.append(de < config.MAX_DEBT_EQUITY)

    # Profit Margin
    pm = info.get('profitMargins')
    if pm is not None:
        checks.append(pm > config.MIN_PROFIT_MARGIN)

    return sum(checks), len(checks)


# =============================================================================
# TRADE EXECUTION
# =============================================================================

def execute_trade(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    entry_idx: int,
    entry_price: float,
    config: Config
) -> Dict[str, Any]:
    """
    Execute a trade with:
    - Fixed initial stop loss
    - Fixed take profit target
    - Optional trailing stop after activation

    Returns trade result dictionary
    """
    stop_price = entry_price * (1 - config.STOP_LOSS_PCT / 100)
    tp_price = entry_price * (1 + config.TAKE_PROFIT_PCT / 100)
    activation_price = entry_price * (1 + config.TRAIL_ACTIVATION_PCT / 100)

    highest_high = entry_price
    trailing_active = False
    trailing_stop = stop_price

    max_dd = 0.0
    max_runup = 0.0

    for day in range(1, config.MAX_HOLD_DAYS + 1):
        idx = entry_idx + day

        # Check if we've run out of data
        if idx >= len(close):
            exit_price = close[-1]
            return_pct = (exit_price - entry_price) / entry_price * 100
            return {
                'return_pct': return_pct,
                'exit_price': exit_price,
                'exit_day': day,
                'exit_reason': 'data_end',
                'max_dd': max_dd,
                'max_runup': max_runup,
                'trailing_activated': trailing_active
            }

        day_high = high[idx]
        day_low = low[idx]
        day_close = close[idx]

        # Track drawdown and runup
        low_ret = (day_low - entry_price) / entry_price * 100
        high_ret = (day_high - entry_price) / entry_price * 100
        max_dd = min(max_dd, low_ret)
        max_runup = max(max_runup, high_ret)

        # Update highest high for trailing
        if day_high > highest_high:
            highest_high = day_high

        # Check trailing activation
        if config.USE_TRAILING and not trailing_active and day_high >= activation_price:
            trailing_active = True

        # Update trailing stop
        if trailing_active:
            new_trail = highest_high * (1 - config.TRAIL_DISTANCE_PCT / 100)
            trailing_stop = max(trailing_stop, new_trail)

        # Current stop level
        current_stop = trailing_stop if trailing_active else stop_price

        # Check stop hit (use stop price, not day low for realistic fill)
        if day_low <= current_stop:
            exit_price = current_stop
            return_pct = (exit_price - entry_price) / entry_price * 100
            exit_reason = 'trail_stop' if trailing_active else 'stop'
            return {
                'return_pct': return_pct,
                'exit_price': exit_price,
                'exit_day': day,
                'exit_reason': exit_reason,
                'max_dd': max_dd,
                'max_runup': max_runup,
                'trailing_activated': trailing_active
            }

        # Check take profit hit
        if day_high >= tp_price:
            return {
                'return_pct': config.TAKE_PROFIT_PCT,
                'exit_price': tp_price,
                'exit_day': day,
                'exit_reason': 'target',
                'max_dd': max_dd,
                'max_runup': max_runup,
                'trailing_activated': trailing_active
            }

    # Max hold time exit
    exit_price = close[entry_idx + config.MAX_HOLD_DAYS]
    return_pct = (exit_price - entry_price) / entry_price * 100
    return {
        'return_pct': return_pct,
        'exit_price': exit_price,
        'exit_day': config.MAX_HOLD_DAYS,
        'exit_reason': 'max_days',
        'max_dd': max_dd,
        'max_runup': max_runup,
        'trailing_activated': trailing_active
    }


# =============================================================================
# SIGNAL GENERATION
# =============================================================================

def check_entry_signal(
    idx: int,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
    rsi: np.ndarray,
    adx: np.ndarray,
    plus_di: np.ndarray,
    minus_di: np.ndarray,
    sma_200: np.ndarray,
    sma_slope: np.ndarray,
    high_52w: np.ndarray,
    volume_avg: np.ndarray,
    rs_values: Optional[np.ndarray],
    config: Config
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if entry conditions are met at index
    Returns (signal_valid, signal_details)
    """
    price = close[idx]

    # Skip if we don't have all indicators
    if np.isnan(sma_200[idx]) or np.isnan(high_52w[idx]) or np.isnan(adx[idx]):
        return False, {}

    # 1. Price position relative to 52-week high
    pct_below_high = (high_52w[idx] - price) / high_52w[idx] * 100
    if not (config.MIN_BELOW_HIGH_PCT <= pct_below_high <= config.MAX_BELOW_HIGH_PCT):
        return False, {}

    # 2. Price near SMA 200 (not too extended)
    pct_from_sma = abs(price - sma_200[idx]) / sma_200[idx] * 100
    if pct_from_sma > config.MAX_FROM_SMA_PCT:
        return False, {}

    # 3. Price must be ABOVE SMA 200 (we want uptrend pullbacks)
    if price < sma_200[idx] * 0.97:  # Allow 3% below
        return False, {}

    # 4. SMA slope positive (uptrend confirmation)
    if not np.isnan(sma_slope[idx]) and sma_slope[idx] < 0:
        return False, {}

    # 5. RSI crossover signal (cross above oversold/signal level)
    rsi_signal = False
    for j in range(1, config.RSI_LOOKBACK + 1):
        prev_idx = idx - j
        curr_idx = idx - j + 1
        if prev_idx >= 0 and curr_idx < len(rsi):
            # RSI crossed above signal level from below
            if rsi[prev_idx] <= config.RSI_SIGNAL and rsi[curr_idx] > config.RSI_SIGNAL:
                rsi_signal = True
                break
            # Or RSI bounced from oversold
            if rsi[prev_idx] <= config.RSI_OVERSOLD:
                rsi_signal = True
                break

    if not rsi_signal:
        return False, {}

    # 6. ADX trend confirmation
    if adx[idx] < config.ADX_MIN:
        return False, {}

    # 7. Directional indicator (optional - bullish bias)
    # Relaxed: don't require +DI > -DI, just check ADX shows trend

    # 8. Volume confirmation
    if config.USE_VOLUME_FILTER:
        if np.isnan(volume_avg[idx]) or volume_avg[idx] == 0:
            return False, {}
        vol_ratio = volume[idx] / volume_avg[idx]
        if vol_ratio < config.VOLUME_SURGE_MULT:
            return False, {}
    else:
        vol_ratio = 1.0

    # 9. Relative strength filter
    if config.USE_RS_FILTER and rs_values is not None:
        if np.isnan(rs_values[idx]):
            return False, {}
        # RS should be at least neutral (not significantly underperforming)
        if rs_values[idx] < -0.10:  # Allow up to 10% underperformance
            return False, {}

    # All conditions met
    details = {
        'pct_below_high': round(pct_below_high, 1),
        'pct_from_sma': round(pct_from_sma, 1),
        'sma_slope': round(sma_slope[idx], 2) if not np.isnan(sma_slope[idx]) else 0,
        'rsi': round(rsi[idx], 1),
        'adx': round(adx[idx], 1),
        'plus_di': round(plus_di[idx], 1),
        'minus_di': round(minus_di[idx], 1),
        'volume_ratio': round(vol_ratio, 2),
        'rs': round(rs_values[idx] * 100, 1) if rs_values is not None and not np.isnan(rs_values[idx]) else None
    }

    return True, details


def scan_stock(
    ticker: str,
    config: Config,
    vix_lookup: Dict[str, float],
    spy_close: Optional[pd.Series]
) -> Tuple[List[Dict], str]:
    """
    Scan a single stock for trading signals
    Returns (list of signals, status string)
    """
    # Get stock data
    df, info = get_stock_data(ticker, config.START_DATE, config.END_DATE)

    if df is None or info is None:
        return [], 'no_data'

    # Check fundamentals
    fund_passed, fund_total = check_fundamentals(info, config)
    if fund_total > 0 and fund_passed < config.MIN_FUNDAMENTAL_CHECKS:
        return [], 'bad_fundamentals'

    # Extract arrays
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    volume = df['Volume'].values
    dates = df.index

    # Calculate indicators
    close_series = pd.Series(close, index=dates)
    high_series = pd.Series(high, index=dates)
    low_series = pd.Series(low, index=dates)
    volume_series = pd.Series(volume, index=dates)

    rsi = calc_rsi(close_series, 14).values
    adx, plus_di, minus_di = calc_adx(high_series, low_series, close_series, 14)
    adx, plus_di, minus_di = adx.values, plus_di.values, minus_di.values

    sma_200 = calc_sma(close_series, 200).values
    sma_slope = calc_sma_slope(pd.Series(sma_200), config.SMA_SLOPE_DAYS).values
    high_52w = high_series.rolling(252).max().values
    volume_avg = volume_series.rolling(config.VOLUME_AVG_DAYS).mean().values

    # Relative strength vs SPY
    rs_values = None
    if config.USE_RS_FILTER and spy_close is not None:
        try:
            # Align SPY data with stock data
            aligned_spy = spy_close.reindex(dates).ffill()
            if len(aligned_spy) == len(close):
                rs = calc_relative_strength(close_series, aligned_spy, config.RS_LOOKBACK)
                rs_values = rs.values
        except:
            pass

    signals = []
    last_signal_idx = -999

    # Start scanning after we have enough history
    start_idx = max(260, config.SMA_SLOPE_DAYS + 200)
    end_idx = len(df) - config.MAX_HOLD_DAYS - 5  # Leave room for trade execution

    for i in range(start_idx, end_idx):
        # Enforce minimum gap between signals
        if i - last_signal_idx < config.MIN_GAP_DAYS:
            continue

        date_str = dates[i].strftime('%Y-%m-%d')

        # VIX filter
        if config.USE_VIX_FILTER:
            vix_value = vix_lookup.get(date_str)
            if vix_value is None:
                continue
            if not (config.VIX_MIN <= vix_value <= config.VIX_MAX):
                continue
        else:
            vix_value = vix_lookup.get(date_str, 0)

        # Check entry signal
        signal_valid, signal_details = check_entry_signal(
            i, close, high, low, volume, rsi, adx, plus_di, minus_di,
            sma_200, sma_slope, high_52w, volume_avg, rs_values, config
        )

        if not signal_valid:
            continue

        # Execute trade
        entry_price = close[i]
        trade_result = execute_trade(close, high, low, i, entry_price, config)

        # Position sizing
        risk_dollars = config.ACCOUNT_SIZE * (config.RISK_PER_TRADE_PCT / 100)
        position_value = risk_dollars / (config.STOP_LOSS_PCT / 100)
        position_value = min(position_value, config.ACCOUNT_SIZE * (config.MAX_POSITION_PCT / 100))
        shares = int(position_value / entry_price)
        pnl = position_value * (trade_result['return_pct'] / 100)

        signal = {
            'ticker': ticker,
            'date': date_str,
            'entry': round(entry_price, 2),
            'vix': round(vix_value, 1) if vix_value else None,
            'sector': info.get('sector', 'Unknown'),
            **signal_details,
            'return_pct': round(trade_result['return_pct'], 2),
            'exit_price': round(trade_result['exit_price'], 2),
            'exit_day': trade_result['exit_day'],
            'exit_reason': trade_result['exit_reason'],
            'trailing_activated': trade_result['trailing_activated'],
            'shares': shares,
            'position': round(position_value, 0),
            'pnl': round(pnl, 0),
            'max_dd': round(trade_result['max_dd'], 1),
            'max_runup': round(trade_result['max_runup'], 1),
        }

        signals.append(signal)
        last_signal_idx = i

    return signals, 'success'


# =============================================================================
# ANALYSIS & REPORTING
# =============================================================================

def calculate_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate performance metrics from results DataFrame"""
    ret = df['return_pct']
    wins = ret > 0

    metrics = {
        'total_trades': len(ret),
        'winners': wins.sum(),
        'losers': (~wins).sum(),
        'win_rate': wins.mean() * 100,
        'avg_return': ret.mean(),
        'avg_win': ret[wins].mean() if wins.any() else 0,
        'avg_loss': ret[~wins].mean() if (~wins).any() else 0,
        'best_trade': ret.max(),
        'worst_trade': ret.min(),
        'total_pnl': df['pnl'].sum(),
        'avg_pnl': df['pnl'].mean(),
        'avg_hold_days': df['exit_day'].mean(),
        'median_hold_days': df['exit_day'].median(),
    }

    # Risk metrics
    if (~wins).any() and metrics['avg_loss'] != 0:
        metrics['win_loss_ratio'] = abs(metrics['avg_win'] / metrics['avg_loss'])
    else:
        metrics['win_loss_ratio'] = float('inf')

    metrics['expectancy'] = (metrics['win_rate']/100 * metrics['avg_win']) + \
                           ((100-metrics['win_rate'])/100 * metrics['avg_loss'])

    if ret.std() > 0:
        metrics['sharpe_like'] = ret.mean() / ret.std()
    else:
        metrics['sharpe_like'] = 0

    if (~wins).any() and ret[~wins].sum() != 0:
        metrics['profit_factor'] = ret[wins].sum() / abs(ret[~wins].sum())
    else:
        metrics['profit_factor'] = float('inf')

    return metrics


def print_results(df: pd.DataFrame, config: Config):
    """Print detailed analysis of backtest results"""
    metrics = calculate_metrics(df)

    print(f"\n{'='*70}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*70}")
    print(f"Total Trades:     {metrics['total_trades']}")
    print(f"Win Rate:         {metrics['win_rate']:.1f}% ({metrics['winners']}W / {metrics['losers']}L)")
    print(f"Avg Return:       {metrics['avg_return']:+.2f}%")
    print(f"Avg Win:          +{metrics['avg_win']:.2f}%")
    print(f"Avg Loss:         {metrics['avg_loss']:.2f}%")
    print(f"Best Trade:       +{metrics['best_trade']:.2f}%")
    print(f"Worst Trade:      {metrics['worst_trade']:.2f}%")

    print(f"\n{'='*70}")
    print("RISK METRICS")
    print(f"{'='*70}")
    print(f"Win/Loss Ratio:   {metrics['win_loss_ratio']:.2f}:1")
    print(f"Expectancy:       {metrics['expectancy']:+.2f}% per trade")
    print(f"Profit Factor:    {metrics['profit_factor']:.2f}")
    print(f"Sharpe-like:      {metrics['sharpe_like']:.3f}")

    print(f"\n{'='*70}")
    print("DOLLAR P&L")
    print(f"{'='*70}")
    print(f"Total P&L:        ${metrics['total_pnl']:+,.0f}")
    print(f"Avg P&L/Trade:    ${metrics['avg_pnl']:+,.0f}")

    print(f"\n{'='*70}")
    print("HOLDING PERIOD")
    print(f"{'='*70}")
    print(f"Avg Hold:         {metrics['avg_hold_days']:.1f} days")
    print(f"Median Hold:      {metrics['median_hold_days']:.0f} days")

    # Exit breakdown
    print(f"\n{'='*70}")
    print("EXIT BREAKDOWN")
    print(f"{'='*70}")
    for reason in ['stop', 'trail_stop', 'target', 'max_days', 'data_end']:
        subset = df[df['exit_reason'] == reason]
        if len(subset) > 0:
            pct = len(subset) / len(df) * 100
            avg_ret = subset['return_pct'].mean()
            avg_day = subset['exit_day'].mean()
            print(f"  {reason:12s}: {len(subset):4d} ({pct:5.1f}%) | Avg: {avg_ret:+6.2f}% | Days: {avg_day:.0f}")

    trail_count = df['trailing_activated'].sum()
    print(f"\nTrailing Activated: {trail_count}/{len(df)} ({trail_count/len(df)*100:.1f}%)")

    # By Year
    print(f"\n{'='*70}")
    print("PERFORMANCE BY YEAR")
    print(f"{'='*70}")
    df['year'] = pd.to_datetime(df['date']).dt.year
    yearly = df.groupby('year').agg({
        'return_pct': ['count', 'mean', lambda x: (x > 0).mean() * 100],
        'pnl': 'sum'
    }).round(2)
    yearly.columns = ['Trades', 'Avg%', 'WinRate%', 'TotalPnL']
    print(yearly.to_string())

    # By Sector
    print(f"\n{'='*70}")
    print("PERFORMANCE BY SECTOR")
    print(f"{'='*70}")
    sector = df.groupby('sector').agg({
        'return_pct': ['count', 'mean', lambda x: (x > 0).mean() * 100],
        'pnl': 'sum'
    }).round(2)
    sector.columns = ['Trades', 'Avg%', 'WinRate%', 'TotalPnL']
    sector = sector.sort_values('WinRate%', ascending=False)
    print(sector.head(15).to_string())

    # Top/Bottom trades
    print(f"\n{'='*70}")
    print("TOP 10 TRADES")
    print(f"{'='*70}")
    cols = ['ticker', 'date', 'return_pct', 'exit_reason', 'exit_day', 'pnl']
    print(df.nlargest(10, 'return_pct')[cols].to_string(index=False))

    print(f"\n{'='*70}")
    print("BOTTOM 10 TRADES")
    print(f"{'='*70}")
    print(df.nsmallest(10, 'return_pct')[cols].to_string(index=False))


# =============================================================================
# MAIN SCANNER
# =============================================================================

def run_screener(config: Config = CONFIG) -> pd.DataFrame:
    """Run the full screener and return results DataFrame"""

    print("="*70)
    print("MARKET SNIPER SCREENER v2.0")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Stop Loss:     {config.STOP_LOSS_PCT}%")
    print(f"  Take Profit:   {config.TAKE_PROFIT_PCT}% ({config.TAKE_PROFIT_PCT/config.STOP_LOSS_PCT:.1f}R)")
    print(f"  Trailing:      {'Enabled' if config.USE_TRAILING else 'Disabled'}")
    if config.USE_TRAILING:
        print(f"    Activation:  +{config.TRAIL_ACTIVATION_PCT}%")
        print(f"    Distance:    {config.TRAIL_DISTANCE_PCT}%")
    print(f"  Max Hold:      {config.MAX_HOLD_DAYS} days")
    print(f"  VIX Filter:    {'Enabled' if config.USE_VIX_FILTER else 'Disabled'}")
    if config.USE_VIX_FILTER:
        print(f"    Range:       {config.VIX_MIN} - {config.VIX_MAX}")
    print(f"  Volume Filter: {'Enabled' if config.USE_VOLUME_FILTER else 'Disabled'}")
    print(f"  RS Filter:     {'Enabled' if config.USE_RS_FILTER else 'Disabled'}")
    print(f"  Universe:      {len(TICKERS)} tickers")

    # Get market data
    vix_lookup = get_vix_data(config.START_DATE, config.END_DATE)
    spy_close = get_spy_data(config.START_DATE, config.END_DATE) if config.USE_RS_FILTER else None

    # Scan all stocks
    all_signals = []
    stats = {'success': 0, 'no_data': 0, 'bad_fundamentals': 0, 'error': 0}

    print(f"\n{'='*70}")
    print("SCANNING STOCKS...")
    print(f"{'='*70}")

    start_time = time.time()

    for i, ticker in enumerate(TICKERS):
        # Progress update
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed * 60 if elapsed > 0 else 0
            eta = (len(TICKERS) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1:4d}/{len(TICKERS)}] Signals: {len(all_signals):4d} | "
                  f"Rate: {rate:.0f}/min | ETA: {eta:.1f}min")

        try:
            signals, status = scan_stock(ticker, config, vix_lookup, spy_close)
            stats[status] = stats.get(status, 0) + 1
            all_signals.extend(signals)
        except Exception as e:
            stats['error'] += 1

        # Rate limiting
        if (i + 1) % 100 == 0:
            time.sleep(1)

    elapsed = time.time() - start_time

    print(f"\n{'='*70}")
    print("SCAN COMPLETE")
    print(f"{'='*70}")
    print(f"Time:            {elapsed/60:.1f} minutes")
    print(f"Stocks scanned:  {len(TICKERS)}")
    print(f"Valid stocks:    {stats['success']}")
    print(f"No data:         {stats['no_data']}")
    print(f"Bad fundamentals:{stats['bad_fundamentals']}")
    print(f"Errors:          {stats['error']}")
    print(f"Total signals:   {len(all_signals)}")

    if not all_signals:
        print("\nNo signals found. Try adjusting filters.")
        return pd.DataFrame()

    # Create results DataFrame
    df = pd.DataFrame(all_signals)

    # Print analysis
    print_results(df, config)

    return df


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Run with default configuration
    results = run_screener()

    if len(results) > 0:
        # Save results
        output_file = 'screener_results.csv'
        results.to_csv(output_file, index=False)
        print(f"\nResults saved to {output_file}")

        # For Colab - download file
        try:
            from google.colab import files
            files.download(output_file)
        except ImportError:
            pass
