import React, { useState, useEffect, useCallback } from 'react';
import { OpenRankingItem } from '../../types';
import { opensApi, ApiError } from '../../api/client';
import { Trophy, AlertCircle, RefreshCw } from 'lucide-react';

interface RankingLeaderboardProps {
  challengeId: string;
}

export const RankingLeaderboard: React.FC<RankingLeaderboardProps> = ({ challengeId }) => {
  const [rankings, setRankings] = useState<OpenRankingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRankings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opensApi.getRanking(challengeId);
      setRankings(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load rankings');
    } finally {
      setLoading(false);
    }
  }, [challengeId]);

  useEffect(() => {
    loadRankings();
  }, [loadRankings]);

  const getRankBadge = (rank: number) => {
    if (rank === 1) {
      return (
        <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-amber-400 to-yellow-200 text-black font-bold text-xs flex items-center justify-center shadow-md shadow-amber-500/30">
          🥇
        </div>
      );
    }
    if (rank === 2) {
      return (
        <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-slate-300 to-slate-100 text-black font-bold text-xs flex items-center justify-center shadow-md">
          🥈
        </div>
      );
    }
    if (rank === 3) {
      return (
        <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-amber-700 to-amber-600 text-white font-bold text-xs flex items-center justify-center shadow-md">
          🥉
        </div>
      );
    }
    return (
      <span className="w-6 text-center font-mono font-bold text-xs text-spreego-text-secondary">
        #{rank}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="py-12 flex flex-col items-center justify-center space-y-2">
        <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-spreego-text-secondary">Computing live scores...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-center space-y-2">
        <div className="flex items-center justify-center space-x-1.5 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-400" />
          <span>{error}</span>
        </div>
        <button
          onClick={loadRankings}
          className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-white text-xs font-semibold mx-auto"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Retry Leaderboard</span>
        </button>
      </div>
    );
  }

  if (rankings.length === 0) {
    return (
      <div className="p-8 rounded-2xl bg-spreego-surface border border-white/5 text-center space-y-2">
        <Trophy className="w-8 h-8 text-spreego-champagne mx-auto opacity-50" />
        <h4 className="text-xs font-bold text-white">No Rankings Yet</h4>
        <p className="text-xs text-spreego-text-secondary">
          Submissions are dynamically scored based on views, claps, and completion rate.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col space-y-3">
      {/* Dynamic Scoring Header */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-bold text-white uppercase tracking-wider">
          Live Standings ({rankings.length})
        </span>
        <span className="text-[10px] text-spreego-champagne font-mono">
          ⚡ Dynamically Scored
        </span>
      </div>

      {/* Leaderboard Table List */}
      <div className="bg-spreego-surface rounded-2xl border border-white/5 divide-y divide-white/5 overflow-hidden">
        {rankings.map((item) => {
          const displayName =
            item.creator?.full_name || item.creator?.username || item.username || `User ${item.user_id.slice(0, 8)}`;
          const handle =
            item.creator?.username ? `@${item.creator.username}` : item.handle || `@user_${item.user_id.slice(0, 6)}`;
          const avatarUrl =
            item.creator?.avatar_url || item.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150';
          const title = item.spree_title || item.spree?.title || 'Submitted Spree';

          return (
            <div
              key={item.submission_id || `${item.user_id}-${item.rank}`}
              className={`px-3.5 py-3 flex items-center justify-between transition-colors ${
                item.rank === 1 ? 'bg-amber-500/5' : 'hover:bg-white/5'
              }`}
            >
              {/* Left Rank & User */}
              <div className="flex items-center space-x-3 min-w-0">
                {getRankBadge(item.rank)}
                <img
                  src={avatarUrl}
                  alt={displayName}
                  className="w-9 h-9 rounded-full object-cover border border-white/10 shrink-0"
                />
                <div className="min-w-0">
                  <span className="text-xs font-bold text-white block truncate">
                    {displayName}
                  </span>
                  <span className="text-[10px] text-spreego-text-secondary block font-mono truncate">
                    {handle} • {title}
                  </span>
                </div>
              </div>

              {/* Right Score & Metrics */}
              <div className="text-right shrink-0 ml-3">
                <span className="font-mono font-extrabold text-xs text-spreego-champagne block">
                  {Math.round(item.score).toLocaleString()} pts
                </span>
                {item.metrics && (
                  <span className="text-[9px] text-spreego-text-secondary block font-mono">
                    👁 {item.metrics.views_count} | 👏 {item.metrics.claps_count}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
