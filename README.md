# Market Sniper Screener v2.0

A Python stock screener designed for finding high-probability swing trading setups with proper risk management.

## Features

- **Fixed Technical Indicators**: Properly implemented RSI (Wilder's smoothing) and ADX calculations
- **Volume Confirmation**: Signals require above-average volume (1.3x 50-day average)
- **Trend Confirmation**: SMA 200 slope must be positive, price near/above SMA
- **Relative Strength**: Compares stock performance vs SPY benchmark
- **VIX Filter**: Trades during elevated fear (VIX 18-40) for better entries
- **Risk Management**: Configurable stops, targets, and trailing stops
- **Position Sizing**: 1% risk per trade with max 15% position size
- **Fundamental Filters**: P/E, PEG, Debt/Equity, Profit Margin checks

## Quick Start (Google Colab)

1. Open [market_sniper_colab.ipynb](market_sniper_colab.ipynb) in Google Colab
2. Run cells 1-3 to install dependencies and load configuration
3. Adjust settings in Cell 2 if desired
4. Run remaining cells to scan and analyze results

## Strategy Logic

### Entry Criteria (ALL must be true)
1. Price 25-50% below 52-week high (pullback, not falling knife)
2. Price within 12% of rising SMA 200
3. RSI recently crossed above 45 or bounced from 35
4. ADX > 20 (trending market)
5. Volume > 1.3x 50-day average
6. Relative strength vs SPY > -10%
7. VIX between 18-40 (optional, can disable)
8. Passes fundamental checks

### Exit Rules
- **Stop Loss**: 12% (configurable)
- **Take Profit**: 36% (3:1 reward/risk)
- **Trailing Stop**: Activates at +12% gain, trails 8% below highest high
- **Time Stop**: 90 days max hold

## Configuration

Edit the configuration section in the notebook or `screener.py`:

```python
# Risk Management
STOP_LOSS_PCT = 12.0          # Stop loss percentage
TAKE_PROFIT_PCT = 36.0        # Take profit (3:1 R/R)

# Trailing Stop
USE_TRAILING = True
TRAIL_ACTIVATION_PCT = 12.0   # Activate at 1R
TRAIL_DISTANCE_PCT = 8.0      # Trail distance

# Filters
USE_VIX_FILTER = True         # Enable/disable VIX filter
VIX_MIN = 18                  # Minimum VIX
VIX_MAX = 40                  # Maximum VIX
USE_VOLUME_FILTER = True      # Require volume confirmation
USE_RS_FILTER = True          # Require relative strength
```

## Files

- `screener.py` - Full standalone Python script
- `market_sniper_colab.ipynb` - Google Colab notebook version

## Key Improvements Over v1

1. **Fixed ADX calculation** - The original had bugs in directional movement logic
2. **Added volume filter** - Reduces false signals significantly
3. **Trend confirmation** - SMA slope check prevents catching falling knives
4. **Relative strength** - Avoids underperforming stocks
5. **Tighter risk management** - 12% stop vs 15%, better trailing
6. **VIX range** - Avoids extreme panic (>40) and complacency (<18)
7. **Better data validation** - Handles missing data, fills small gaps

## Typical Results

Results vary by market conditions and date range. The screener is designed for:
- **Win Rate**: 50-65%
- **Win/Loss Ratio**: 2:1 to 3:1
- **Average Hold**: 20-45 days
- **Positive Expectancy**: Target +2-5% per trade average

## Disclaimer

This screener is for educational and research purposes only. Past backtest performance does not guarantee future results. Always do your own research and risk management before trading.

## Requirements

- Python 3.8+
- pandas
- numpy
- yfinance

## License

MIT
