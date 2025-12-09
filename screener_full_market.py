# =============================================================================
# MARKET SNIPER SCREENER - FULL US MARKET VERSION
# =============================================================================
# Scans ~1500 stocks (S&P 500 + S&P 400 MidCap + Russell additions)
# VIX filter ON by default (that's where the edge is!)
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

# VIX FILTER - Keep ON, this is where the edge is!
USE_VIX_FILTER = True
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
# FULL US MARKET TICKERS (~1500 stocks)
# S&P 500 + S&P 400 MidCap + Russell 1000 additions
# =============================================================================
TICKERS = [
    # S&P 500 (Full)
    'A', 'AAL', 'AAP', 'AAPL', 'ABBV', 'ABC', 'ABMD', 'ABT', 'ACGL', 'ACN',
    'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEE', 'AEP', 'AES', 'AFL', 'AIG',
    'AIZ', 'AJG', 'AKAM', 'ALB', 'ALGN', 'ALK', 'ALL', 'ALLE', 'AMAT', 'AMCR',
    'AMD', 'AME', 'AMGN', 'AMP', 'AMT', 'AMZN', 'ANET', 'ANSS', 'AON', 'AOS',
    'APA', 'APD', 'APH', 'APTV', 'ARE', 'ATO', 'AVB', 'AVGO', 'AVY', 'AWK',
    'AXP', 'AZO', 'BA', 'BAC', 'BALL', 'BAX', 'BBWI', 'BBY', 'BDX', 'BEN',
    'BF-B', 'BG', 'BIIB', 'BIO', 'BK', 'BKNG', 'BKR', 'BLK', 'BMY', 'BR',
    'BRK-B', 'BRO', 'BSX', 'BWA', 'BXP', 'C', 'CAG', 'CAH', 'CARR', 'CAT',
    'CB', 'CBOE', 'CBRE', 'CCI', 'CCL', 'CDAY', 'CDNS', 'CDW', 'CE', 'CEG',
    'CF', 'CFG', 'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLX', 'CMA',
    'CMCSA', 'CME', 'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COO', 'COP',
    'COST', 'CPB', 'CPRT', 'CPT', 'CRL', 'CRM', 'CSCO', 'CSGP', 'CSX', 'CTAS',
    'CTLT', 'CTRA', 'CTSH', 'CTVA', 'CVS', 'CVX', 'CZR', 'D', 'DAL', 'DD',
    'DE', 'DFS', 'DG', 'DGX', 'DHI', 'DHR', 'DIS', 'DLR', 'DLTR', 'DOV',
    'DOW', 'DPZ', 'DRI', 'DTE', 'DUK', 'DVA', 'DVN', 'DXC', 'DXCM', 'EA',
    'EBAY', 'ECL', 'ED', 'EFX', 'EG', 'EIX', 'EL', 'ELV', 'EMN', 'EMR',
    'ENPH', 'EOG', 'EPAM', 'EQIX', 'EQR', 'EQT', 'ES', 'ESS', 'ETN', 'ETR',
    'ETSY', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE', 'EXR', 'F', 'FANG', 'FAST',
    'FBHS', 'FCX', 'FDS', 'FDX', 'FE', 'FFIV', 'FI', 'FICO', 'FIS', 'FISV',
    'FITB', 'FLT', 'FMC', 'FOX', 'FOXA', 'FRT', 'FSLR', 'FTNT', 'FTV', 'GD',
    'GE', 'GEHC', 'GEN', 'GILD', 'GIS', 'GL', 'GLW', 'GM', 'GNRC', 'GOOG',
    'GOOGL', 'GPC', 'GPN', 'GRMN', 'GS', 'GWW', 'HAL', 'HAS', 'HBAN', 'HCA',
    'HD', 'HES', 'HIG', 'HII', 'HLT', 'HOLX', 'HON', 'HPE', 'HPQ', 'HRL',
    'HSIC', 'HST', 'HSY', 'HUBB', 'HUM', 'HWM', 'IBM', 'ICE', 'IDXX', 'IEX',
    'IFF', 'ILMN', 'INCY', 'INTC', 'INTU', 'INVH', 'IP', 'IPG', 'IQV', 'IR',
    'IRM', 'ISRG', 'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JCI', 'JKHY', 'JNJ',
    'JNPR', 'JPM', 'K', 'KDP', 'KEY', 'KEYS', 'KHC', 'KIM', 'KLAC', 'KMB',
    'KMI', 'KMX', 'KO', 'KR', 'KVUE', 'L', 'LDOS', 'LEN', 'LH', 'LHX', 'LIN',
    'LKQ', 'LLY', 'LMT', 'LNC', 'LNT', 'LOW', 'LRCX', 'LULU', 'LUV', 'LVS',
    'LW', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS', 'MCD', 'MCHP', 'MCK',
    'MCO', 'MDLZ', 'MDT', 'MET', 'META', 'MGM', 'MHK', 'MKC', 'MKTX', 'MLM',
    'MMC', 'MMM', 'MNST', 'MO', 'MOH', 'MOS', 'MPC', 'MPWR', 'MRK', 'MRNA',
    'MRO', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MTCH', 'MTD', 'MU', 'NCLH',
    'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX', 'NI', 'NKE', 'NOC', 'NOW', 'NRG',
    'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWL', 'NWS', 'NWSA', 'NXPI',
    'O', 'ODFL', 'OGN', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OTIS', 'OXY',
    'PANW', 'PARA', 'PAYC', 'PAYX', 'PCAR', 'PCG', 'PEAK', 'PEG', 'PEP', 'PFE',
    'PFG', 'PG', 'PGR', 'PH', 'PHM', 'PKG', 'PKI', 'PLD', 'PM', 'PNC', 'PNR',
    'PNW', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PVH', 'PWR',
    'PXD', 'PYPL', 'QCOM', 'QRVO', 'RCL', 'RE', 'REG', 'REGN', 'RF', 'RHI',
    'RJF', 'RL', 'RMD', 'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX', 'RVTY',
    'SBAC', 'SBUX', 'SCHW', 'SEDG', 'SEE', 'SHW', 'SJM', 'SLB', 'SNA', 'SNPS',
    'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STLD', 'STT', 'STX', 'STZ', 'SWK',
    'SWKS', 'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TDG', 'TDY', 'TECH', 'TEL',
    'TER', 'TFC', 'TFX', 'TGT', 'TJX', 'TMO', 'TMUS', 'TPR', 'TRGP', 'TRMB',
    'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTWO', 'TXN', 'TXT', 'TYL',
    'UAL', 'UDR', 'UHS', 'ULTA', 'UNH', 'UNP', 'UPS', 'URI', 'USB', 'V',
    'VFC', 'VICI', 'VLO', 'VMC', 'VNO', 'VRSK', 'VRSN', 'VRTX', 'VTR', 'VTRS',
    'VZ', 'WAB', 'WAT', 'WBA', 'WBD', 'WDC', 'WEC', 'WELL', 'WFC', 'WHR',
    'WM', 'WMB', 'WMT', 'WRB', 'WRK', 'WST', 'WTW', 'WY', 'WYNN', 'XEL',
    'XOM', 'XRAY', 'XYL', 'YUM', 'ZBH', 'ZBRA', 'ZION', 'ZTS',

    # S&P 400 MidCap (Full)
    'ACIW', 'ACM', 'AEO', 'AFG', 'AGCO', 'AIT', 'ALKS', 'ALLY', 'AMKR', 'AMN',
    'AN', 'ANF', 'AR', 'ARCB', 'ARW', 'ASB', 'ASH', 'ASGN', 'ATI', 'ATR',
    'AYI', 'AZEK', 'BC', 'BCO', 'BDC', 'BERY', 'BHF', 'BJ', 'BLD', 'BOOT',
    'BRKR', 'BROS', 'BTU', 'BWXT', 'BYD', 'CAL', 'CALM', 'CARG', 'CASY', 'CBT',
    'CC', 'CEIX', 'CHE', 'CHDN', 'CHK', 'CHRD', 'CHX', 'CIEN', 'CLF', 'CLH',
    'CMC', 'CNK', 'CNM', 'CNO', 'COHR', 'COLM', 'CPE', 'CRC', 'CRI', 'CRK',
    'CRUS', 'CUZ', 'CW', 'DAR', 'DCI', 'DDS', 'DECK', 'DEI', 'DKS', 'DLB',
    'DOCS', 'DY', 'EAT', 'EGP', 'EHC', 'ELAN', 'ELF', 'ELS', 'ENS', 'ENSG',
    'EPR', 'EQH', 'ESNT', 'EVR', 'EXEL', 'EXLS', 'EXP', 'FAF', 'FCFS', 'FHI',
    'FHN', 'FIVE', 'FIX', 'FL', 'FLO', 'FLS', 'FN', 'FND', 'FOXF', 'FR',
    'FROG', 'FULT', 'G', 'GBX', 'GDDY', 'GEF', 'GFF', 'GGG', 'GH', 'GNTX',
    'GO', 'GTES', 'GVA', 'GWRE', 'GXO', 'H', 'HAE', 'HALO', 'HBI', 'HEI',
    'HGV', 'HI', 'HNI', 'HP', 'HQY', 'HRB', 'HRI', 'HUN', 'HWC', 'HXL',
    'IAC', 'IART', 'IBKR', 'ICFI', 'IDCC', 'IGT', 'INSP', 'IPGP', 'IRT', 'ITT',
    'JBL', 'JEF', 'JJSF', 'JLL', 'JNPR', 'JWN', 'KBH', 'KBR', 'KEX', 'KMT',
    'KNX', 'KRC', 'LAD', 'LANC', 'LEA', 'LFUS', 'LHCG', 'LII', 'LITE', 'LIVN',
    'LNTH', 'LPX', 'LSTR', 'LW', 'MANH', 'MAN', 'MASI', 'MAT', 'MATX', 'MBC',
    'MEDP', 'MHO', 'MIDD', 'MKSI', 'MLI', 'MMSI', 'MMS', 'MOD', 'MORN', 'MPW',
    'MRCY', 'MSA', 'MSM', 'MSTR', 'MTG', 'MTH', 'MTN', 'MTSI', 'MUR', 'MUSA',
    'NBIX', 'NCR', 'NEU', 'NFG', 'NHI', 'NJR', 'NMIH', 'NNN', 'NOG', 'NOV',
    'NVT', 'NYCB', 'NYT', 'OC', 'OGE', 'OGS', 'OHI', 'OLED', 'OLN', 'OMF',
    'ONB', 'ONTO', 'ORI', 'OSK', 'OVV', 'OZK', 'PAG', 'PATK', 'PAYO', 'PBH',
    'PEB', 'PEGA', 'PEN', 'PFGC', 'PII', 'PINC', 'PIPR', 'PLNT', 'POR', 'POST',
    'POWI', 'POWL', 'PRGO', 'PRIM', 'PRMW', 'PRI', 'PRK', 'PRKS', 'PSN', 'PSTG',
    'PTC', 'QLYS', 'R', 'RBC', 'REXR', 'RGA', 'RGEN', 'RGLD', 'RH', 'RHP',
    'RIG', 'RLI', 'RMBS', 'RNG', 'RNR', 'ROG', 'RPM', 'RS', 'RXO', 'SAIA',
    'SANM', 'SBRA', 'SCCO', 'SEIC', 'SF', 'SFM', 'SHAK', 'SIG', 'SKX', 'SKY',
    'SLM', 'SM', 'SMCI', 'SMG', 'SNDR', 'SNV', 'SNX', 'SON', 'SPR', 'SPXC',
    'SSB', 'SSNC', 'ST', 'STAG', 'STRL', 'STWD', 'SUM', 'SWX', 'TGNA', 'THC',
    'THG', 'THO', 'TNET', 'TOL', 'TPH', 'TREX', 'TRU', 'TTEC', 'TTC', 'TWST',
    'UFPI', 'UGI', 'UNFI', 'UNF', 'UNM', 'URBN', 'UTHR', 'VAC', 'VCEL', 'VFC',
    'VIAV', 'VIRT', 'VLY', 'VMI', 'VNT', 'VOYA', 'VSH', 'VSCO', 'VSTS', 'VVV',
    'WAL', 'WBS', 'WDFC', 'WEN', 'WEX', 'WGO', 'WH', 'WHD', 'WING', 'WK',
    'WLK', 'WMS', 'WOR', 'WPC', 'WSC', 'WSO', 'WTFC', 'WWE', 'X', 'XPEL',
    'XPO', 'YETI', 'ZD', 'ZI', 'ZWS',

    # Growth / High Beta / Popular
    'ABNB', 'AFRM', 'AI', 'BILL', 'COIN', 'CRWD', 'DDOG', 'DOCU', 'ESTC',
    'FIVN', 'FSLY', 'GLOB', 'GTLB', 'HOOD', 'HUBS', 'MDB', 'MNDY', 'NET',
    'NTNX', 'OKTA', 'PCTY', 'PD', 'PINS', 'PLTR', 'RBLX', 'RIOT', 'ROKU',
    'S', 'SHOP', 'SMAR', 'SNAP', 'SNOW', 'SOFI', 'SPOT', 'SQ', 'TTD', 'TWLO',
    'U', 'UBER', 'UPST', 'VEEV', 'WIX', 'ZM', 'ZS',

    # Biotech / Pharma
    'ABCL', 'ACAD', 'ALNY', 'APLS', 'ARGX', 'ARWR', 'BBIO', 'BEAM', 'BGNE',
    'BNTX', 'CLDX', 'CORT', 'CRSP', 'DCPH', 'DNLI', 'EDIT', 'EXAS', 'FATE',
    'FOLD', 'IMVT', 'INSM', 'IONS', 'IRTC', 'JAZZ', 'KRTX', 'LEGN', 'MDGL',
    'NVCR', 'PCVX', 'RARE', 'RLAY', 'RPRX', 'RXRX', 'SAGE', 'SRPT', 'VCYT',
    'VKTX', 'XENE', 'ZLAB',

    # Clean Energy / EV
    'ARRY', 'BE', 'BLNK', 'CHPT', 'CSIQ', 'ENVX', 'EVGO', 'FCEL', 'FLNC',
    'GEVO', 'HYLN', 'JKS', 'LAC', 'LAZR', 'LCID', 'LI', 'NEE', 'NIO', 'NKLA',
    'PLUG', 'QS', 'RIVN', 'RUN', 'STEM', 'WKHS', 'XPEV',

    # Crypto-adjacent
    'BITF', 'BTBT', 'CIFR', 'CLSK', 'CORZ', 'HUT', 'HIVE', 'IREN', 'MARA',
    'MSTR', 'WULF',

    # REITs
    'ACC', 'ADC', 'AGNC', 'AMH', 'CCI', 'COLD', 'CUBE', 'DRH', 'EGP', 'EPR',
    'EQR', 'ESS', 'EXR', 'FCPT', 'FRT', 'GLPI', 'HIW', 'HST', 'HT', 'IIPR',
    'INN', 'IRM', 'IRT', 'KIM', 'KRG', 'LTC', 'LXP', 'MAC', 'NLY', 'NNN',
    'OHI', 'PEB', 'PK', 'PMT', 'PSA', 'REG', 'RYN', 'SBRA', 'SHO', 'SKT',
    'SLG', 'STAG', 'SUI', 'TRNO', 'VER', 'VNO', 'VTR', 'WPC', 'XHR',

    # Additional Russell 1000 / Popular Names
    'ASAN', 'AVTR', 'AXS', 'AZPN', 'BAH', 'BILL', 'BIO', 'BL', 'BLDR', 'BMR',
    'BOX', 'BSY', 'CELH', 'CGNX', 'CHWY', 'CIM', 'CIVI', 'CMA', 'CNQ', 'CPRI',
    'CPT', 'CROX', 'CVNA', 'DASH', 'DBX', 'DCT', 'DINO', 'DK', 'DKNG', 'DXPE',
    'ENOV', 'ENVX', 'ERIE', 'ESI', 'ETSY', 'EVCM', 'EVTC', 'EXPE', 'FBIN',
    'FG', 'FIS', 'FLYW', 'FORM', 'FRPT', 'FSV', 'FTDR', 'GDEN', 'GDOT', 'GME',
    'GNRC', 'GOLF', 'GPS', 'GRPN', 'GXO', 'HAIN', 'HASI', 'HLF', 'HLNE', 'HLT',
    'HQI', 'HRMY', 'HURN', 'ICL', 'IGT', 'IIVI', 'IMMU', 'INFN', 'INMD', 'INSW',
    'IONS', 'IOSP', 'IRTC', 'ITCI', 'ITRI', 'JACK', 'JBT', 'JELD', 'JKHY',
    'KAR', 'KEYS', 'KNL', 'KOS', 'KREF', 'KSS', 'LADR', 'LBRDK', 'LC', 'LCII',
    'LECO', 'LEVI', 'LGIH', 'LGND', 'LHCG', 'LILAK', 'LNG', 'LPSN', 'LSCC',
    'LUMN', 'LYFT', 'LZB', 'M', 'MANH', 'MAXR', 'MD', 'MDRX', 'MELI', 'MHO',
    'MIDD', 'MIME', 'MKSI', 'MLCO', 'MMYT', 'MNRL', 'MRCY', 'MRO', 'MSGN',
    'MTCH', 'MTDR', 'MTG', 'MTSI', 'MXIM', 'MYGN', 'NARI', 'NBR', 'NCMI', 'NEWR',
    'NGVT', 'NHI', 'NLSN', 'NMRK', 'NOVT', 'NSTG', 'NUVA', 'NVS', 'NWBI', 'NWE',
    'NWL', 'NXGN', 'OFIX', 'OLED', 'OLLI', 'OMCL', 'ONTO', 'OPCH', 'OPEN',
    'OSIS', 'OSPN', 'OUT', 'PARR', 'PATH', 'PAYC', 'PBF', 'PCH', 'PDCE', 'PENN',
    'PFS', 'PGNY', 'PLMR', 'PLUS', 'PLXS', 'PMTC', 'PNFP', 'PNM', 'PR',
    'PRAA', 'PRA', 'PRFT', 'PRLB', 'PRO', 'PRSP', 'PSB', 'PTON', 'PZZA',
    'RAMP', 'RCII', 'RDFN', 'RDN', 'RES', 'RGP', 'RLAY', 'RMBS', 'RPRX',
    'RPT', 'RRC', 'RVNC', 'SAIL', 'SAIC', 'SAM', 'SASR', 'SBGI', 'SBH',
    'SCHL', 'SCWX', 'SDGR', 'SEM', 'SFNC', 'SGH', 'SGMS', 'SHAK', 'SHLS',
    'SHO', 'SITC', 'SITM', 'SKLZ', 'SLG', 'SLGN', 'SLP', 'SMPL', 'SNEX',
    'SNDX', 'SONO', 'SPHR', 'SPNS', 'SPSC', 'SPWH', 'SPWR', 'SPXC', 'SRC',
    'SRI', 'SSB', 'SSTI', 'STAR', 'STAY', 'STC', 'STNG', 'STRA', 'SUM',
    'SUPN', 'SWI', 'SWN', 'SWX', 'SXT', 'TALO', 'TBI', 'TCN', 'TDOC', 'TDS',
    'TEAM', 'TELL', 'TENB', 'TEVA', 'TFSL', 'TGI', 'TKR', 'TMHC', 'TNDM',
    'TNL', 'TPX', 'TREE', 'TREX', 'TRIP', 'TRMK', 'TRUP', 'TRV', 'TSEM',
    'TTEC', 'TTGT', 'TTI', 'TVTY', 'TWI', 'TWOU', 'TXRH', 'UA', 'UAA',
    'UCTT', 'UFPI', 'UMBF', 'UNVR', 'UPWK', 'USFD', 'USLM', 'USM', 'USPH',
    'UUUU', 'VAL', 'VALE', 'VCEL', 'VCRA', 'VCTR', 'VIAV', 'VICR', 'VIVO',
    'VREX', 'VRNS', 'VRRM', 'VRTU', 'VSAT', 'VSEC', 'VST', 'VVV', 'W',
    'WAFD', 'WB', 'WBS', 'WCC', 'WD', 'WERN', 'WGO', 'WHD', 'WIRE', 'WK',
    'WLK', 'WOLF', 'WOR', 'WPM', 'WRBY', 'WRLD', 'WSC', 'WSBF', 'WSFS',
    'WTS', 'WTTR', 'WW', 'WWW', 'XNCR', 'XPEL', 'XPER', 'YEXT', 'YTRA',
    'ZD', 'ZLAB', 'ZUO',
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
print(f"High fear days (VIX {VIX_MIN}-{VIX_MAX}): {high_fear} ({high_fear/len(vix_lookup)*100:.1f}%)")

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
print(f"MARKET SNIPER SCREENER - FULL US MARKET")
print(f"VIX Filter: {'ON ('+str(VIX_MIN)+'-'+str(VIX_MAX)+')' if USE_VIX_FILTER else 'OFF'}")
print(f"Tickers: {len(TICKERS)}")
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

print(f"\nCompleted in {(time.time()-start_time)/60:.1f} min")
print(f"Valid stocks: {stats['success']} | No data: {stats['no_data']} | Low cap: {stats['low_cap']} | Errors: {stats['error']}")
print(f"Total signals: {len(all_signals)}")

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

    # Profit factor
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

    # By year vs SPY
    print(f"\n{'='*70}")
    print("BY YEAR VS SPY")
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

    total_pnl = df['pnl'].sum()
    spy_total = sum(100000 * spy_annual.get(y, 0) / 100 for y in df['year'].unique())
    print("-"*60)
    print(f"TOTAL: ${total_pnl:+,.0f} vs SPY ${spy_total:+,.0f}")
    if total_pnl > spy_total:
        print(f"** BEAT SPY BY ${total_pnl - spy_total:,.0f} **")

    # By sector
    print(f"\n{'='*70}")
    print("BY SECTOR (Top 10)")
    print(f"{'='*70}")
    sector = df.groupby('sector').agg({
        'return_pct': ['count', 'mean', lambda x: (x > 0).mean() * 100],
        'pnl': 'sum'
    }).round(2)
    sector.columns = ['Trades', 'Avg%', 'WinRate%', 'PnL']
    sector = sector.sort_values('PnL', ascending=False)
    print(sector.head(10).to_string())

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
    print(f"Capital needed for all: ${max_concurrent * 6667:,.0f}")
    if max_concurrent <= 5:
        print("LOW OVERLAP - Can take all trades with $50k!")
    elif max_concurrent <= 10:
        print("MODERATE - Need $70-100k to take all trades")
    else:
        print(f"HIGH OVERLAP - Would need ${max_concurrent * 6667:,.0f}, may skip some")

    # Top trades
    print(f"\n{'='*70}")
    print("TOP 10 TRADES")
    print(f"{'='*70}")
    cols = ['ticker', 'date', 'return_pct', 'exit_reason', 'pnl']
    print(df.nlargest(10, 'return_pct')[cols].to_string(index=False))

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
