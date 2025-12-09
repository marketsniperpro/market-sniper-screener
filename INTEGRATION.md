# Market Sniper - Supabase Integration Guide

Complete guide to deploy the VIX-based stock screener to your Supabase project.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Supabase Edge  │────▶│    Supabase     │◀────│  Next.js App    │
│    Function     │     │  (PostgreSQL)   │     │  (Vercel)       │
│  (runs on-demand│     │                 │     │                 │
│   or scheduled) │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Files to Deploy

```
supabase/
├── schema.sql                      # Run in SQL Editor
└── functions/
    └── stock-screener/
        └── index.ts                # Deploy as Edge Function

app/
└── portal/
    └── screener/
        └── page.tsx                # Copy to your Next.js app
```

## Step 1: Database Setup

1. Go to your Supabase project > **SQL Editor**

2. Run the schema (this will replace any existing `screener_picks` table):

```sql
-- Full schema in supabase/schema.sql
-- Key parts:

DROP TABLE IF EXISTS screener_picks CASCADE;

CREATE TABLE screener_picks (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR(10) NOT NULL,
  pick_date DATE NOT NULL,
  entry_price DECIMAL(10,2),
  current_price DECIMAL(10,2),

  -- VIX Strategy Fields
  vix DECIMAL(5,2),
  rsi DECIMAL(5,2),
  adx DECIMAL(5,2),
  correction_pct DECIMAL(5,2),
  volume_ratio DECIMAL(5,2),
  pe_ratio DECIMAL(10,2),

  -- Signal Scoring
  signal_score INTEGER CHECK (signal_score >= 0 AND signal_score <= 100),
  signal_strength VARCHAR(10) CHECK (signal_strength IN ('Strong', 'Medium', 'Weak')),
  signal_factors TEXT[],

  -- Exit Tracking
  exit_date DATE,
  exit_price DECIMAL(10,2),
  exit_reason VARCHAR(20),
  return_pct DECIMAL(8,2),

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(ticker, pick_date)
);

-- Creates views: active_picks, closed_trades, performance_summary
-- Creates function: get_performance_stats()
```

3. Verify tables created:
   - Go to **Table Editor**
   - You should see `screener_picks` table
   - Check views in **Database > Views**

## Step 2: Deploy Edge Function

### Option A: Supabase CLI (Recommended)

```bash
# Install Supabase CLI if needed
npm install -g supabase

# Login
supabase login

# Link to your project
supabase link --project-ref YOUR_PROJECT_REF

# Deploy the function
supabase functions deploy stock-screener
```

### Option B: Manual Upload

1. Go to Supabase Dashboard > **Edge Functions**
2. Click **New Function**
3. Name: `stock-screener`
4. Copy contents of `supabase/functions/stock-screener/index.ts`
5. Click **Deploy**

### Verify Deployment

```bash
# Test the function
curl "https://YOUR_PROJECT.supabase.co/functions/v1/stock-screener" \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Should return: {"status": "ok", "vix": 22.5, "inBuyZone": true, ...}
```

## Step 3: Next.js App Setup

### Copy the Page Component

Copy `app/portal/screener/page.tsx` to your Next.js app at the same path.

### Required Dependencies

```bash
npm install @supabase/supabase-js
```

### Environment Variables

Add to `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### Supabase Client

Create `lib/supabase.ts` if it doesn't exist:

```typescript
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

## Step 4: Test the Integration

1. Start your Next.js app: `npm run dev`
2. Navigate to `/portal/screener`
3. You should see:
   - VIX status badge (BUY ZONE or WAIT)
   - Empty table (no picks yet)
4. Click **Refresh Screener** to trigger a scan
5. If VIX is in range (20-35), you'll see new picks

## Edge Function API

### GET /functions/v1/stock-screener

Returns current VIX status and recent picks.

**Response:**
```json
{
  "status": "ok",
  "vix": 24.5,
  "inBuyZone": true,
  "message": "VIX in buy zone (20-35)"
}
```

### GET /functions/v1/stock-screener?mode=scan

Runs a full scan and saves picks to database.

**Response:**
```json
{
  "status": "ok",
  "vix": 24.5,
  "inBuyZone": true,
  "picksFound": 5,
  "picksSaved": 5,
  "message": "Scan complete"
}
```

### Configuration in Edge Function

Edit `index.ts` to adjust parameters:

```typescript
const CONFIG = {
  VIX_MIN: 20,           // Minimum VIX for buy zone
  VIX_MAX: 35,           // Maximum VIX (crash protection)
  RSI_SIGNAL: 45,        // RSI crossover threshold
  ADX_MIN: 18,           // Minimum trend strength
  MIN_CORRECTION: 25,    // Min % below 52-week high
  MAX_CORRECTION: 50,    // Max % below high
  VOLUME_RATIO: 1.3,     // Min volume vs 50-day avg
  MAX_PE: 30,            // Maximum P/E ratio
  MIN_ROE: 8,            // Minimum ROE %
  MAX_DEBT_EQUITY: 2.0   // Maximum D/E ratio
}
```

## Automated Scanning (Optional)

### Option 1: Supabase Cron (pg_cron)

```sql
-- Run daily at 4:30 PM EST (21:30 UTC)
SELECT cron.schedule(
  'daily-screener-scan',
  '30 21 * * 1-5',  -- Mon-Fri at 9:30 PM UTC
  $$
  SELECT net.http_post(
    'https://YOUR_PROJECT.supabase.co/functions/v1/stock-screener?mode=scan',
    '{}',
    'application/json',
    ARRAY[http_header('Authorization', 'Bearer ' || current_setting('app.settings.service_role_key'))]
  );
  $$
);
```

### Option 2: GitHub Actions

Use `.github/workflows/screener.yml` with the Python worker for more comprehensive scanning.

```yaml
name: Daily Screener
on:
  schedule:
    - cron: '30 21 * * 1-5'  # 4:30 PM EST
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install pandas numpy yfinance requests
      - run: python worker/screener_worker.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
```

## Page Component Features

The React component (`app/portal/screener/page.tsx`) includes:

### VIX Status Display
- Green badge: "BUY ZONE (20-35)" when VIX is optimal
- Yellow badge: "WAIT" when VIX is outside range
- Shows current VIX value

### Picks Table
| Column | Description |
|--------|-------------|
| Ticker | Stock symbol (links to chart) |
| Date | Signal date |
| Entry | Entry price |
| Return | Current return % |
| VIX | VIX at entry |
| RSI | RSI value |
| ADX | Trend strength |
| Correction | % below 52-week high |
| Volume | Volume ratio vs average |
| P/E | Price-to-earnings ratio |
| Score | Signal score (0-100) |
| Strength | Strong/Medium badge |

### Actions
- **Refresh Screener**: Triggers new scan via Edge Function
- **View**: Opens stock on external chart site

## Troubleshooting

### "VIX outside buy zone"
- Normal - screener only finds picks when VIX is 20-35
- Check current VIX at https://finance.yahoo.com/quote/%5EVIX

### No picks appearing after scan
- VIX may be outside range
- Market conditions may not meet criteria
- Check Edge Function logs in Supabase dashboard

### Edge Function timeout
- Default 60 second limit
- Reduce ticker count in `TICKERS` array if needed
- Or use GitHub Actions worker for comprehensive scans

### CORS errors
- Ensure your app domain is in Supabase allowed origins
- Go to **Authentication > URL Configuration**

## Database Views

### active_picks
Shows all open positions (no exit_date):
```sql
SELECT * FROM active_picks ORDER BY pick_date DESC;
```

### closed_trades
Shows completed trades with returns:
```sql
SELECT * FROM closed_trades ORDER BY exit_date DESC;
```

### performance_summary
Aggregated stats:
```sql
SELECT * FROM performance_summary;
-- Returns: total_trades, wins, losses, win_rate, total_return, avg_return
```
