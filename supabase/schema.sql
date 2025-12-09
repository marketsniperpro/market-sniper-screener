-- =============================================================================
-- MARKET SNIPER - SUPABASE SCHEMA
-- =============================================================================
-- Run this in your Supabase SQL Editor to create the tables
-- =============================================================================

-- Signals table - stores all screener picks
CREATE TABLE IF NOT EXISTS signals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    signal_date DATE NOT NULL,
    entry_price DECIMAL(10, 2) NOT NULL,

    -- Technical data
    vix DECIMAL(5, 1),
    rsi DECIMAL(5, 1),
    adx DECIMAL(5, 1),
    pct_below_high DECIMAL(5, 1),

    -- Fundamental data
    sector VARCHAR(50),
    pe_ratio DECIMAL(10, 2),
    peg_ratio DECIMAL(10, 2),
    roe DECIMAL(5, 1),
    debt_equity DECIMAL(10, 2),
    fund_score INTEGER,

    -- Backtest results (historical signals)
    return_pct DECIMAL(8, 2),
    exit_day INTEGER,
    exit_reason VARCHAR(20),
    pnl DECIMAL(10, 0),
    is_winner BOOLEAN,

    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, closed, expired
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicates
    UNIQUE(ticker, signal_date)
);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(signal_date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_sector ON signals(sector);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_fund_score ON signals(fund_score DESC);

-- Performance stats table - aggregated stats
CREATE TABLE IF NOT EXISTS performance_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    stat_date DATE NOT NULL UNIQUE,
    total_signals INTEGER,
    win_rate DECIMAL(5, 1),
    avg_return DECIMAL(8, 2),
    total_pnl DECIMAL(12, 0),
    profit_factor DECIMAL(5, 2),
    best_sector VARCHAR(50),
    worst_sector VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Screener runs - track when the screener ran
CREATE TABLE IF NOT EXISTS screener_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    run_date TIMESTAMPTZ DEFAULT NOW(),
    signals_found INTEGER,
    new_signals INTEGER,
    tickers_scanned INTEGER,
    duration_seconds INTEGER,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT
);

-- VIX history for display
CREATE TABLE IF NOT EXISTS vix_history (
    date DATE PRIMARY KEY,
    close_value DECIMAL(6, 2) NOT NULL,
    is_fear_day BOOLEAN DEFAULT FALSE
);

-- =============================================================================
-- ROW LEVEL SECURITY (Optional - for multi-tenant)
-- =============================================================================

-- Enable RLS
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_stats ENABLE ROW LEVEL SECURITY;

-- Public read access (anyone can view signals)
CREATE POLICY "Public read access" ON signals FOR SELECT USING (true);
CREATE POLICY "Public read access" ON performance_stats FOR SELECT USING (true);

-- Service role can insert/update (for the worker)
CREATE POLICY "Service role insert" ON signals FOR INSERT WITH CHECK (true);
CREATE POLICY "Service role update" ON signals FOR UPDATE USING (true);
CREATE POLICY "Service role insert" ON performance_stats FOR INSERT WITH CHECK (true);

-- =============================================================================
-- VIEWS FOR EASY QUERYING
-- =============================================================================

-- Latest signals view
CREATE OR REPLACE VIEW latest_signals AS
SELECT
    ticker,
    signal_date,
    entry_price,
    sector,
    pe_ratio,
    roe,
    fund_score,
    return_pct,
    is_winner,
    status
FROM signals
WHERE signal_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY signal_date DESC, fund_score DESC;

-- Top picks view (high quality recent signals)
CREATE OR REPLACE VIEW top_picks AS
SELECT
    ticker,
    signal_date,
    entry_price,
    sector,
    pe_ratio,
    peg_ratio,
    roe,
    debt_equity,
    fund_score,
    vix,
    return_pct,
    is_winner
FROM signals
WHERE fund_score >= 8
  AND signal_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY fund_score DESC, signal_date DESC
LIMIT 20;

-- Sector performance view
CREATE OR REPLACE VIEW sector_performance AS
SELECT
    sector,
    COUNT(*) as total_trades,
    ROUND(AVG(CASE WHEN is_winner THEN 1 ELSE 0 END) * 100, 1) as win_rate,
    ROUND(AVG(return_pct), 2) as avg_return,
    SUM(pnl) as total_pnl,
    ROUND(AVG(fund_score), 1) as avg_fund_score
FROM signals
WHERE sector IS NOT NULL
GROUP BY sector
ORDER BY total_pnl DESC;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to get performance summary
CREATE OR REPLACE FUNCTION get_performance_summary()
RETURNS TABLE (
    total_signals BIGINT,
    win_rate DECIMAL,
    avg_return DECIMAL,
    total_pnl DECIMAL,
    profit_factor DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT,
        ROUND(AVG(CASE WHEN is_winner THEN 1 ELSE 0 END) * 100, 1),
        ROUND(AVG(return_pct), 2),
        SUM(pnl),
        CASE
            WHEN SUM(CASE WHEN NOT is_winner THEN ABS(return_pct) ELSE 0 END) > 0
            THEN ROUND(SUM(CASE WHEN is_winner THEN return_pct ELSE 0 END) /
                 SUM(CASE WHEN NOT is_winner THEN ABS(return_pct) ELSE 0 END), 2)
            ELSE 0
        END
    FROM signals;
END;
$$ LANGUAGE plpgsql;
