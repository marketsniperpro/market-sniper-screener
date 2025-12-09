'use client';

import { Signal } from '@/types/signal';

interface SignalCardProps {
  signal: Signal;
  showBacktest?: boolean;
}

export function SignalCard({ signal, showBacktest = false }: SignalCardProps) {
  const isWinner = signal.return_pct !== null && signal.return_pct > 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">
            {signal.ticker}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {signal.sector}
          </p>
        </div>
        <div className="text-right">
          <div className="text-lg font-semibold text-gray-900 dark:text-white">
            ${signal.entry_price.toFixed(2)}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {new Date(signal.signal_date).toLocaleDateString()}
          </div>
        </div>
      </div>

      {/* Quality Score */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm text-gray-600 dark:text-gray-300">Quality:</span>
        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="bg-green-500 h-2 rounded-full"
            style={{ width: `${(signal.fund_score / 18) * 100}%` }}
          />
        </div>
        <span className="text-sm font-medium text-gray-900 dark:text-white">
          {signal.fund_score}/18
        </span>
      </div>

      {/* Fundamentals Grid */}
      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        {signal.pe_ratio && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">P/E:</span>
            <span className={`font-medium ${signal.pe_ratio < 20 ? 'text-green-600' : 'text-gray-900 dark:text-white'}`}>
              {signal.pe_ratio.toFixed(1)}
            </span>
          </div>
        )}
        {signal.roe && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">ROE:</span>
            <span className={`font-medium ${signal.roe > 15 ? 'text-green-600' : 'text-gray-900 dark:text-white'}`}>
              {signal.roe.toFixed(0)}%
            </span>
          </div>
        )}
        {signal.peg_ratio && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">PEG:</span>
            <span className={`font-medium ${signal.peg_ratio < 1 ? 'text-green-600' : 'text-gray-900 dark:text-white'}`}>
              {signal.peg_ratio.toFixed(2)}
            </span>
          </div>
        )}
        {signal.debt_equity && (
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">D/E:</span>
            <span className={`font-medium ${signal.debt_equity < 0.5 ? 'text-green-600' : 'text-gray-900 dark:text-white'}`}>
              {signal.debt_equity.toFixed(2)}
            </span>
          </div>
        )}
      </div>

      {/* Technical Indicators */}
      <div className="flex gap-3 text-xs text-gray-500 dark:text-gray-400 mb-3">
        {signal.vix && <span>VIX: {signal.vix}</span>}
        {signal.rsi && <span>RSI: {signal.rsi}</span>}
        {signal.adx && <span>ADX: {signal.adx}</span>}
      </div>

      {/* Backtest Results (optional) */}
      {showBacktest && signal.return_pct !== null && (
        <div className={`mt-3 pt-3 border-t border-gray-200 dark:border-gray-700`}>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Result ({signal.exit_reason}):
            </span>
            <span className={`font-bold ${isWinner ? 'text-green-600' : 'text-red-600'}`}>
              {signal.return_pct > 0 ? '+' : ''}{signal.return_pct.toFixed(1)}%
            </span>
          </div>
        </div>
      )}

      {/* Status Badge */}
      <div className="mt-3 flex justify-end">
        <span className={`px-2 py-1 text-xs rounded-full ${
          signal.status === 'active'
            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
            : signal.is_winner
            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
            : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
        }`}>
          {signal.status === 'active' ? 'Active' : isWinner ? 'Winner' : 'Stopped'}
        </span>
      </div>
    </div>
  );
}
