# =============================================================================
# MARKET SNIPER SCREENER - BALANCED VERSION
# =============================================================================
# Target: ~40 signals/year with quality
# Changes from strict version:
#   - VIX > 20 (was 25) - more days qualify
#   - 20-55% below high (was 25-50%) - wider range
#   - 20 day gap between signals (was 30)
#   - Volume 1.2x (was 1.3x)
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
# CONFIGURATION - BALANCED FOR MORE SIGNALS
# =============================================================================
STOP_LOSS_PCT = 15.0
TAKE_PROFIT_PCT = 50.0
USE_TRAILING = True
TRAIL_ACTIVATION_PCT = 15.0
TRAIL_DISTANCE_PCT = 10.0
MAX_HOLD_DAYS = 120

# VIX FILTER - Lowered to 20 for more opportunities
USE_VIX_FILTER = True
VIX_MIN = 20              # <-- Was 25, now 20
VIX_MAX = 50

# VOLUME - Slightly relaxed
USE_VOLUME_FILTER = True
VOLUME_SURGE_MULT = 1.2   # <-- Was 1.3, now 1.2

ACCOUNT_SIZE = 100000
RISK_PER_TRADE_PCT = 1.0

START_DATE = '2018-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')

# TECHNICAL - Slightly wider ranges
MIN_MARKET_CAP = 1e9
MIN_BARS = 500
RSI_OVERSOLD = 35
RSI_SIGNAL = 45
RSI_LOOKBACK = 5
ADX_MIN = 18              # <-- Was 20, now 18
MIN_BELOW_HIGH_PCT = 20.0 # <-- Was 25, now 20
MAX_BELOW_HIGH_PCT = 55.0 # <-- Was 50, now 55
MAX_FROM_SMA_PCT = 15.0   # <-- Was 12, now 15
SMA_SLOPE_DAYS = 20
VOLUME_AVG_DAYS = 50
MIN_GAP_DAYS = 20         # <-- Was 30, now 20
MAX_POSITION_PCT = 15.0

# =============================================================================
# FULL US MARKET TICKERS (~1500 stocks)
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

    # S&P 400 MidCap
    'ACIW', 'ACM', 'AEO', 'AFG', 'AGCO', 'AIT', 'ALKS', 'ALLY', 'AMKR', 'AMN',
    'AN', 'ANF', 'AR', 'ARCB', 'ARW', 'ASB', 'ASH', 'ASGN', 'ATI', 'ATR',
    'AYI', 'BC', 'BCO', 'BDC', 'BERY', 'BHF', 'BJ', 'BLD', 'BOOT', 'BRKR',
    'BTU', 'BWXT', 'BYD', 'CAL', 'CALM', 'CASY', 'CBT', 'CC', 'CEIX', 'CHE',
    'CHDN', 'CHK', 'CHRD', 'CIEN', 'CLF', 'CLH', 'CMC', 'CNK', 'CNO', 'COHR',
    'COLM', 'CPE', 'CRC', 'CRK', 'CRUS', 'CUZ', 'CW', 'DAR', 'DCI', 'DDS',
    'DECK', 'DEI', 'DKS', 'DLB', 'DY', 'EAT', 'EGP', 'EHC', 'ELAN', 'ELF',
    'ELS', 'ENSG', 'EPR', 'EQH', 'ESNT', 'EVR', 'EXEL', 'EXLS', 'EXP', 'FAF',
    'FCFS', 'FHN', 'FIVE', 'FIX', 'FL', 'FLO', 'FLS', 'FND', 'FOXF', 'FR',
    'G', 'GBX', 'GDDY', 'GEF', 'GGG', 'GNTX', 'GO', 'GTES', 'GVA', 'GWRE',
    'GXO', 'H', 'HAE', 'HALO', 'HBI', 'HEI', 'HGV', 'HI', 'HNI', 'HP', 'HQY',
    'HRB', 'HRI', 'HUN', 'HWC', 'HXL', 'IAC', 'IART', 'IBKR', 'ICFI', 'IDCC',
    'IGT', 'INSP', 'IPGP', 'IRT', 'ITT', 'JBL', 'JEF', 'JLL', 'KBH', 'KBR',
    'KEX', 'KMT', 'KNX', 'KRC', 'LAD', 'LANC', 'LEA', 'LFUS', 'LII', 'LITE',
    'LNTH', 'LPX', 'MANH', 'MAN', 'MASI', 'MAT', 'MATX', 'MEDP', 'MHO', 'MIDD',
    'MKSI', 'MLI', 'MMS', 'MOD', 'MORN', 'MPW', 'MRCY', 'MSA', 'MSM', 'MSTR',
    'MTG', 'MTH', 'MTN', 'MTSI', 'MUR', 'MUSA', 'NBIX', 'NFG', 'NHI', 'NMIH',
    'NNN', 'NOG', 'NOV', 'NVT', 'NYCB', 'NYT', 'OC', 'OGE', 'OHI', 'OLED',
    'OLN', 'OMF', 'ONB', 'ONTO', 'ORI', 'OSK', 'OVV', 'PAG', 'PBH', 'PEB',
    'PEGA', 'PEN', 'PFGC', 'PII', 'PIPR', 'PLNT', 'POR', 'POST', 'POWI', 'POWL',
    'PRGO', 'PRI', 'PSTG', 'QLYS', 'R', 'RBC', 'REXR', 'RGA', 'RGEN', 'RGLD',
    'RH', 'RHP', 'RMBS', 'RNG', 'RNR', 'RPM', 'RS', 'SAIA', 'SANM', 'SBRA',
    'SCCO', 'SEIC', 'SF', 'SFM', 'SHAK', 'SIG', 'SKX', 'SKY', 'SLM', 'SM',
    'SMCI', 'SMG', 'SNDR', 'SNV', 'SNX', 'SON', 'SPR', 'SPXC', 'SSB', 'SSNC',
    'ST', 'STAG', 'STRL', 'STWD', 'THC', 'THO', 'TNET', 'TOL', 'TPH', 'TREX',
    'TRU', 'TTEC', 'TTC', 'UFPI', 'UGI', 'UNFI', 'UNF', 'UNM', 'URBN', 'UTHR',
    'VAC', 'VCEL', 'VIAV', 'VIRT', 'VOYA', 'VSCO', 'VVV', 'WAL', 'WBS', 'WEN',
    'WEX', 'WGO', 'WH', 'WHD', 'WING', 'WLK', 'WMS', 'WOR', 'WSC', 'WSO',
    'WTFC', 'X', 'XPO', 'YETI',

    # Growth / Tech
    'ABNB', 'AFRM', 'AI', 'BILL', 'COIN', 'CRWD', 'DDOG', 'DOCU', 'ESTC',
    'FTNT', 'GLOB', 'GTLB', 'HOOD', 'HUBS', 'MDB', 'MNDY', 'NET', 'NTNX',
    'OKTA', 'PCTY', 'PINS', 'PLTR', 'RBLX', 'RIOT', 'ROKU', 'SHOP', 'SNAP',
    'SNOW', 'SOFI', 'SPOT', 'SQ', 'TTD', 'TWLO', 'U', 'UBER', 'UPST', 'VEEV',
    'WIX', 'ZI', 'ZM', 'ZS',

    # Biotech
    'ALNY', 'ARGX', 'BGNE', 'BNTX', 'CRSP', 'EXAS', 'INCY', 'IONS', 'JAZZ',
    'LEGN', 'MDGL', 'NBIX', 'RARE', 'REGN', 'RPRX', 'SRPT', 'UTHR', 'VKTX',

    # Energy
    'APA', 'AR', 'BKR', 'CHK', 'CHRD', 'CNX', 'CTRA', 'DVN', 'EOG', 'EQT',
    'FANG', 'HAL', 'HES', 'KMI', 'MPC', 'MRO', 'MTDR', 'MUR', 'NOV', 'OKE',
    'OVV', 'OXY', 'PXD', 'RRC', 'SLB', 'SM', 'SWN', 'TRGP', 'VLO', 'WMB', 'XOM',

    # Financials
    'ACGL', 'AFG', 'AIG', 'AJG', 'ALL', 'ALLY', 'AON', 'APO', 'AXP', 'AXS',
    'BAC', 'BK', 'BLK', 'BRO', 'BX', 'C', 'CB', 'CFG', 'CINF', 'CMA', 'COF',
    'DFS', 'ERIE', 'EVR', 'FITB', 'FNB', 'GS', 'HBAN', 'HIG', 'IBKR', 'ICE',
    'JPM', 'KEY', 'KKR', 'L', 'LPLA', 'MET', 'MMC', 'MS', 'MTB', 'MTG',
    'NDAQ', 'NMIH', 'NTRS', 'ORI', 'PFG', 'PGR', 'PIPR', 'PNC', 'PRU', 'RDN',
    'RF', 'RGA', 'RJF', 'RNR', 'SCHW', 'SEIC', 'SF', 'SLM', 'SOFI', 'STT',
    'SYF', 'TFC', 'TROW', 'TRV', 'UNM', 'USB', 'VOYA', 'WAL', 'WBS', 'WFC',
    'WRB', 'ZION',

    # Industrials
    'AGCO', 'AXON', 'BAH', 'BLDR', 'CAT', 'CMI', 'DE', 'EME', 'EMR', 'ETN',
    'FAST', 'FDX', 'FTV', 'GE', 'GNRC', 'GWW', 'HEI', 'HON', 'HWM', 'IEX',
    'IR', 'ITT', 'ITW', 'J', 'JBHT', 'JBL', 'JCI', 'KBR', 'LDOS', 'LMT',
    'MAS', 'MLI', 'MMM', 'MOD', 'NDSN', 'NOC', 'ODFL', 'OSK', 'OTIS', 'PCAR',
    'PH', 'PNR', 'PWR', 'RBC', 'ROK', 'ROL', 'ROP', 'RSG', 'RTX', 'SAIA',
    'SNA', 'STRL', 'SWK', 'TDG', 'TDY', 'TT', 'TTC', 'TXT', 'UFPI', 'UNP',
    'UPS', 'URI', 'WAB', 'WCC', 'WM', 'XPO', 'XYL',

    # Consumer
    'AMZN', 'ANF', 'AZO', 'BBY', 'BKNG', 'BURL', 'CCL', 'CHWY', 'CMG', 'COST',
    'CPRI', 'CROX', 'CVNA', 'DASH', 'DG', 'DHI', 'DKS', 'DLTR', 'DPZ', 'DRI',
    'ETSY', 'EXPE', 'F', 'FIVE', 'FND', 'GM', 'GPS', 'GPC', 'HAS', 'HD',
    'HLT', 'KMX', 'KR', 'LEN', 'LOW', 'LULU', 'LVS', 'LYFT', 'M', 'MAR',
    'MAT', 'MCD', 'MGM', 'NCLH', 'NKE', 'NVR', 'OLLI', 'ORLY', 'PHM', 'POOL',
    'PTON', 'RCL', 'RH', 'RL', 'ROST', 'SBUX', 'SHAK', 'SKX', 'TGT', 'TJX',
    'TOL', 'TPR', 'TRIP', 'TSCO', 'TSLA', 'UA', 'UBER', 'ULTA', 'URBN', 'VFC',
    'W', 'WHR', 'WING', 'WMT', 'WSM', 'WYNN', 'YUM',

    # Materials
    'AA', 'ALB', 'BALL', 'CCJ', 'CE', 'CF', 'CLF', 'DOW', 'EMN', 'FCX',
    'FMC', 'GOLD', 'IFF', 'IP', 'LIN', 'LYB', 'MLM', 'MOS', 'MP', 'NEM',
    'NTR', 'NUE', 'OLN', 'PKG', 'PPG', 'RGLD', 'RS', 'SCCO', 'SHW', 'SMG',
    'SON', 'STLD', 'TECK', 'VALE', 'VMC', 'WPM', 'WRK',

    # REITs
    'ACC', 'AMT', 'ARE', 'AVB', 'CCI', 'CPT', 'CUBE', 'DLR', 'EGP', 'EQIX',
    'EQR', 'ESS', 'EXR', 'FR', 'FRT', 'GLPI', 'HST', 'INVH', 'IRM', 'IRT',
    'KIM', 'KRC', 'MAA', 'MPW', 'NNN', 'O', 'OHI', 'PEB', 'PLD', 'PSA',
    'REG', 'REXR', 'SBAC', 'SLG', 'SPG', 'STAG', 'UDR', 'VICI', 'VNO', 'VTR',
    'WELL', 'WPC',

    # Utilities
    'AEE', 'AEP', 'AES', 'ATO', 'AWK', 'CMS', 'CNP', 'D', 'DTE', 'DUK',
    'ED', 'EIX', 'ES', 'ETR', 'EVRG', 'EXC', 'FE', 'LNT', 'NEE', 'NI',
    'NRG', 'PCG', 'PEG', 'PNW', 'PPL', 'SO', 'SRE', 'VST', 'WEC', 'XEL',

    # Clean Energy / EV
    'CHPT', 'ENPH', 'FSLR', 'LAC', 'LCID', 'LI', 'NIO', 'PLUG', 'QS', 'RIVN',
    'RUN', 'SEDG', 'XPEV',

    # Crypto
    'COIN', 'MARA', 'MSTR', 'RIOT',
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
        if (info.get('marketCap', 0) or 0) < MIN_MARKET_CAP:
            return [], 'low_cap'

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

            if not np.isnan(sma_slope[i]) and sma_slope[i] < -2:  # Allow slightly negative
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
# RUN
# =============================================================================
print(f"\n{'='*70}")
print(f"MARKET SNIPER - BALANCED (Target: ~40/year)")
print(f"VIX: {VIX_MIN}-{VIX_MAX} | Below High: {MIN_BELOW_HIGH_PCT}-{MAX_BELOW_HIGH_PCT}%")
print(f"{'='*70}")

all_signals = []
stats = {'success': 0, 'no_data': 0, 'error': 0, 'low_cap': 0}
start_time = time.time()

for i, ticker in enumerate(TICKERS):
    if (i + 1) % 100 == 0:
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed * 60 if elapsed > 0 else 0
        eta = (len(TICKERS) - i - 1) / rate if rate > 0 else 0
        print(f"  [{i+1:4d}/{len(TICKERS)}] Signals: {len(all_signals):4d} | {rate:.0f}/min | ETA: {eta:.0f}min")

    signals, status = scan_stock(ticker)
    stats[status] = stats.get(status, 0) + 1
    all_signals.extend(signals)

    if (i + 1) % 150 == 0:
        time.sleep(2)

print(f"\nDone in {(time.time()-start_time)/60:.1f} min | Signals: {len(all_signals)}")
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
    print("PERFORMANCE")
    print(f"{'='*70}")
    print(f"Trades: {len(ret)} | Win Rate: {wins.mean()*100:.1f}%")
    print(f"Avg Return: {ret.mean():+.2f}% | Avg Win: +{ret[wins].mean():.1f}% | Avg Loss: {ret[~wins].mean():.1f}%")
    print(f"Total P&L: ${df['pnl'].sum():+,.0f}")

    if (~wins).any() and ret[~wins].sum() != 0:
        pf = ret[wins].sum() / abs(ret[~wins].sum())
        print(f"Profit Factor: {pf:.2f}")

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

    # Overlap
    print(f"\n{'='*70}")
    print("OVERLAP CHECK")
    print(f"{'='*70}")
    df['entry_date'] = pd.to_datetime(df['date'])
    df['exit_date'] = df['entry_date'] + pd.to_timedelta(df['exit_day'], unit='D')
    df = df.sort_values('entry_date').reset_index(drop=True)
    max_concurrent = 0
    for _, row in df.iterrows():
        active = df[(df['entry_date'] <= row['entry_date']) & (df['exit_date'] > row['entry_date'])]
        max_concurrent = max(max_concurrent, len(active))
    print(f"Max concurrent: {max_concurrent} positions")

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
