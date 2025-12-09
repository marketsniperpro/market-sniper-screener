// Supabase Edge Function - VIX-Based Stock Screener
// Deploy: supabase functions deploy stock-screener

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Strategy Config
const CONFIG = {
  VIX_MIN: 20,
  VIX_MAX: 35,
  RSI_OVERSOLD: 35,
  RSI_SIGNAL: 45,
  ADX_MIN: 18,
  MIN_BELOW_HIGH_PCT: 20,
  MAX_BELOW_HIGH_PCT: 55,
  MAX_PE_RATIO: 30,
  MIN_ROE: 8,
  MAX_DEBT_EQUITY: 2,
};

// S&P 500 + S&P 400 tickers (fallback - fetched dynamically in scan)
const TICKERS = [
  'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'ADP', 'AMAT', 'AMD', 'AMGN', 'AMZN',
  'AVGO', 'AXP', 'BA', 'BAC', 'BK', 'BKNG', 'BLK', 'BMY', 'BRK-B', 'C',
  'CAT', 'CHTR', 'CL', 'CMCSA', 'COF', 'COP', 'COST', 'CRM', 'CSCO', 'CVS',
  'CVX', 'DE', 'DHR', 'DIS', 'DOW', 'DUK', 'EMR', 'EXC', 'F', 'FDX',
  'GD', 'GE', 'GILD', 'GM', 'GOOG', 'GOOGL', 'GS', 'HD', 'HON', 'IBM',
  'INTC', 'INTU', 'ISRG', 'JNJ', 'JPM', 'KO', 'LIN', 'LLY', 'LMT', 'LOW',
  'MA', 'MCD', 'MDLZ', 'MDT', 'MET', 'META', 'MMM', 'MO', 'MRK', 'MS',
  'MSFT', 'NEE', 'NFLX', 'NKE', 'NOW', 'NVDA', 'ORCL', 'PEP', 'PFE', 'PG',
  'PM', 'PYPL', 'QCOM', 'RTX', 'SBUX', 'SCHW', 'SO', 'SPG', 'T', 'TGT',
  'TMO', 'TMUS', 'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'USB', 'V', 'VZ',
  'WFC', 'WMT', 'XOM', 'DHI', 'LEN', 'PHM', 'TOL', 'KBH', 'NVR', 'MTH',
  'MHO', 'ALLY', 'CFG', 'RF', 'FITB', 'KEY', 'ZION', 'CMA', 'WAL',
  'OXY', 'DVN', 'EOG', 'FANG', 'MPC', 'VLO', 'PSX', 'HAL', 'SLB', 'BKR',
  'FCX', 'NUE', 'STLD', 'CLF', 'X', 'AA', 'RS', 'CMC',
  'DECK', 'CROX', 'SKX', 'UAA', 'RL', 'PVH', 'TPR', 'CPRI',
  'RCL', 'CCL', 'NCLH', 'MAR', 'HLT', 'H', 'WH',
];

interface StockData {
  ticker: string;
  price: number;
  high52w: number;
  rsi: number;
  adx: number;
  volume: number;
  avgVolume: number;
  pe?: number;
  roe?: number;
  debtEquity?: number;
  name?: string;
  sma200w?: number;
}

// Fetch VIX
async function getVIX(): Promise<number | null> {
  try {
    const res = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=5d`
    );
    const data = await res.json();
    const closes = data.chart.result[0].indicators.quote[0].close;
    return closes[closes.length - 1];
  } catch (e) {
    console.error("VIX fetch error:", e);
    return null;
  }
}

// Fetch stock data from Yahoo Finance
async function getStockData(ticker: string): Promise<StockData | null> {
  try {
    // Get quote data
    const quoteRes = await fetch(
      `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${ticker}`
    );
    const quoteData = await quoteRes.json();
    const quote = quoteData.quoteResponse.result[0];

    if (!quote) return null;

    // Get historical for RSI/ADX calculation
    const histRes = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?interval=1d&range=3mo`
    );
    const histData = await histRes.json();
    const result = histData.chart.result?.[0];

    if (!result) return null;

    const closes = result.indicators.quote[0].close.filter((c: number) => c != null);
    const highs = result.indicators.quote[0].high.filter((h: number) => h != null);
    const lows = result.indicators.quote[0].low.filter((l: number) => l != null);
    const volumes = result.indicators.quote[0].volume.filter((v: number) => v != null);

    // Calculate RSI (14-period)
    const rsi = calculateRSI(closes, 14);

    // Calculate ADX (14-period)
    const adx = calculateADX(highs, lows, closes, 14);

    // Average volume (50-day)
    const avgVolume = volumes.slice(-50).reduce((a: number, b: number) => a + b, 0) / 50;

    return {
      ticker,
      price: quote.regularMarketPrice,
      high52w: quote.fiftyTwoWeekHigh,
      rsi,
      adx,
      volume: quote.regularMarketVolume,
      avgVolume,
      pe: quote.forwardPE || quote.trailingPE,
      roe: quote.returnOnEquity ? quote.returnOnEquity * 100 : undefined,
      debtEquity: quote.debtToEquity ? quote.debtToEquity / 100 : undefined,
      name: quote.shortName || quote.longName,
    };
  } catch (e) {
    console.error(`Error fetching ${ticker}:`, e);
    return null;
  }
}

// RSI Calculation
function calculateRSI(closes: number[], period: number): number {
  if (closes.length < period + 1) return 50;

  let gains = 0;
  let losses = 0;

  for (let i = closes.length - period; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    if (change > 0) gains += change;
    else losses -= change;
  }

  const avgGain = gains / period;
  const avgLoss = losses / period;

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

// ADX Calculation (simplified)
function calculateADX(highs: number[], lows: number[], closes: number[], period: number): number {
  if (highs.length < period + 1) return 0;

  let sumDX = 0;
  for (let i = highs.length - period; i < highs.length; i++) {
    const tr = Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1])
    );
    const plusDM = highs[i] - highs[i - 1] > lows[i - 1] - lows[i] ? Math.max(highs[i] - highs[i - 1], 0) : 0;
    const minusDM = lows[i - 1] - lows[i] > highs[i] - highs[i - 1] ? Math.max(lows[i - 1] - lows[i], 0) : 0;

    if (tr > 0) {
      const plusDI = (plusDM / tr) * 100;
      const minusDI = (minusDM / tr) * 100;
      const dx = Math.abs(plusDI - minusDI) / (plusDI + minusDI + 0.001) * 100;
      sumDX += dx;
    }
  }

  return sumDX / period;
}

// Calculate signal score (0-100)
function calculateSignalScore(stock: StockData, vix: number): { score: number; factors: string[] } {
  let score = 0;
  const factors: string[] = [];

  // VIX in sweet spot (25 pts)
  if (vix >= CONFIG.VIX_MIN && vix <= CONFIG.VIX_MAX) {
    score += 25;
    factors.push(`VIX ${vix.toFixed(1)} in buy zone`);
  }

  // RSI recovering from oversold (25 pts)
  if (stock.rsi >= CONFIG.RSI_OVERSOLD && stock.rsi <= CONFIG.RSI_SIGNAL + 10) {
    score += 25;
    factors.push(`RSI ${stock.rsi.toFixed(0)} recovering`);
  } else if (stock.rsi > CONFIG.RSI_SIGNAL + 10 && stock.rsi < 60) {
    score += 15;
    factors.push(`RSI ${stock.rsi.toFixed(0)} bullish`);
  }

  // ADX trending (15 pts)
  if (stock.adx >= CONFIG.ADX_MIN) {
    score += 15;
    factors.push(`ADX ${stock.adx.toFixed(0)} trending`);
  }

  // Correction depth (20 pts)
  const correctionPct = ((stock.high52w - stock.price) / stock.high52w) * 100;
  if (correctionPct >= CONFIG.MIN_BELOW_HIGH_PCT && correctionPct <= CONFIG.MAX_BELOW_HIGH_PCT) {
    score += 20;
    factors.push(`${correctionPct.toFixed(0)}% off highs`);
  }

  // Volume surge (10 pts)
  const volumeRatio = stock.volume / stock.avgVolume;
  if (volumeRatio > 1.2) {
    score += 10;
    factors.push(`Volume ${volumeRatio.toFixed(1)}x avg`);
  }

  // Fundamentals (15 pts)
  if (stock.pe && stock.pe > 0 && stock.pe <= CONFIG.MAX_PE_RATIO) {
    score += 8;
    factors.push(`P/E ${stock.pe.toFixed(1)}`);
  }
  if (stock.roe && stock.roe >= CONFIG.MIN_ROE) {
    score += 7;
    factors.push(`ROE ${stock.roe.toFixed(1)}%`);
  }

  return { score: Math.min(score, 100), factors };
}

// Get signal strength from score
function getSignalStrength(score: number): string {
  if (score >= 75) return 'strong';
  if (score >= 50) return 'medium';
  return 'weak';
}

serve(async (req) => {
  // Handle CORS
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    const mode = url.searchParams.get("mode") || "scan";

    // Initialize Supabase
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Get current VIX
    const vix = await getVIX();
    if (!vix) {
      return new Response(
        JSON.stringify({ error: "Could not fetch VIX" }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 500 }
      );
    }

    console.log(`VIX: ${vix.toFixed(2)}`);

    // Check VIX filter
    if (vix < CONFIG.VIX_MIN || vix > CONFIG.VIX_MAX) {
      return new Response(
        JSON.stringify({
          message: `VIX ${vix.toFixed(1)} outside buy zone (${CONFIG.VIX_MIN}-${CONFIG.VIX_MAX})`,
          vix,
          signals: 0
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const signals: any[] = [];
    const today = new Date().toISOString().split('T')[0];

    // Scan stocks
    for (const ticker of TICKERS) {
      try {
        const stock = await getStockData(ticker);
        if (!stock) continue;

        // Check entry criteria
        const correctionPct = ((stock.high52w - stock.price) / stock.high52w) * 100;

        // RSI recovering from oversold
        if (stock.rsi < CONFIG.RSI_OVERSOLD || stock.rsi > 60) continue;

        // ADX showing trend
        if (stock.adx < CONFIG.ADX_MIN) continue;

        // In correction zone
        if (correctionPct < CONFIG.MIN_BELOW_HIGH_PCT || correctionPct > CONFIG.MAX_BELOW_HIGH_PCT) continue;

        // Calculate score
        const { score, factors } = calculateSignalScore(stock, vix);
        const strength = getSignalStrength(score);

        // Only include medium+ signals
        if (score < 50) continue;

        const volumeRatio = stock.volume / stock.avgVolume;

        signals.push({
          ticker: stock.ticker,
          company_name: stock.name,
          pick_date: today,
          entry_price: stock.price,
          current_price: stock.price,
          rsi: stock.rsi,
          adx: stock.adx,
          correction_pct: correctionPct,
          volume_ratio: volumeRatio,
          volume_spike: volumeRatio > 1.5,
          pe_ratio: stock.pe,
          status: 'active',
          signal_strength: strength,
          signal_score: score,
          signal_factors: factors,
          notes: `VIX: ${vix.toFixed(1)}`,
        });

        // Rate limit
        await new Promise(r => setTimeout(r, 100));

      } catch (e) {
        console.error(`Error processing ${ticker}:`, e);
      }
    }

    console.log(`Found ${signals.length} signals`);

    // Insert signals to database
    if (signals.length > 0) {
      const { error } = await supabase
        .from('screener_picks')
        .upsert(signals, {
          onConflict: 'ticker,pick_date',
          ignoreDuplicates: false
        });

      if (error) {
        console.error("Insert error:", error);
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        vix,
        signals: signals.length,
        picks: signals.map(s => ({
          ticker: s.ticker,
          score: s.signal_score,
          strength: s.signal_strength
        })),
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Error:", error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 500 }
    );
  }
});
