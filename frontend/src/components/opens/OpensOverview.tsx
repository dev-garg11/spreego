import React, { useState, useEffect, useCallback } from 'react';
import { Open, OpenType } from '../../types';
import { opensApi, ApiError } from '../../api/client';
import { ChallengeDetails } from './ChallengeDetails';
import { BrandSponsorship } from './BrandSponsorship';
import { Clock, Sparkles, Plus, AlertCircle, RefreshCw } from 'lucide-react';

function getDaysLeft(endAt: string): number {
  const end = new Date(endAt).getTime();
  const now = Date.now();
  return Math.max(0, Math.ceil((end - now) / (1000 * 60 * 60 * 24)));
}

export const OpensOverview: React.FC = () => {
  const [selectedType, setSelectedType] = useState<OpenType>('CHALLENGE');
  const [opens, setOpens] = useState<Open[]>([]);
  const [selectedChallengeId, setSelectedChallengeId] = useState<string | null>(null);
  const [showSponsorship, setShowSponsorship] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [newTitle, setNewTitle] = useState('');
  const [newType, setNewType] = useState<OpenType>('CHALLENGE');
  const [newDesc, setNewDesc] = useState('');
  const [newCover, setNewCover] = useState('');
  const [newRules, setNewRules] = useState('');
  const [newReward, setNewReward] = useState('');
  const [newEndAt, setNewEndAt] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const loadOpens = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await opensApi.getOpens({
        type: selectedType,
        status: 'ACTIVE',
      });
      setOpens(items);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to load Opens';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedType]);

  useEffect(() => {
    loadOpens();
  }, [loadOpens]);

  const handleCreateOpen = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (!newTitle.trim()) {
      setCreateError('Title is required');
      return;
    }
    if (!newEndAt) {
      setCreateError('End date is required');
      return;
    }
    const end = new Date(newEndAt);
    if (end <= new Date()) {
      setCreateError('End date must be in the future');
      return;
    }

    setIsCreating(true);
    try {
      const parsedRules = newRules
        .split('\n')
        .map((r) => r.trim())
        .filter(Boolean);

      const created = await opensApi.createOpen({
        title: newTitle.trim(),
        type: newType,
        description: newDesc.trim() || undefined,
        cover_image_url: newCover.trim() || undefined,
        rules: parsedRules.length > 0 ? parsedRules : undefined,
        reward_info: newReward.trim() || undefined,
        end_at: end.toISOString(),
      });

      setShowCreateModal(false);
      // Reset form
      setNewTitle('');
      setNewDesc('');
      setNewCover('');
      setNewRules('');
      setNewReward('');
      setNewEndAt('');
      // Refresh and open details
      await loadOpens();
      setSelectedChallengeId(created.id);
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : 'Failed to create Open');
    } finally {
      setIsCreating(false);
    }
  };

  if (selectedChallengeId) {
    return (
      <ChallengeDetails
        challengeId={selectedChallengeId}
        onBack={() => setSelectedChallengeId(null)}
      />
    );
  }

  if (showSponsorship) {
    return <BrandSponsorship onBack={() => setShowSponsorship(false)} />;
  }

  const heroChallenge = opens[0];

  return (
    <div className="w-full flex-1 flex flex-col space-y-4 pb-12">
      {/* Top Header & Actions */}
      <div className="flex flex-col space-y-3 pt-1">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-extrabold text-xl text-white">Opens</h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center space-x-1 px-3 py-1 rounded-full bg-spreego-violet text-white text-xs font-semibold hover:bg-spreego-violet-light transition-all shadow-sm shadow-spreego-violet/30"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create</span>
            </button>
            <button
              onClick={() => setShowSponsorship(true)}
              className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-spreego-elevated border border-spreego-champagne/30 text-spreego-champagne text-xs font-semibold hover:bg-spreego-surface transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Sponsors</span>
            </button>
          </div>
        </div>

        {/* Mode Toggle (Challenges vs Competitions) */}
        <div className="flex items-center space-x-1 bg-spreego-surface p-1 rounded-2xl border border-white/5">
          <button
            onClick={() => setSelectedType('CHALLENGE')}
            className={`flex-1 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              selectedType === 'CHALLENGE'
                ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                : 'text-spreego-text-secondary hover:text-white'
            }`}
          >
            Challenges
          </button>
          <button
            onClick={() => setSelectedType('COMPETITION')}
            className={`flex-1 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              selectedType === 'COMPETITION'
                ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                : 'text-spreego-text-secondary hover:text-white'
            }`}
          >
            Competitions
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
          <button
            onClick={loadOpens}
            className="flex items-center space-x-1 px-2 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-white font-medium"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Featured Hero Challenge Card */}
      {heroChallenge && !loading && (
        <div
          onClick={() => setSelectedChallengeId(heroChallenge.id)}
          className="group relative rounded-3xl overflow-hidden bg-spreego-surface border border-white/10 p-5 cursor-pointer shadow-xl hover:border-spreego-violet/50 transition-all active:scale-[0.99]"
        >
          {heroChallenge.cover_image_url && (
            <img
              src={heroChallenge.cover_image_url}
              alt={heroChallenge.title}
              className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-black/20" />

          <div className="relative z-10 flex flex-col justify-between h-48">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-spreego-violet/90 text-white backdrop-blur-md">
                {heroChallenge.type}
              </span>
              {heroChallenge.reward_info && (
                <span className="text-xs font-mono font-bold text-spreego-champagne bg-black/60 px-2 py-0.5 rounded-full border border-spreego-champagne/30">
                  💰 {heroChallenge.reward_info}
                </span>
              )}
            </div>

            <div>
              <h3 className="font-display font-extrabold text-2xl text-white drop-shadow">
                {heroChallenge.title}
              </h3>
              {heroChallenge.description && (
                <p className="text-xs text-slate-300 line-clamp-1 mt-1">
                  {heroChallenge.description}
                </p>
              )}
              <div className="mt-2 flex items-center justify-between">
                <span className="text-xs text-slate-200 flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-rose-400" />
                  <span>{getDaysLeft(heroChallenge.end_at)} Days Left</span>
                </span>
                <span className="px-3.5 py-1.5 rounded-xl bg-white text-black font-semibold text-xs shadow-md group-hover:bg-spreego-violet group-hover:text-white transition-colors">
                  View Details
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Active Challenges List */}
      <div className="flex flex-col space-y-2.5">
        <span className="text-xs font-bold text-white uppercase tracking-wider pl-1">
          Active {selectedType === 'CHALLENGE' ? 'Challenges' : 'Competitions'} ({opens.length})
        </span>

        {loading ? (
          <div className="py-12 flex justify-center">
            <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
          </div>
        ) : opens.length === 0 ? (
          <div className="py-12 text-center text-xs text-spreego-text-secondary bg-spreego-surface rounded-2xl border border-white/5 p-6">
            No active {selectedType.toLowerCase()}s found. Be the first to create one!
          </div>
        ) : (
          <div className="space-y-2.5">
            {opens.map((c) => (
              <div
                key={c.id}
                onClick={() => setSelectedChallengeId(c.id)}
                className="p-3 rounded-2xl bg-spreego-surface border border-white/5 hover:border-white/15 cursor-pointer flex items-center justify-between group transition-all"
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-14 h-14 rounded-xl overflow-hidden bg-spreego-elevated border border-white/10 shrink-0">
                    {c.cover_image_url ? (
                      <img
                        src={c.cover_image_url}
                        alt={c.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-spreego-text-secondary text-lg">
                        🏆
                      </div>
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center space-x-1.5">
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-spreego-elevated text-spreego-champagne">
                        {c.reward_info || 'Community'}
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-white mt-1 group-hover:text-spreego-violet-light transition-colors truncate">
                      {c.title}
                    </h4>
                    <div className="flex items-center space-x-3 text-[10px] text-spreego-text-secondary mt-1">
                      <span>👥 {c.participants_count} joined</span>
                      <span>⏱ {getDaysLeft(c.end_at)}d left</span>
                    </div>
                  </div>
                </div>

                <button className="px-3 py-1.5 rounded-xl bg-spreego-elevated group-hover:bg-spreego-violet text-white text-xs font-medium transition-colors shrink-0 ml-2">
                  View
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Open Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-spreego-surface border border-white/10 rounded-3xl p-5 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-base text-white">Create New Open</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-spreego-text-secondary hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {createError && (
              <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateOpen} className="space-y-3">
              <div>
                <label className="text-xs text-spreego-text-secondary block mb-1">Title *</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Summer Fitness Sprint"
                  className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs focus:border-spreego-violet outline-none"
                />
              </div>

              <div>
                <label className="text-xs text-spreego-text-secondary block mb-1">Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as OpenType)}
                  className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs focus:border-spreego-violet outline-none"
                >
                  <option value="CHALLENGE">Challenge</option>
                  <option value="COMPETITION">Competition</option>
                  <option value="SPONSORED">Sponsored</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-spreego-text-secondary block mb-1">Description</label>
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Brief details about the open..."
                  rows={2}
                  className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs focus:border-spreego-violet outline-none"
                />
              </div>

              <div>
                <label className="text-xs text-spreego-text-secondary block mb-1">Cover Image URL</label>
                <input
                  type="url"
                  value={newCover}
                  onChange={(e) => setNewCover(e.target.value)}
                  placeholder="https://images.unsplash.com/..."
                  className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs focus:border-spreego-violet outline-none"
                />
              </div>

              <div>
                <label className="text-xs text-spreego-text-secondary block mb-1">Rules (one per line)</label>
                <textarea
                  value={newRules}
                  onChange={(e) => setNewRules(e.target.value)}
                  placeholder="Rule 1: Must be vertical video&#10;Rule 2: Original sound"
                  rows={2}
                  className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs focus:border-spreego-violet outline-none"
                />
              </div>

              <div>
                <label className="text-xs text-spreego-text-secondary block mb-1">Reward Info</label>
                <input
                  type="text"
                  value={newReward}
                  onChange={(e) => setNewReward(e.target.value)}
                  placeholder="e.g. ₹50,000 Reward Pool"
                  className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs focus:border-spreego-violet outline-none"
                />
              </div>

              <div>
                <label className="text-xs text-spreego-text-secondary block mb-1">End Date &amp; Time *</label>
                <input
                  type="datetime-local"
                  required
                  value={newEndAt}
                  onChange={(e) => setNewEndAt(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs focus:border-spreego-violet outline-none"
                />
              </div>

              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-spreego-text-secondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="px-5 py-2 rounded-xl bg-spreego-violet hover:bg-spreego-violet-light text-white font-semibold text-xs transition-all disabled:opacity-50"
                >
                  {isCreating ? 'Creating...' : 'Create Open'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
