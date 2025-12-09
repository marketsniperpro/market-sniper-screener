import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabase';

// GET /api/stats - Get performance statistics
export async function GET(request: NextRequest) {
  const supabase = createServerClient();

  try {
    // Get overall stats
    const { data: signals, error: signalsError } = await supabase
      .from('signals')
      .select('return_pct, pnl, is_winner, sector, fund_score');

    if (signalsError) {
      return NextResponse.json({ error: signalsError.message }, { status: 500 });
    }

    if (!signals || signals.length === 0) {
      return NextResponse.json({
        stats: {
          total_signals: 0,
          win_rate: 0,
          avg_return: 0,
          total_pnl: 0,
          profit_factor: 0,
        },
        sectors: [],
      });
    }

    // Calculate overall stats
    const withResults = signals.filter(s => s.return_pct !== null);
    const winners = withResults.filter(s => s.is_winner);
    const losers = withResults.filter(s => !s.is_winner);

    const totalPnl = withResults.reduce((sum, s) => sum + (s.pnl || 0), 0);
    const avgReturn = withResults.reduce((sum, s) => sum + (s.return_pct || 0), 0) / withResults.length;
    const winRate = (winners.length / withResults.length) * 100;

    const winSum = winners.reduce((sum, s) => sum + (s.return_pct || 0), 0);
    const lossSum = Math.abs(losers.reduce((sum, s) => sum + (s.return_pct || 0), 0));
    const profitFactor = lossSum > 0 ? winSum / lossSum : winSum;

    // Calculate sector stats
    const sectorMap = new Map<string, {
      trades: number;
      wins: number;
      returns: number[];
      pnl: number;
      scores: number[];
    }>();

    for (const signal of withResults) {
      const sector = signal.sector || 'Unknown';
      if (!sectorMap.has(sector)) {
        sectorMap.set(sector, { trades: 0, wins: 0, returns: [], pnl: 0, scores: [] });
      }
      const s = sectorMap.get(sector)!;
      s.trades++;
      if (signal.is_winner) s.wins++;
      s.returns.push(signal.return_pct || 0);
      s.pnl += signal.pnl || 0;
      s.scores.push(signal.fund_score || 0);
    }

    const sectors = Array.from(sectorMap.entries()).map(([sector, data]) => ({
      sector,
      total_trades: data.trades,
      win_rate: Math.round((data.wins / data.trades) * 1000) / 10,
      avg_return: Math.round(data.returns.reduce((a, b) => a + b, 0) / data.returns.length * 100) / 100,
      total_pnl: data.pnl,
      avg_fund_score: Math.round(data.scores.reduce((a, b) => a + b, 0) / data.scores.length * 10) / 10,
    })).sort((a, b) => b.total_pnl - a.total_pnl);

    return NextResponse.json({
      stats: {
        total_signals: signals.length,
        win_rate: Math.round(winRate * 10) / 10,
        avg_return: Math.round(avgReturn * 100) / 100,
        total_pnl: Math.round(totalPnl),
        profit_factor: Math.round(profitFactor * 100) / 100,
      },
      sectors,
    });
  } catch (err) {
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
