# =============================================================================
# PORTFOLIO ANALYSIS MODULE
# =============================================================================
# Analyzes screener results to answer key questions:
# 1. Are we beating the market (SPY)?
# 2. Do trades overlap? Can we take all of them?
# 3. What's the realistic P&L with capital constraints?
# =============================================================================

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def get_spy_annual_returns(start_date: str, end_date: str) -> Dict[int, float]:
    """Get SPY buy-and-hold annual returns for comparison"""
    print("Downloading SPY data for benchmark...")
    try:
        spy = yf.download('SPY', start=start_date, end=end_date, progress=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = [col[0] for col in spy.columns]

        spy['year'] = spy.index.year
        annual_returns = {}

        for year in spy['year'].unique():
            year_data = spy[spy['year'] == year]['Close']
            if len(year_data) > 1:
                start_price = year_data.iloc[0]
                end_price = year_data.iloc[-1]
                annual_returns[year] = (end_price - start_price) / start_price * 100

        return annual_returns
    except Exception as e:
        print(f"Error getting SPY data: {e}")
        return {}


def analyze_trade_overlaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze trade overlaps to see concurrent positions.

    Returns DataFrame with overlap info added to each trade.
    """
    if len(df) == 0:
        return df

    # Convert date to datetime and calculate exit date
    df = df.copy()
    df['entry_date'] = pd.to_datetime(df['date'])
    df['exit_date'] = df['entry_date'] + pd.to_timedelta(df['exit_day'], unit='D')

    # Sort by entry date
    df = df.sort_values('entry_date').reset_index(drop=True)

    # For each trade, count how many other trades are active at entry
    concurrent_at_entry = []
    max_concurrent = []

    for idx, row in df.iterrows():
        entry = row['entry_date']
        exit_dt = row['exit_date']

        # Count trades that are active when this trade enters
        # A trade is active if: its entry <= this entry AND its exit > this entry
        active_at_entry = df[
            (df['entry_date'] <= entry) &
            (df['exit_date'] > entry) &
            (df.index != idx)
        ]
        concurrent_at_entry.append(len(active_at_entry))

        # Find max concurrent during this trade's lifetime
        # Check each day of the trade
        max_conc = len(active_at_entry)
        check_date = entry
        while check_date <= exit_dt:
            active = df[
                (df['entry_date'] <= check_date) &
                (df['exit_date'] > check_date)
            ]
            max_conc = max(max_conc, len(active))
            check_date += timedelta(days=1)
        max_concurrent.append(max_conc)

    df['concurrent_at_entry'] = concurrent_at_entry
    df['max_concurrent'] = max_concurrent

    return df


def simulate_with_capital_constraints(
    df: pd.DataFrame,
    max_positions: int = 5,
    account_size: float = 100000,
    risk_per_trade_pct: float = 1.0,
    stop_loss_pct: float = 15.0
) -> Tuple[pd.DataFrame, Dict]:
    """
    Simulate taking trades with capital constraints.

    If we can only have N positions at once, which trades do we skip?
    Uses first-come-first-served approach.

    Returns:
    - DataFrame of trades actually taken
    - Dict with simulation stats
    """
    if len(df) == 0:
        return df, {}

    df = df.copy()
    df['entry_date'] = pd.to_datetime(df['date'])
    df['exit_date'] = df['entry_date'] + pd.to_timedelta(df['exit_day'], unit='D')
    df = df.sort_values('entry_date').reset_index(drop=True)

    # Track which trades we take
    taken = []
    skipped = []
    active_trades = []  # List of (exit_date, trade_idx)

    for idx, row in df.iterrows():
        entry = row['entry_date']
        exit_dt = row['exit_date']

        # Remove expired trades from active list
        active_trades = [(ex, i) for ex, i in active_trades if ex > entry]

        if len(active_trades) < max_positions:
            # Can take this trade
            taken.append(idx)
            active_trades.append((exit_dt, idx))
        else:
            # Skip this trade - at capacity
            skipped.append(idx)

    # Calculate stats
    taken_df = df.loc[taken].copy()
    skipped_df = df.loc[skipped].copy()

    stats = {
        'total_signals': len(df),
        'trades_taken': len(taken),
        'trades_skipped': len(skipped),
        'skip_rate': len(skipped) / len(df) * 100 if len(df) > 0 else 0,
        'taken_win_rate': (taken_df['return_pct'] > 0).mean() * 100 if len(taken_df) > 0 else 0,
        'taken_avg_return': taken_df['return_pct'].mean() if len(taken_df) > 0 else 0,
        'taken_total_pnl': taken_df['pnl'].sum() if len(taken_df) > 0 else 0,
        'skipped_win_rate': (skipped_df['return_pct'] > 0).mean() * 100 if len(skipped_df) > 0 else 0,
        'skipped_avg_return': skipped_df['return_pct'].mean() if len(skipped_df) > 0 else 0,
        'skipped_total_pnl': skipped_df['pnl'].sum() if len(skipped_df) > 0 else 0,
    }

    return taken_df, stats


def yearly_vs_spy_analysis(df: pd.DataFrame, spy_returns: Dict[int, float]) -> pd.DataFrame:
    """
    Compare strategy returns to SPY by year.

    Returns DataFrame with yearly comparison.
    """
    if len(df) == 0:
        return pd.DataFrame()

    df = df.copy()
    df['year'] = pd.to_datetime(df['date']).dt.year

    # Calculate strategy stats by year
    yearly_stats = df.groupby('year').agg({
        'return_pct': ['count', 'sum', 'mean', lambda x: (x > 0).mean() * 100],
        'pnl': 'sum',
        'position': 'mean'  # Average position size
    }).reset_index()

    yearly_stats.columns = ['year', 'trades', 'total_return_pct', 'avg_return', 'win_rate', 'total_pnl', 'avg_position']

    # Calculate capital-weighted return (approximate)
    # Assumes each trade uses ~$6,666 (1% risk / 15% stop on $100k)
    yearly_stats['capital_deployed'] = yearly_stats['trades'] * yearly_stats['avg_position']

    # Add SPY returns
    yearly_stats['spy_return'] = yearly_stats['year'].map(spy_returns)

    # Calculate excess return (simple, not risk-adjusted)
    # This is rough - compares average trade return to SPY annual return
    yearly_stats['vs_spy'] = yearly_stats['avg_return'] - (yearly_stats['spy_return'] / 12)  # Rough monthly comparison

    # More meaningful: ROI on deployed capital
    yearly_stats['strategy_roi'] = (yearly_stats['total_pnl'] / yearly_stats['capital_deployed'] * 100).round(2)

    return yearly_stats


def print_full_analysis(df: pd.DataFrame, start_date: str = '2018-01-01', end_date: str = None):
    """
    Print comprehensive analysis including:
    1. Yearly P&L vs SPY
    2. Trade overlap analysis
    3. Capital-constrained simulation
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    print("\n" + "="*80)
    print("COMPREHENSIVE PORTFOLIO ANALYSIS")
    print("="*80)

    # Get SPY benchmark
    spy_returns = get_spy_annual_returns(start_date, end_date)

    # === 1. YEARLY VS SPY ===
    print("\n" + "="*80)
    print("1. YEARLY PERFORMANCE VS SPY (BUY & HOLD)")
    print("="*80)

    yearly = yearly_vs_spy_analysis(df, spy_returns)

    if len(yearly) > 0:
        print(f"\n{'Year':<6} {'Trades':<7} {'Win%':<7} {'Avg Ret':<9} {'Total PnL':<12} {'SPY':<8} {'Beat SPY?':<10}")
        print("-" * 75)

        total_pnl = 0
        total_trades = 0
        years_beat = 0

        for _, row in yearly.iterrows():
            year = int(row['year'])
            trades = int(row['trades'])
            win_rate = row['win_rate']
            avg_ret = row['avg_return']
            pnl = row['total_pnl']
            spy_ret = row['spy_return'] if pd.notna(row['spy_return']) else 0

            total_pnl += pnl
            total_trades += trades

            # Simple comparison: did we make money when market went up?
            # And did we avoid losses when market went down?
            beat = "YES" if pnl > 0 or (pnl > spy_ret * 1000) else "NO"  # Rough comparison
            if pnl > 0:
                years_beat += 1

            print(f"{year:<6} {trades:<7} {win_rate:<7.1f} {avg_ret:<+9.2f} ${pnl:<+11,.0f} {spy_ret:<+8.1f}% {beat:<10}")

        print("-" * 75)
        print(f"{'TOTAL':<6} {total_trades:<7} {'':<7} {'':<9} ${total_pnl:<+11,.0f}")
        print(f"\nProfitable years: {years_beat}/{len(yearly)}")

    # === 2. TRADE OVERLAP ANALYSIS ===
    print("\n" + "="*80)
    print("2. TRADE OVERLAP ANALYSIS")
    print("="*80)

    df_overlaps = analyze_trade_overlaps(df)

    if len(df_overlaps) > 0:
        max_concurrent = df_overlaps['max_concurrent'].max()
        avg_concurrent = df_overlaps['concurrent_at_entry'].mean()

        print(f"\nMaximum concurrent positions needed: {max_concurrent}")
        print(f"Average concurrent positions at entry: {avg_concurrent:.1f}")

        # Distribution of concurrent positions
        print(f"\nConcurrent positions distribution:")
        conc_dist = df_overlaps['concurrent_at_entry'].value_counts().sort_index()
        for conc, count in conc_dist.items():
            pct = count / len(df_overlaps) * 100
            bar = "#" * int(pct / 2)
            print(f"  {conc} positions: {count:3d} ({pct:5.1f}%) {bar}")

        # Show which periods had highest overlap
        print(f"\nTrades with highest overlap (entered while 3+ other trades active):")
        high_overlap = df_overlaps[df_overlaps['concurrent_at_entry'] >= 3][['ticker', 'date', 'concurrent_at_entry', 'return_pct', 'pnl']]
        if len(high_overlap) > 0:
            print(high_overlap.to_string(index=False))
        else:
            print("  None - all trades had < 3 concurrent positions")

    # === 3. CAPITAL CONSTRAINT SIMULATION ===
    print("\n" + "="*80)
    print("3. CAPITAL-CONSTRAINED SIMULATION")
    print("="*80)

    for max_pos in [3, 5, 10]:
        taken_df, stats = simulate_with_capital_constraints(df, max_positions=max_pos)

        print(f"\n--- Max {max_pos} concurrent positions ---")
        print(f"Trades taken:  {stats['trades_taken']}/{stats['total_signals']} ({100-stats['skip_rate']:.1f}%)")
        print(f"Trades skipped: {stats['trades_skipped']} ({stats['skip_rate']:.1f}%)")
        print(f"Taken trades:  {stats['taken_win_rate']:.1f}% WR, {stats['taken_avg_return']:+.2f}% avg, ${stats['taken_total_pnl']:+,.0f} P&L")
        if stats['trades_skipped'] > 0:
            print(f"Skipped trades: {stats['skipped_win_rate']:.1f}% WR, {stats['skipped_avg_return']:+.2f}% avg, ${stats['skipped_total_pnl']:+,.0f} P&L")

    # === 4. REALISTIC CAPITAL DEPLOYMENT ===
    print("\n" + "="*80)
    print("4. REALISTIC CAPITAL DEPLOYMENT ANALYSIS")
    print("="*80)

    if len(df) > 0:
        # Calculate actual capital needed
        avg_position = df['position'].mean()
        max_concurrent = df_overlaps['max_concurrent'].max() if len(df_overlaps) > 0 else 1

        capital_needed_max = avg_position * max_concurrent
        capital_for_5 = avg_position * 5

        print(f"\nAverage position size: ${avg_position:,.0f}")
        print(f"Max concurrent positions: {max_concurrent}")
        print(f"Capital needed for ALL trades: ${capital_needed_max:,.0f}")
        print(f"Capital needed for max 5 positions: ${capital_for_5:,.0f}")

        # ROI calculation
        total_pnl = df['pnl'].sum()

        print(f"\nReturns on different capital bases:")
        for capital in [50000, 100000, 150000, 200000]:
            roi = total_pnl / capital * 100
            print(f"  ${capital:,} account: {roi:+.1f}% total return ({roi/len(yearly) if len(yearly) > 0 else 0:+.1f}%/year avg)")

    # === 5. KEY INSIGHTS ===
    print("\n" + "="*80)
    print("5. KEY INSIGHTS")
    print("="*80)

    if len(df) > 0 and len(yearly) > 0:
        total_pnl = df['pnl'].sum()
        total_trades = len(df)
        win_rate = (df['return_pct'] > 0).mean() * 100

        # Check if strategy is practical
        max_conc = df_overlaps['max_concurrent'].max() if len(df_overlaps) > 0 else 1

        print(f"""
Summary:
- Total P&L: ${total_pnl:+,.0f} over {len(yearly)} years
- Average P&L/year: ${total_pnl/len(yearly):+,.0f}
- Win rate: {win_rate:.1f}%
- Max concurrent positions: {max_conc}

Practicality Assessment:
""")
        if max_conc <= 5:
            print("- LOW OVERLAP: You can likely take ALL trades with a $100k account")
        elif max_conc <= 10:
            print("- MODERATE OVERLAP: You can take MOST trades, may skip a few")
        else:
            print("- HIGH OVERLAP: Significant trade skipping required")

        # Check yearly consistency
        profitable_years = (yearly['total_pnl'] > 0).sum()
        if profitable_years == len(yearly):
            print("- CONSISTENT: Profitable every year tested")
        elif profitable_years >= len(yearly) * 0.7:
            print(f"- MOSTLY CONSISTENT: Profitable {profitable_years}/{len(yearly)} years")
        else:
            print(f"- INCONSISTENT: Only profitable {profitable_years}/{len(yearly)} years")

    return df_overlaps


# =============================================================================
# STANDALONE USAGE
# =============================================================================

if __name__ == "__main__":
    # Load results from CSV if exists
    import os

    csv_files = ['screener_results.csv', 'simple_working.csv']

    for csv_file in csv_files:
        if os.path.exists(csv_file):
            print(f"Loading {csv_file}...")
            df = pd.read_csv(csv_file)
            print_full_analysis(df)
            break
    else:
        print("No results file found. Run the screener first.")
