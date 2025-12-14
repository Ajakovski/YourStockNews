import React from 'react';
import { ArticleStats } from '../../types';

interface StatsCardsProps {
  stats: ArticleStats | null;
}

export function StatsCards({ stats }: StatsCardsProps) {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
        <div className="text-3xl font-bold text-gray-900">{stats.total}</div>
        <div className="text-sm text-gray-500 mt-1">Total Alerts</div>
      </div>
      <div className="bg-red-50 rounded-xl shadow-sm p-6 border border-red-200">
        <div className="text-3xl font-bold text-red-600">{stats.high}</div>
        <div className="text-sm text-red-700 mt-1">High Severity</div>
      </div>
      <div className="bg-yellow-50 rounded-xl shadow-sm p-6 border border-yellow-200">
        <div className="text-3xl font-bold text-yellow-600">{stats.med}</div>
        <div className="text-sm text-yellow-700 mt-1">Medium Severity</div>
      </div>
      <div className="bg-blue-50 rounded-xl shadow-sm p-6 border border-blue-200">
        <div className="text-3xl font-bold text-blue-600">{stats.unread}</div>
        <div className="text-sm text-blue-700 mt-1">Unread</div>
      </div>
    </div>
  );
}