import React from 'react';
import { Watchlist } from '../../types';

interface WatchlistSelectorProps {
  watchlists: Watchlist[];
  selectedWatchlist: number | null;
  onSelect: (id: number) => void;
  onCreateNew: () => void;
  onScan: () => void;
  scanning: boolean;
}

export function WatchlistSelector({
  watchlists,
  selectedWatchlist,
  onSelect,
  onCreateNew,
  onScan,
  scanning
}: WatchlistSelectorProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">Watchlist:</label>
          <select
            value={selectedWatchlist || ''}
            onChange={(e) => onSelect(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            {watchlists.map(wl => (
              <option key={wl.id} value={wl.id}>
                {wl.name} ({wl.tickers.length} tickers)
              </option>
            ))}
          </select>
          <button
            onClick={onCreateNew}
            className="px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition"
          >
            + New Watchlist
          </button>
        </div>
        <button
          onClick={onScan}
          disabled={scanning || !selectedWatchlist}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50"
        >
          {scanning ? 'Scanning...' : '🔍 Scan Now'}
        </button>
      </div>
    </div>
  );
}