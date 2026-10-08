import React from 'react';
import { SpreeItem } from '../../types';
import { Eye, Heart, Play } from 'lucide-react';

interface MasonryGridProps {
  items: SpreeItem[];
  onSelectSpree: (spree: SpreeItem) => void;
}

export const MasonryGrid: React.FC<MasonryGridProps> = ({ items, onSelectSpree }) => {
  if (items.length === 0) {
    return (
      <div className="py-12 text-center space-y-2">
        <p className="text-sm font-semibold text-white">No Sprees found</p>
        <p className="text-xs text-spreego-text-secondary">Try searching with different keywords or filters</p>
      </div>
    );
  }

  // Split into 2 columns for masonry layout
  const col1 = items.filter((_, i) => i % 2 === 0);
  const col2 = items.filter((_, i) => i % 2 !== 0);

  const renderCard = (spree: SpreeItem, index: number) => {
    // Varied aspect ratio for natural masonry feel
    const isTall = index % 2 === 1;

    return (
      <div
        key={spree.id}
        onClick={() => onSelectSpree(spree)}
        className="group relative rounded-2xl overflow-hidden bg-spreego-surface border border-white/10 cursor-pointer hover:border-spreego-violet/50 transition-all duration-200 active:scale-[0.98] shadow-md flex flex-col mb-3"
      >
        {/* Media Thumbnail Container */}
        <div className={`relative w-full overflow-hidden ${isTall ? 'h-64' : 'h-48'}`}>
          <img
            src={spree.thumbnail_url || spree.media_url}
            alt={spree.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />

          {/* Type Badge */}
          {spree.type === 'VIDEO_SHORT' && (
            <div className="absolute top-2 right-2 p-1 rounded-full bg-black/60 backdrop-blur-sm text-white">
              <Play className="w-3 h-3 fill-white" />
            </div>
          )}

          {/* Metric Pill Overlays */}
          <div className="absolute bottom-2 left-2 flex items-center space-x-2 text-[10px] font-mono text-white bg-black/50 backdrop-blur-sm px-2 py-0.5 rounded-full border border-white/10">
            <span className="flex items-center space-x-1">
              <Eye className="w-3 h-3 text-spreego-champagne" />
              <span>{(((spree.views_count ?? 1200)) / 1000).toFixed(1)}K</span>
            </span>
            <span className="flex items-center space-x-1">
              <Heart className="w-3 h-3 text-rose-400" />
              <span>{(((spree.claps_count ?? 340)) / 1000).toFixed(1)}K</span>
            </span>
          </div>
        </div>

        {/* Footer Info */}
        <div className="p-2.5 flex flex-col space-y-1 bg-spreego-surface/90">
          <h4 className="text-xs font-semibold text-white line-clamp-1 group-hover:text-spreego-violet-light transition-colors">
            {spree.title}
          </h4>
          <div className="flex items-center space-x-1.5">
            <img
              src={spree.creator?.avatar_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}
              alt={spree.creator?.username || 'Creator'}
              className="w-4 h-4 rounded-full object-cover border border-white/20"
            />
            <span className="text-[10px] text-spreego-text-secondary truncate">
              {spree.creator?.handle || `@creator_${(spree.creator_id || spree.id).slice(0, 6)}`}
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-2 gap-3 w-full">
      <div className="flex flex-col">{col1.map((item, idx) => renderCard(item, idx))}</div>
      <div className="flex flex-col">{col2.map((item, idx) => renderCard(item, idx))}</div>
    </div>
  );
};

