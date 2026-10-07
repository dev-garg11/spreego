import React, { useState, useEffect, useCallback } from 'react';
import { Open, SpreeItem } from '../../types';
import { opensApi, feedApi, ApiError } from '../../api/client';
import { RankingLeaderboard } from './RankingLeaderboard';
import {
  ArrowLeft,
  Share2,
  Users,
  Trophy,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Upload,
  Film,
} from 'lucide-react';

interface ChallengeDetailsProps {
  challengeId: string;
  onBack: () => void;
}

function getDaysLeft(endAt?: string): number {
  if (!endAt) return 0;
  const end = new Date(endAt).getTime();
  const now = Date.now();
  return Math.max(0, Math.ceil((end - now) / (1000 * 60 * 60 * 24)));
}

export const ChallengeDetails: React.FC<ChallengeDetailsProps> = ({ challengeId, onBack }) => {
  const [challenge, setChallenge] = useState<Open | null>(null);
  const [viewTab, setViewTab] = useState<'view' | 'ranking'>('view');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Join state
  const [hasJoined, setHasJoined] = useState(false);
  const [isJoining, setIsJoining] = useState(false);
  const [joinMessage, setJoinMessage] = useState<string | null>(null);
  const [joinError, setJoinError] = useState<string | null>(null);

  // Submissions feed state
  const [feedItems, setFeedItems] = useState<SpreeItem[]>([]);
  const [feedLoading, setFeedLoading] = useState(false);
  const [feedError, setFeedError] = useState<string | null>(null);
  const [feedPage, setFeedPage] = useState(1);

  // Submit modal state
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [mySprees, setMySprees] = useState<SpreeItem[]>([]);
  const [selectedSpreeId, setSelectedSpreeId] = useState<string>('');
  const [manualSpreeId, setManualSpreeId] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  const loadChallenge = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await opensApi.getChallengeById(challengeId);
      setChallenge(data);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setError('Open not found (404)');
        } else {
          setError(err.message);
        }
      } else {
        setError('Failed to load Open details');
      }
    } finally {
      setLoading(false);
    }
  }, [challengeId]);

  const loadFeed = useCallback(async () => {
    setFeedLoading(true);
    setFeedError(null);
    try {
      const items = await opensApi.getOpenFeed(challengeId, { page: feedPage, limit: 10 });
      setFeedItems(items);
    } catch (err) {
      setFeedError(err instanceof ApiError ? err.message : 'Failed to load submissions');
    } finally {
      setFeedLoading(false);
    }
  }, [challengeId, feedPage]);

  useEffect(() => {
    loadChallenge();
  }, [loadChallenge]);

  useEffect(() => {
    if (viewTab === 'view') {
      loadFeed();
    }
  }, [viewTab, loadFeed]);

  const handleJoin = async () => {
    if (!challenge || hasJoined || isJoining) return;
    setIsJoining(true);
    setJoinError(null);
    setJoinMessage(null);

    try {
      const res = await opensApi.joinChallenge(challenge.id);
      setHasJoined(true);
      setJoinMessage(res.message || 'Successfully joined Open!');
      // Update participants count locally
      setChallenge((prev) =>
        prev ? { ...prev, participants_count: prev.participants_count + 1 } : null
      );
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to join challenge';
      setJoinError(msg);
    } finally {
      setIsJoining(false);
    }
  };

  const handleOpenSubmitModal = async () => {
    setShowSubmitModal(true);
    setSubmitError(null);
    setSubmitSuccess(null);
    try {
      const sprees = await feedApi.getFeed('for_you');
      setMySprees(sprees);
      if (sprees.length > 0) {
        setSelectedSpreeId(sprees[0].id);
      }
    } catch {
      // Fallback manual entry
    }
  };

  const handleSubmitSpree = async (e: React.FormEvent) => {
    e.preventDefault();
    const spreeId = selectedSpreeId || manualSpreeId.trim();
    if (!spreeId) {
      setSubmitError('Please select or provide a Spree ID to submit.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      await opensApi.submitSpree(challengeId, spreeId);
      setSubmitSuccess('Spree submitted successfully!');
      // Update submissions count locally
      setChallenge((prev) =>
        prev ? { ...prev, submissions_count: prev.submissions_count + 1 } : null
      );
      // Reload feed
      loadFeed();
      setTimeout(() => setShowSubmitModal(false), 1500);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Submission failed';
      setSubmitError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <div className="w-7 h-7 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-spreego-text-secondary">Loading Open details...</span>
      </div>
    );
  }

  if (error || !challenge) {
    return (
      <div className="w-full flex-1 flex flex-col items-center justify-center py-20 px-4 space-y-4 text-center">
        <div className="w-12 h-12 rounded-full bg-rose-500/10 flex items-center justify-center text-rose-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <div>
          <h3 className="font-display font-bold text-base text-white">Unable to Load Open</h3>
          <p className="text-xs text-spreego-text-secondary mt-1">{error || 'Open not found'}</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onBack}
            className="px-4 py-2 rounded-xl bg-spreego-elevated text-xs font-semibold text-white hover:bg-white/10"
          >
            Go Back
          </button>
          <button
            onClick={loadChallenge}
            className="px-4 py-2 rounded-xl bg-spreego-violet text-xs font-semibold text-white hover:bg-spreego-violet-light"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex-1 flex flex-col space-y-4 pb-20">
      {/* Top Header Bar */}
      <div className="flex items-center justify-between py-1 border-b border-white/5">
        <button
          onClick={onBack}
          aria-label="Back"
          className="p-1.5 rounded-full hover:bg-spreego-elevated text-spreego-text-secondary hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <span className="font-display font-bold text-sm text-white truncate max-w-[200px]">
          {challenge.title}
        </span>
        <button
          onClick={() => alert('Challenge link copied!')}
          aria-label="Share"
          className="p-1.5 rounded-full hover:bg-spreego-elevated text-spreego-text-secondary hover:text-white transition-colors"
        >
          <Share2 className="w-4 h-4" />
        </button>
      </div>

      {/* Hero Cover Image & Header */}
      <div className="relative rounded-3xl overflow-hidden h-44 border border-white/10 shadow-lg bg-spreego-surface">
        {challenge.cover_image_url ? (
          <img
            src={challenge.cover_image_url}
            alt={challenge.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl bg-gradient-to-tr from-slate-900 to-spreego-surface">
            🏆
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />
        <div className="absolute bottom-3 left-4 right-4">
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-spreego-violet text-white">
              {challenge.type}
            </span>
            {challenge.reward_info && (
              <span className="text-xs text-spreego-champagne font-semibold font-mono">
                {challenge.reward_info}
              </span>
            )}
          </div>
          <h2 className="font-display font-extrabold text-xl text-white mt-1 drop-shadow">
            {challenge.title}
          </h2>
          {challenge.description && (
            <p className="text-xs text-slate-200 line-clamp-1">{challenge.description}</p>
          )}
        </div>
      </div>

      {/* Join Messages & Errors */}
      {joinMessage && (
        <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{joinMessage}</span>
        </div>
      )}
      {joinError && (
        <div className="p-3 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{joinError}</span>
        </div>
      )}

      {/* Key Metric Cards */}
      <div className="grid grid-cols-3 gap-2">
        <div className="p-3 rounded-2xl bg-spreego-surface border border-white/5 flex flex-col items-center text-center space-y-1">
          <Users className="w-4 h-4 text-spreego-violet" />
          <span className="text-xs font-mono font-bold text-white">
            {challenge.participants_count}
          </span>
          <span className="text-[10px] text-spreego-text-secondary">Participants</span>
        </div>
        <div className="p-3 rounded-2xl bg-spreego-surface border border-white/5 flex flex-col items-center text-center space-y-1">
          <Trophy className="w-4 h-4 text-spreego-champagne" />
          <span className="text-xs font-mono font-bold text-spreego-champagne truncate max-w-[80px]">
            {challenge.reward_info || 'Community'}
          </span>
          <span className="text-[10px] text-spreego-text-secondary">Reward Pool</span>
        </div>
        <div className="p-3 rounded-2xl bg-spreego-surface border border-white/5 flex flex-col items-center text-center space-y-1">
          <Clock className="w-4 h-4 text-rose-400" />
          <span className="text-xs font-mono font-bold text-white">
            {getDaysLeft(challenge.end_at)} Days
          </span>
          <span className="text-[10px] text-spreego-text-secondary">Time Left</span>
        </div>
      </div>

      {/* Segmented Controller: View Submissions vs Leaderboard */}
      <div className="flex items-center space-x-1 bg-spreego-surface p-1 rounded-2xl border border-white/10 self-center">
        <button
          onClick={() => setViewTab('view')}
          className={`px-5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
            viewTab === 'view'
              ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
              : 'text-spreego-text-secondary hover:text-white'
          }`}
        >
          View Submissions
        </button>
        <button
          onClick={() => setViewTab('ranking')}
          className={`px-5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
            viewTab === 'ranking'
              ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
              : 'text-spreego-text-secondary hover:text-white'
          }`}
        >
          Leaderboard Ranking
        </button>
      </div>

      {/* Tab View: Rules & Real Submissions Feed */}
      {viewTab === 'view' ? (
        <div className="flex flex-col space-y-3">
          {/* Rules Section */}
          {challenge.rules && challenge.rules.length > 0 && (
            <div className="p-4 rounded-2xl bg-spreego-surface border border-white/5 space-y-2">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                Rules &amp; Guidelines
              </h4>
              <ul className="space-y-1.5 text-xs text-spreego-text-secondary list-disc pl-4">
                {challenge.rules.map((rule, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Submissions Section Header */}
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs font-bold text-white">
              Submissions ({challenge.submissions_count})
            </span>
            <button
              onClick={handleOpenSubmitModal}
              className="flex items-center space-x-1 px-3 py-1 rounded-full bg-spreego-violet/20 border border-spreego-violet/40 text-spreego-violet-light text-xs font-semibold hover:bg-spreego-violet hover:text-white transition-all"
            >
              <Upload className="w-3 h-3" />
              <span>Submit Spree</span>
            </button>
          </div>

          {/* Real Backend Submissions Feed */}
          {feedLoading ? (
            <div className="py-8 flex justify-center">
              <div className="w-5 h-5 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
            </div>
          ) : feedError ? (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-center space-y-2">
              <p className="text-xs text-rose-300">{feedError}</p>
              <button
                onClick={loadFeed}
                className="px-3 py-1 rounded-lg bg-rose-500/20 text-white text-xs"
              >
                Retry Feed
              </button>
            </div>
          ) : feedItems.length === 0 ? (
            <div className="py-8 rounded-2xl bg-spreego-surface border border-white/5 text-center p-6 space-y-2">
              <Film className="w-8 h-8 text-spreego-text-secondary mx-auto opacity-50" />
              <p className="text-xs text-spreego-text-secondary">
                No submissions in this Open yet. Be the first creator to submit!
              </p>
              <button
                onClick={handleOpenSubmitModal}
                className="px-4 py-1.5 rounded-xl bg-spreego-violet text-white text-xs font-semibold hover:bg-spreego-violet-light transition-all"
              >
                Submit Now
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2.5">
              {feedItems.map((sub) => (
                <div
                  key={sub.id}
                  className="relative rounded-2xl overflow-hidden h-40 bg-spreego-surface border border-white/5 shadow-md group"
                >
                  <img
                    src={sub.thumbnail_url || sub.media_url}
                    alt={sub.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent" />
                  <div className="absolute bottom-2 left-2 right-2">
                    <span className="text-[11px] font-bold text-white block truncate">
                      {sub.title}
                    </span>
                    <div className="flex items-center justify-between text-[9px] font-mono text-spreego-champagne mt-0.5">
                      <span>👤 {sub.creator?.username || 'Creator'}</span>
                      <span>👏 {sub.claps_count}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination if applicable */}
          {feedItems.length >= 10 && (
            <div className="flex justify-center pt-2">
              <button
                onClick={() => setFeedPage((p) => p + 1)}
                className="px-4 py-1.5 rounded-xl bg-spreego-elevated text-xs text-spreego-text-secondary hover:text-white"
              >
                Load More
              </button>
            </div>
          )}
        </div>
      ) : (
        <RankingLeaderboard challengeId={challenge.id} />
      )}

      {/* Sticky Bottom Join CTA */}
      <div className="pt-2">
        <button
          onClick={handleJoin}
          disabled={hasJoined || isJoining || !challenge.is_active}
          className={`w-full py-3.5 rounded-2xl font-display font-bold text-sm shadow-lg flex items-center justify-center space-x-2 transition-all active:scale-[0.98] ${
            hasJoined
              ? 'bg-emerald-600 text-white shadow-emerald-900/30'
              : !challenge.is_active
              ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-spreego-violet to-spreego-violet-light text-white shadow-violet-900/30 hover:brightness-110'
          }`}
        >
          {hasJoined ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-white" />
              <span>Registered in Challenge</span>
            </>
          ) : !challenge.is_active ? (
            <span>Challenge Ended</span>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-spreego-champagne" />
              <span>{isJoining ? 'Joining...' : 'Join Challenge Now'}</span>
            </>
          )}
        </button>
      </div>

      {/* Submit Spree Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-spreego-surface border border-white/10 rounded-3xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-sm text-white">Submit Spree to Challenge</h3>
              <button
                onClick={() => setShowSubmitModal(false)}
                className="text-spreego-text-secondary hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            {submitSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{submitSuccess}</span>
              </div>
            )}

            {submitError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            <form onSubmit={handleSubmitSpree} className="space-y-3">
              {mySprees.length > 0 && (
                <div>
                  <label className="text-xs text-spreego-text-secondary block mb-1">
                    Select Your Spree
                  </label>
                  <select
                    value={selectedSpreeId}
                    onChange={(e) => {
                      setSelectedSpreeId(e.target.value);
                      setManualSpreeId('');
                    }}
                    className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs outline-none"
                  >
                    {mySprees.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.title} ({s.type})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="text-xs text-spreego-text-secondary block mb-1">
                  Or Enter Spree UUID
                </label>
                <input
                  type="text"
                  placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                  value={manualSpreeId}
                  onChange={(e) => {
                    setManualSpreeId(e.target.value);
                    if (e.target.value) setSelectedSpreeId('');
                  }}
                  className="w-full px-3 py-2 rounded-xl bg-spreego-elevated border border-white/10 text-white text-xs outline-none focus:border-spreego-violet"
                />
              </div>

              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowSubmitModal(false)}
                  className="px-3 py-1.5 rounded-xl text-xs text-spreego-text-secondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl bg-spreego-violet hover:bg-spreego-violet-light text-white text-xs font-semibold disabled:opacity-50"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Spree'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
