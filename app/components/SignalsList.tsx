'use client';

import { useState, useEffect } from 'react';
import { Signal, SignalsResponse } from '@/types/signal';
import { SignalCard } from './SignalCard';

interface SignalsListProps {
  initialSignals?: Signal[];
  showBacktest?: boolean;
}

const SECTORS = [
  'all',
  'Technology',
  'Financial Services',
  'Healthcare',
  'Consumer Cyclical',
  'Industrials',
  'Energy',
  'Consumer Defensive',
  'Utilities',
  'Real Estate',
  'Basic Materials',
  'Communication Services',
];

export function SignalsList({ initialSignals, showBacktest = false }: SignalsListProps) {
  const [signals, setSignals] = useState<Signal[]>(initialSignals || []);
  const [loading, setLoading] = useState(!initialSignals);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [sector, setSector] = useState('all');
  const [minScore, setMinScore] = useState(0);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchSignals();
  }, [sector, minScore, days]);

  async function fetchSignals() {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        sector,
        minScore: minScore.toString(),
        days: days.toString(),
        limit: '50',
      });

      const res = await fetch(`/api/signals?${params}`);
      if (!res.ok) throw new Error('Failed to fetch signals');

      const data: SignalsResponse = await res.json();
      setSignals(data.signals);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4">
          {/* Sector Filter */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Sector
            </label>
            <select
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-gray-900 dark:text-white"
            >
              {SECTORS.map((s) => (
                <option key={s} value={s}>
                  {s === 'all' ? 'All Sectors' : s}
                </option>
              ))}
            </select>
          </div>

          {/* Quality Score Filter */}
          <div className="w-40">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Min Quality Score
            </label>
            <select
              value={minScore}
              onChange={(e) => setMinScore(parseInt(e.target.value))}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-gray-900 dark:text-white"
            >
              <option value={0}>Any</option>
              <option value={5}>5+ (Good)</option>
              <option value={8}>8+ (High)</option>
              <option value={10}>10+ (Premium)</option>
            </select>
          </div>

          {/* Days Filter */}
          <div className="w-40">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Time Range
            </label>
            <select
              value={days}
              onChange={(e) => setDays(parseInt(e.target.value))}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-gray-900 dark:text-white"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
              <option value={365}>Last year</option>
              <option value={9999}>All time</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {signals.length} signals found
        </p>
        <button
          onClick={fetchSignals}
          className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
        >
          Refresh
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      {/* Signals Grid */}
      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {signals.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              showBacktest={showBacktest}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && signals.length === 0 && (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No signals found matching your filters
        </div>
      )}
    </div>
  );
}
