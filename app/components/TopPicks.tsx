'use client';

import { useState, useEffect } from 'react';
import { Signal, TopPicksResponse } from '@/types/signal';
import { SignalCard } from './SignalCard';

interface TopPicksProps {
  limit?: number;
  minScore?: number;
}

export function TopPicks({ limit = 6, minScore = 8 }: TopPicksProps) {
  const [picks, setPicks] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTopPicks() {
      try {
        const params = new URLSearchParams({
          limit: limit.toString(),
          minScore: minScore.toString(),
        });

        const res = await fetch(`/api/top-picks?${params}`);
        const data: TopPicksResponse = await res.json();
        setPicks(data.picks);
      } catch (err) {
        console.error('Failed to fetch top picks:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchTopPicks();
  }, [limit, minScore]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(limit)].map((_, i) => (
          <div key={i} className="bg-gray-200 dark:bg-gray-700 h-64 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (picks.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        No high-quality picks available at the moment
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          Top Picks
        </h2>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          Quality Score {minScore}+
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {picks.map((pick) => (
          <SignalCard
            key={pick.id}
            signal={pick}
            showBacktest={true}
          />
        ))}
      </div>
    </div>
  );
}
