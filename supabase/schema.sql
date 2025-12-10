-- =============================================================================
-- MARKET SNIPER - VIX SCREENER SCHEMA
-- =============================================================================
-- Run this in Supabase SQL Editor
-- This REPLACES the old screener_picks table
-- =============================================================================

-- Drop old table if exists (WARNING: deletes all data)
DROP TABLE IF EXISTS screener_picks CASCADE;

-- Create new screener_picks table
CREATE TABLE screener_picks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Stock info
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(100),
    pick_date DATE NOT NULL,

    -- Prices
    entry_price DECIMAL(10, 2) NOT NULL,
    current_price DECIMAL(10, 2),
    exit_price DECIMAL(10, 2),
    exit_date DATE,
    gain_loss_pct DECIMAL(8, 2),

    -- VIX Strategy Indicators
    vix DECIMAL(5, 1),                    -- VIX at entry
    rsi DECIMAL(5, 1),                    -- Daily RSI
    adx DECIMAL(5, 1),                    -- ADX trend strength
    atr DECIMAL(10, 2),                   -- ATR for volatility-based stops
    correction_pct DECIMAL(5, 1),         -- % below 52-week high

    -- Volume
    volume_ratio DECIMAL(5, 2),           -- Current vs avg volume
    volume_spike BOOLEAN DEFAULT FALSE,   -- Volume > 1.5x avg

    -- Fundamentals
    pe_ratio DECIMAL(10, 2),
    roe DECIMAL(5, 1),
    debt_equity DECIMAL(5, 2),

    -- Dynamic Stop Levels (per stock based on volatility)
    stop_pct DECIMAL(5, 1),               -- Stop loss % (e.g., 8.5)
    tp_pct DECIMAL(5, 1),                 -- Take profit % (e.g., 25.5)
    trail_pct DECIMAL(5, 1),              -- Trailing stop distance %
    stop_mode VARCHAR(10) DEFAULT 'atr',  -- 'fixed', 'atr', 'pivot', 'hybrid'
    stop_price DECIMAL(10, 2),            -- Calculated stop price
    tp_price DECIMAL(10, 2),              -- Calculated take profit price

    -- Signal scoring
    signal_score INTEGER,                 -- 0-100
    signal_strength VARCHAR(10),          -- 'strong', 'medium', 'weak'
    signal_factors TEXT[],                -- Array of contributing factors

    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'closed', 'stopped'
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate entries per day
    UNIQUE(ticker, pick_date)
);

-- Indexes for fast queries
CREATE INDEX idx_picks_date ON screener_picks(pick_date DESC);
CREATE INDEX idx_picks_ticker ON screener_picks(ticker);
CREATE INDEX idx_picks_status ON screener_picks(status);
CREATE INDEX idx_picks_score ON screener_picks(signal_score DESC);
CREATE INDEX idx_picks_strength ON screener_picks(signal_strength);

-- =============================================================================
-- VIX HISTORY TABLE
-- =============================================================================
DROP TABLE IF EXISTS vix_history CASCADE;

CREATE TABLE vix_history (
    date DATE PRIMARY KEY,
    close_value DECIMAL(6, 2) NOT NULL,
    is_buy_zone BOOLEAN DEFAULT FALSE  -- VIX 20-35
);

-- =============================================================================
-- SCREENER RUNS LOG
-- =============================================================================
DROP TABLE IF EXISTS screener_runs CASCADE;

CREATE TABLE screener_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    run_date TIMESTAMPTZ DEFAULT NOW(),
    vix_value DECIMAL(5, 1),
    signals_found INTEGER,
    tickers_scanned INTEGER,
    duration_ms INTEGER,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT
);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Active picks sorted by score
CREATE OR REPLACE VIEW active_picks AS
SELECT
    ticker,
    company_name,
    pick_date,
    entry_price,
    current_price,
    CASE
        WHEN current_price IS NOT NULL
        THEN ROUND(((current_price - entry_price) / entry_price * 100)::numeric, 2)
        ELSE NULL
    END as unrealized_pct,
    rsi,
    adx,
    atr,
    correction_pct,
    volume_ratio,
    pe_ratio,
    -- Dynamic stop info
    stop_pct,
    tp_pct,
    trail_pct,
    stop_mode,
    stop_price,
    tp_price,
    signal_score,
    signal_strength,
    signal_factors
FROM screener_picks
WHERE status = 'active'
ORDER BY signal_score DESC, pick_date DESC;

-- Closed trades with P&L
CREATE OR REPLACE VIEW closed_trades AS
SELECT
    ticker,
    company_name,
    pick_date,
    exit_date,
    entry_price,
    exit_price,
    gain_loss_pct,
    signal_strength,
    signal_score,
    CASE WHEN gain_loss_pct > 0 THEN TRUE ELSE FALSE END as is_winner
FROM screener_picks
WHERE status = 'closed'
ORDER BY exit_date DESC;

-- Performance summary
CREATE OR REPLACE VIEW performance_summary AS
SELECT
    COUNT(*) as total_trades,
    COUNT(*) FILTER (WHERE status = 'active') as active_trades,
    COUNT(*) FILTER (WHERE status = 'closed') as closed_trades,
    ROUND(AVG(gain_loss_pct) FILTER (WHERE status = 'closed'), 2) as avg_return,
    ROUND(
        (COUNT(*) FILTER (WHERE status = 'closed' AND gain_loss_pct > 0)::numeric /
         NULLIF(COUNT(*) FILTER (WHERE status = 'closed'), 0) * 100), 1
    ) as win_rate,
    SUM(gain_loss_pct) FILTER (WHERE status = 'closed') as total_return
FROM screener_picks;

-- Performance by signal strength
CREATE OR REPLACE VIEW performance_by_strength AS
SELECT
    signal_strength,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'closed') as closed,
    ROUND(AVG(gain_loss_pct) FILTER (WHERE status = 'closed'), 2) as avg_return,
    ROUND(
        (COUNT(*) FILTER (WHERE status = 'closed' AND gain_loss_pct > 0)::numeric /
         NULLIF(COUNT(*) FILTER (WHERE status = 'closed'), 0) * 100), 1
    ) as win_rate
FROM screener_picks
GROUP BY signal_strength
ORDER BY
    CASE signal_strength
        WHEN 'strong' THEN 1
        WHEN 'medium' THEN 2
        ELSE 3
    END;

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE screener_picks ENABLE ROW LEVEL SECURITY;
ALTER TABLE vix_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE screener_runs ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Public read" ON screener_picks FOR SELECT USING (true);
CREATE POLICY "Public read" ON vix_history FOR SELECT USING (true);
CREATE POLICY "Public read" ON screener_runs FOR SELECT USING (true);

-- Service role can write
CREATE POLICY "Service write" ON screener_picks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service write" ON vix_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service write" ON screener_runs FOR ALL USING (true) WITH CHECK (true);

-- =============================================================================
-- FUNCTION: Update modified timestamp
-- =============================================================================
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_screener_picks_modtime
    BEFORE UPDATE ON screener_picks
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- =============================================================================
-- FUNCTION: Get performance stats
-- =============================================================================
CREATE OR REPLACE FUNCTION get_performance_stats()
RETURNS TABLE (
    total_signals BIGINT,
    active_count BIGINT,
    closed_count BIGINT,
    win_rate DECIMAL,
    avg_return DECIMAL,
    total_pnl DECIMAL,
    strong_win_rate DECIMAL,
    medium_win_rate DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE status = 'active')::BIGINT,
        COUNT(*) FILTER (WHERE status = 'closed')::BIGINT,
        ROUND(
            (COUNT(*) FILTER (WHERE status = 'closed' AND gain_loss_pct > 0)::numeric /
             NULLIF(COUNT(*) FILTER (WHERE status = 'closed'), 0) * 100), 1
        ),
        ROUND(AVG(gain_loss_pct) FILTER (WHERE status = 'closed'), 2),
        ROUND(SUM(gain_loss_pct) FILTER (WHERE status = 'closed'), 2),
        ROUND(
            (COUNT(*) FILTER (WHERE status = 'closed' AND gain_loss_pct > 0 AND signal_strength = 'strong')::numeric /
             NULLIF(COUNT(*) FILTER (WHERE status = 'closed' AND signal_strength = 'strong'), 0) * 100), 1
        ),
        ROUND(
            (COUNT(*) FILTER (WHERE status = 'closed' AND gain_loss_pct > 0 AND signal_strength = 'medium')::numeric /
             NULLIF(COUNT(*) FILTER (WHERE status = 'closed' AND signal_strength = 'medium'), 0) * 100), 1
        )
    FROM screener_picks;
END;
$$ LANGUAGE plpgsql;
