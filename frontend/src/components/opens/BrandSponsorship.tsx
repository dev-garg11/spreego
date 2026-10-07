import React, { useState, useEffect } from 'react';
import { BrandCampaign } from '../../types';
import { opensApi } from '../../api/client';
import { ArrowLeft, Trophy, Calendar, Users, Sparkles, Check } from 'lucide-react';

interface BrandSponsorshipProps {
  onBack: () => void;
}

export const BrandSponsorship: React.FC<BrandSponsorshipProps> = ({ onBack }) => {
  const [campaign, setCampaign] = useState<BrandCampaign | null>(null);
  const [hasJoined, setHasJoined] = useState(false);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    opensApi
      .getBrandCampaign()
      .then((res) => setCampaign(res))
      .catch((err) => setError(err.message || 'Failed to load sponsorship'));
  }, []);

  if (error) {
    return (
      <div className="py-16 text-center text-xs text-rose-300 space-y-2">
        <p>{error}</p>
        <button
          onClick={onBack}
          className="px-3 py-1.5 rounded-xl bg-spreego-elevated text-white text-xs"
        >
          Go Back
        </button>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="py-16 flex justify-center">
        <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="w-full flex-1 flex flex-col space-y-4 pb-20">
      {/* Header */}
      <div className="flex items-center justify-between py-1 border-b border-white/5">
        <button
          onClick={onBack}
          aria-label="Back"
          className="p-1.5 rounded-full hover:bg-spreego-elevated text-spreego-text-secondary hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <span className="font-display font-bold text-sm text-white">Brand Collaborations</span>
        <div className="w-8" />
      </div>

      {/* Hero Brand Card */}
      <div className="relative rounded-3xl overflow-hidden bg-spreego-surface border border-white/10 shadow-xl flex flex-col">
        <div className="relative h-44 w-full">
          <img
            src={campaign.hero_image_url}
            alt={campaign.campaign_title}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent" />
          <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-full border border-white/10 flex items-center space-x-1.5">
            <span className="text-[10px] font-bold text-spreego-champagne uppercase">
              {campaign.brand_name}
            </span>
            <span className="text-[9px] text-white">
              {campaign.is_demo ? '⚡ Demo Showcase' : '✓ Verified Sponsor'}
            </span>
          </div>
          <div className="absolute bottom-3 left-4 right-4">
            <h2 className="font-display font-extrabold text-xl text-white drop-shadow">
              {campaign.headline}
            </h2>
            <p className="text-xs text-slate-200 mt-1">{campaign.description}</p>
          </div>
        </div>
      </div>

      {/* Campaign Details 3-Metric Container */}
      <div className="grid grid-cols-3 gap-2">
        <div className="p-3 rounded-2xl bg-spreego-surface border border-white/5 flex flex-col items-center text-center space-y-1">
          <Trophy className="w-4 h-4 text-spreego-champagne" />
          <span className="text-xs font-mono font-bold text-spreego-champagne">
            {campaign.reward_pool}
          </span>
          <span className="text-[10px] text-spreego-text-secondary">Prize Pool</span>
        </div>
        <div className="p-3 rounded-2xl bg-spreego-surface border border-white/5 flex flex-col items-center text-center space-y-1">
          <Calendar className="w-4 h-4 text-spreego-violet" />
          <span className="text-xs font-mono font-bold text-white">{campaign.duration_days} Days</span>
          <span className="text-[10px] text-spreego-text-secondary">Duration</span>
        </div>
        <div className="p-3 rounded-2xl bg-spreego-surface border border-white/5 flex flex-col items-center text-center space-y-1">
          <Users className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-mono font-bold text-white">Top {campaign.winners_quota}</span>
          <span className="text-[10px] text-spreego-text-secondary">Winners</span>
        </div>
      </div>

      {/* About the Sponsor */}
      <div className="p-4 rounded-2xl bg-spreego-surface border border-white/5 space-y-2">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider">
          About {campaign.brand_name}
        </h4>
        <p className="text-xs text-spreego-text-secondary leading-relaxed">
          {campaign.about_brand}
        </p>
      </div>

      {/* Submission CTA */}
      <div className="pt-2">
        <button
          onClick={() => {
            setHasJoined(true);
            alert(`Registered for ${campaign.brand_name} campaign! Submission open.`);
          }}
          disabled={hasJoined}
          className={`w-full py-3.5 rounded-2xl font-display font-bold text-sm shadow-lg flex items-center justify-center space-x-2 transition-all active:scale-[0.98] ${
            hasJoined
              ? 'bg-emerald-600 text-white'
              : 'bg-gradient-to-r from-spreego-violet to-spreego-violet-light text-white shadow-violet-900/30 hover:brightness-110'
          }`}
        >
          {hasJoined ? (
            <>
              <Check className="w-4 h-4" />
              <span>Submission Registered</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-spreego-champagne" />
              <span>Join Sponsorship Campaign</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

