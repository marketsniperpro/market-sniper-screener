'use client';

import { useState, useEffect } from 'react';
import { PerformanceStats as Stats, SectorPerformance, StatsResponse } from '@/types/signal';

export function PerformanceStats() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [sectors, setSectors] = useState<SectorPerformance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch('/api/stats');
        const data: StatsResponse = await res.json();
        setStats(data.stats);
        setSectors(data.sectors);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-gray-200 dark:bg-gray-700 h-24 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Main Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard
          label="Total Signals"
          value={stats.total_signals.toLocaleString()}
        />
        <StatCard
          label="Win Rate"
          value={`${stats.win_rate}%`}
          color={stats.win_rate >= 60 ? 'green' : stats.win_rate >= 50 ? 'yellow' : 'red'}
        />
        <StatCard
          label="Avg Return"
          value={`${stats.avg_return > 0 ? '+' : ''}${stats.avg_return}%`}
          color={stats.avg_return > 0 ? 'green' : 'red'}
        />
        <StatCard
          label="Total P&L"
          value={`$${stats.total_pnl.toLocaleString()}`}
          color={stats.total_pnl > 0 ? 'green' : 'red'}
        />
        <StatCard
          label="Profit Factor"
          value={stats.profit_factor.toFixed(2)}
          color={stats.profit_factor >= 2 ? 'green' : stats.profit_factor >= 1.5 ? 'yellow' : 'red'}
        />
      </div>

      {/* Sector Performance */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Performance by Sector
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Sector
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Trades
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Win Rate
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Avg Return
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  P&L
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  Quality
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {sectors.map((sector) => (
                <tr key={sector.sector} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                    {sector.sector}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-300">
                    {sector.total_trades}
                  </td>
                  <td className={`px-4 py-3 text-sm text-right font-medium ${
                    sector.win_rate >= 60 ? 'text-green-600' :
                    sector.win_rate >= 50 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {sector.win_rate}%
                  </td>
                  <td className={`px-4 py-3 text-sm text-right font-medium ${
                    sector.avg_return > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {sector.avg_return > 0 ? '+' : ''}{sector.avg_return}%
                  </td>
                  <td className={`px-4 py-3 text-sm text-right font-medium ${
                    sector.total_pnl > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    ${sector.total_pnl.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-300">
                    {sector.avg_fund_score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  color?: 'green' | 'yellow' | 'red' | 'default';
}

function StatCard({ label, value, color = 'default' }: StatCardProps) {
  const colorClasses = {
    green: 'text-green-600 dark:text-green-400',
    yellow: 'text-yellow-600 dark:text-yellow-400',
    red: 'text-red-600 dark:text-red-400',
    default: 'text-gray-900 dark:text-white',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</p>
    </div>
  );
}
