# Market Sniper - Supabase + Vercel Integration Guide

This guide shows how to integrate the Market Sniper screener into your Next.js app on Vercel with Supabase as the database.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Python Worker  │────▶│    Supabase     │◀────│  Next.js App    │
│  (GitHub Actions│     │  (PostgreSQL)   │     │  (Vercel)       │
│   runs daily)   │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Setup Steps

### 1. Supabase Setup

1. Create a new Supabase project at [supabase.com](https://supabase.com)

2. Go to SQL Editor and run the schema:
   ```sql
   -- Copy contents of supabase/schema.sql and run it
   ```

3. Get your credentials from Settings > API:
   - `SUPABASE_URL` - Your project URL
   - `SUPABASE_ANON_KEY` - Public anon key (for client)
   - `SUPABASE_SERVICE_KEY` - Service role key (for worker)

### 2. GitHub Actions Setup

1. In your GitHub repo, go to Settings > Secrets > Actions

2. Add these secrets:
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_SERVICE_KEY` - Service role key

3. The workflow file `.github/workflows/screener.yml` will:
   - Run daily at 4 PM EST (after market close)
   - Scan for new signals
   - Push to Supabase

### 3. Next.js App Setup

1. Install Supabase client:
   ```bash
   npm install @supabase/supabase-js
   ```

2. Add environment variables to your `.env.local`:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   ```

3. Copy these files to your Next.js app:
   ```
   app/
   ├── api/
   │   ├── signals/route.ts
   │   ├── top-picks/route.ts
   │   └── stats/route.ts
   ├── components/
   │   ├── SignalCard.tsx
   │   ├── SignalsList.tsx
   │   ├── PerformanceStats.tsx
   │   ├── TopPicks.tsx
   │   └── index.ts
   ├── lib/
   │   └── supabase.ts
   └── types/
       └── signal.ts
   ```

4. Update import paths if your project structure differs.

### 4. Vercel Deployment

1. Push to GitHub
2. Connect repo to Vercel
3. Add environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Usage in Your App

### Display Top Picks on Homepage

```tsx
import { TopPicks } from '@/components';

export default function HomePage() {
  return (
    <div>
      <h1>Market Sniper</h1>
      <TopPicks limit={6} minScore={8} />
    </div>
  );
}
```

### Full Signals Page

```tsx
import { SignalsList, PerformanceStats } from '@/components';

export default function SignalsPage() {
  return (
    <div className="space-y-8">
      <h1>All Signals</h1>
      <PerformanceStats />
      <SignalsList showBacktest={true} />
    </div>
  );
}
```

### Single Signal Card

```tsx
import { SignalCard } from '@/components';

// Use with a signal object
<SignalCard signal={mySignal} showBacktest={false} />
```

## API Endpoints

### GET /api/signals

Query params:
- `limit` (default: 50)
- `offset` (default: 0)
- `sector` (filter by sector)
- `status` (active/closed/all)
- `minScore` (min quality score)
- `days` (lookback days)

### GET /api/top-picks

Query params:
- `limit` (default: 10)
- `minScore` (default: 8)
- `days` (default: 90)

### GET /api/stats

Returns overall performance and sector breakdown.

## Customization

### Adjust Screener Parameters

Edit `worker/screener_worker.py`:
- `VIX_MIN` / `VIX_MAX` - Market fear range
- `MIN_BELOW_HIGH_PCT` / `MAX_BELOW_HIGH_PCT` - Price correction range
- `ADX_MIN` - Trend strength
- Fundamental thresholds (`MAX_PE_RATIO`, `MIN_ROE`, etc.)

### Styling

Components use Tailwind CSS. Customize classes or replace with your design system.

## Manual Backfill

To backfill historical data:

1. Run `screener_showcase.py` in Colab
2. Export `showcase_results.csv`
3. Import to Supabase:

```sql
-- In Supabase SQL Editor
COPY signals(ticker, signal_date, entry_price, ...)
FROM '/path/to/showcase_results.csv'
WITH (FORMAT csv, HEADER true);
```

Or use the Supabase dashboard to import CSV.

## Troubleshooting

### No signals appearing
- Check GitHub Actions logs for errors
- Verify Supabase credentials
- Check VIX is in range (20-50)

### Worker timeout
- GitHub Actions has 6-hour limit
- Current worker takes ~6 minutes for ~600 tickers

### Rate limiting
- yfinance may throttle requests
- Worker has built-in delays
- If issues persist, reduce ticker list
