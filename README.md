# Market Sniper Screener v3.0

A Python stock screener for swing trading with **VIX-based market timing**. Optimized for crash protection while capturing upside.

## Backtest Results (2019-2024)

```
Tickers Scanned:  904 (S&P 500 + S&P 400)
Total Signals:    1,097
Win Rate:         61%
Total P&L:        +$320,445
vs SPY Buy/Hold:  +$128,000 better
```

### Yearly Performance
| Year | Signals | Win Rate | P&L |
|------|---------|----------|-----|
| 2019 | 149 | 63.1% | +$57,449 |
| 2020 | 174 | 57.5% | +$45,190 |
| 2021 | 200 | 62.5% | +$75,213 |
| 2022 | 159 | 54.7% | +$25,608 |
| 2023 | 217 | 63.1% | +$67,983 |
| 2024 | 198 | 65.7% | +$49,002 |

## Strategy Overview

### VIX Market Timing (Key Innovation)
- **VIX 20-35**: BUY ZONE - Elevated fear = better entries
- **VIX < 20**: WAIT - Market complacent, poor risk/reward
- **VIX > 35**: WAIT - Extreme panic, catching falling knives

The VIX ceiling of 35 (vs 50) improves crash year performance by ~$20k while maintaining overall returns.

### Entry Criteria
1. **VIX in range**: 20-35 (market fear without panic)
2. **Price correction**: 25-50% below 52-week high
3. **RSI crossover**: Recently crossed above 45
4. **ADX > 18**: Trending market confirmed
5. **Volume**: 1.3x above 50-day average
6. **Near support**: Within 12% of SMA 200
7. **Fundamentals**: P/E < 30, ROE > 8%, D/E < 2

### Exit Rules
- **Stop Loss**: 15%
- **Take Profit**: 50% (3.3:1 R/R)
- **Trailing Stop**: Activates at +15%, trails 10%
- **Time Stop**: 90 days max hold

### Signal Scoring (0-100)
- **Strong (75-100)**: All conditions met, high conviction
- **Medium (50-74)**: Most conditions met
- **Weak (<50)**: Marginal setup, lower size

## Quick Start

### Option 1: Google Colab (Backtesting)

1. Upload `backtest_vs_spy.py` to Colab
2. Set scan mode:
   ```python
   SCAN_MODE = 'medium'  # 'fast'=500, 'medium'=900, 'full'=6000 tickers
   ```
3. Run all cells
4. Review results in `backtest_results.csv`

### Option 2: Supabase Edge Function (Live Scanning)

See [INTEGRATION.md](INTEGRATION.md) for full setup.

```bash
# Deploy Edge Function
supabase functions deploy stock-screener

# Trigger scan
curl https://your-project.supabase.co/functions/v1/stock-screener?mode=scan
```

## File Structure

```
market-sniper-screener/
├── backtest_vs_spy.py       # Main backtester with SPY comparison
├── vix_smart.py             # VIX optimization testing
├── vix_optimization.py      # VIX ceiling analysis
├── ticker_fetcher.py        # Dynamic ticker fetching module
├── screener_balanced.py     # Original balanced screener
│
├── supabase/
│   ├── schema.sql           # Database schema for VIX strategy
│   └── functions/
│       └── stock-screener/
│           └── index.ts     # Deno Edge Function
│
├── worker/
│   └── screener_worker.py   # GitHub Actions worker
│
├── app/                     # Next.js components
│   ├── portal/
│   │   └── screener/
│   │       └── page.tsx     # VIX screener page component
│   ├── api/                 # API routes
│   ├── components/          # React components
│   ├── lib/                 # Supabase client
│   └── types/               # TypeScript types
│
└── .github/
    └── workflows/
        └── screener.yml     # Daily scan automation
```

## Configuration

### Core Parameters
```python
# VIX Filter (optimized)
VIX_MIN = 20                  # Minimum fear level
VIX_MAX = 35                  # Maximum (crash protection)

# Technical
RSI_SIGNAL = 45               # RSI crossover threshold
ADX_MIN = 18                  # Minimum trend strength
MIN_BELOW_HIGH_PCT = 25       # Min correction from high
MAX_BELOW_HIGH_PCT = 50       # Max correction (not falling knife)

# Risk Management
STOP_LOSS_PCT = 15.0          # Stop loss
TAKE_PROFIT_PCT = 50.0        # Take profit (3.3:1 R/R)
TRAIL_ACTIVATION_PCT = 15.0   # Trailing stop activation
TRAIL_DISTANCE_PCT = 10.0     # Trailing distance

# Fundamentals
MAX_PE_RATIO = 30
MIN_ROE = 8
MAX_DEBT_EQUITY = 2.0
```

### Scan Modes
```python
SCAN_MODE = 'medium'  # Choose one:
# 'fast'   - ~500 tickers (S&P 500 only) - 5 min
# 'medium' - ~900 tickers (S&P 500 + 400) - 10 min
# 'full'   - ~6000 tickers (all NASDAQ/NYSE) - 60+ min
```

## Dynamic Ticker Fetching

Tickers are fetched dynamically from official sources:

1. **NASDAQ Official FTP** (primary)
   - `nasdaqtraded.txt` - All NASDAQ securities
   - `otherlisted.txt` - NYSE/AMEX securities

2. **Wikipedia** (fallback)
   - S&P 500, S&P 400, S&P 600, NASDAQ 100

3. **Hardcoded fallback** (~500 stocks if APIs fail)

## Database Schema

The Supabase schema includes:

```sql
-- Main table
CREATE TABLE screener_picks (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR(10),
  pick_date DATE,
  entry_price DECIMAL(10,2),
  vix DECIMAL(5,2),
  rsi DECIMAL(5,2),
  adx DECIMAL(5,2),
  correction_pct DECIMAL(5,2),
  volume_ratio DECIMAL(5,2),
  pe_ratio DECIMAL(10,2),
  signal_score INTEGER,
  signal_strength VARCHAR(10),
  signal_factors TEXT[],
  -- Exit tracking
  exit_date DATE,
  exit_price DECIMAL(10,2),
  exit_reason VARCHAR(20),
  return_pct DECIMAL(8,2)
);

-- Views: active_picks, closed_trades, performance_summary
```

## Why VIX 20-35?

We tested multiple VIX configurations:

| Configuration | 2020 P&L | 2022 P&L | Total P&L |
|--------------|----------|----------|-----------|
| VIX 20-50 (original) | +$37,660 | +$4,983 | +$316,445 |
| **VIX 20-35 (optimized)** | **+$45,190** | **+$25,608** | **+$320,445** |
| VIX 20-30 | +$38,421 | +$31,521 | +$287,013 |

The 35 ceiling blocks buying during extreme panic (VIX > 35 typically means panic selling, not capitulation bottoms).

## Requirements

```
Python 3.8+
pandas
numpy
yfinance
requests
```

## Disclaimer

This screener is for educational and research purposes only. Past backtest performance does not guarantee future results. Always do your own research and manage risk appropriately.

## License

MIT
