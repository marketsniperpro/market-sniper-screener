// Signal type from Supabase
export interface Signal {
  id: string;
  ticker: string;
  signal_date: string;
  entry_price: number;

  // Technical
  vix: number | null;
  rsi: number | null;
  adx: number | null;
  pct_below_high: number | null;

  // Fundamental
  sector: string | null;
  pe_ratio: number | null;
  peg_ratio: number | null;
  roe: number | null;
  debt_equity: number | null;
  fund_score: number;

  // Backtest results
  return_pct: number | null;
  exit_day: number | null;
  exit_reason: string | null;
  pnl: number | null;
  is_winner: boolean | null;

  // Status
  status: 'active' | 'closed' | 'expired';
  created_at: string;
}

export interface PerformanceStats {
  total_signals: number;
  win_rate: number;
  avg_return: number;
  total_pnl: number;
  profit_factor: number;
}

export interface SectorPerformance {
  sector: string;
  total_trades: number;
  win_rate: number;
  avg_return: number;
  total_pnl: number;
  avg_fund_score: number;
}

// API response types
export interface SignalsResponse {
  signals: Signal[];
  total: number;
}

export interface TopPicksResponse {
  picks: Signal[];
}

export interface StatsResponse {
  stats: PerformanceStats;
  sectors: SectorPerformance[];
}
