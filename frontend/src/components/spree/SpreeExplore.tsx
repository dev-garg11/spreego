import React, { useState, useEffect } from 'react';
import { SpreeItem, ExploreSubTab, CategoryFilterChip } from '../../types';
import { feedApi } from '../../api/client';
import { MasonryGrid } from './MasonryGrid';
import { Search, X, SlidersHorizontal } from 'lucide-react';
import { ReelCard } from '../feed/ReelCard';

export const SpreeExplore: React.FC = () => {
  const [subTab, setSubTab] = useState<ExploreSubTab>('for_you');
  const [category, setCategory] = useState<CategoryFilterChip>('all');
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<SpreeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSpree, setSelectedSpree] = useState<SpreeItem | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    feedApi.getExploreItems(category, query).then((res) => {
      if (active) {
        setItems(res);
        setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, [category, query]);

  const categories: { id: CategoryFilterChip; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'photos', label: 'Photos' },
    { id: 'videos', label: 'Videos' },
    { id: 'long_videos', label: 'Long Videos' },
  ];

  return (
    <div className="w-full flex-1 flex flex-col space-y-3 pb-8">
      {/* Sticky Search Header */}
      <div className="sticky top-14 z-30 bg-spreego-canvas/90 backdrop-blur-md pb-2 pt-1 flex flex-col space-y-2.5 border-b border-white/5">
        {/* Search Bar */}
        <div className="relative flex items-center">
          <Search className="absolute left-3 w-4 h-4 text-spreego-text-secondary" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search sprees, creators, topics..."
            className="w-full bg-spreego-elevated border border-white/10 rounded-2xl pl-9 pr-9 py-2 text-xs text-white placeholder-spreego-text-secondary focus:outline-none focus:border-spreego-violet transition-colors"
          />
          {query ? (
            <button
              onClick={() => setQuery('')}
              className="absolute right-3 p-0.5 rounded-full text-spreego-text-secondary hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          ) : (
            <SlidersHorizontal className="absolute right-3 w-3.5 h-3.5 text-spreego-text-secondary" />
          )}
        </div>

        {/* Discovery Sub-Tabs (For You, Trending, Following) */}
        <div className="flex items-center space-x-1 bg-spreego-surface p-0.5 rounded-full border border-white/5 self-start">
          {(['for_you', 'trending', 'following'] as ExploreSubTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setSubTab(tab)}
              className={`px-3 py-1 rounded-full text-[11px] font-medium transition-all ${
                subTab === tab
                  ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                  : 'text-spreego-text-secondary hover:text-white'
              }`}
            >
              {tab === 'for_you' ? 'For You' : tab === 'trending' ? 'Trending' : 'Following'}
            </button>
          ))}
        </div>

        {/* Category Discovery Filter Chips */}
        <div className="flex items-center space-x-1.5 overflow-x-auto scrollbar-none py-0.5">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setCategory(cat.id)}
              className={`px-3 py-1 rounded-xl text-xs whitespace-nowrap transition-all border ${
                category === cat.id
                  ? 'bg-spreego-violet/20 border-spreego-violet text-spreego-violet-light font-semibold'
                  : 'bg-spreego-elevated border-white/5 text-spreego-text-secondary hover:border-white/20'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid Content */}
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center space-y-2">
          <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-spreego-text-secondary">Filtering Sprees...</span>
        </div>
      ) : (
        <MasonryGrid items={items} onSelectSpree={(spree) => setSelectedSpree(spree)} />
      )}

      {/* Full-Screen Reel Modal Preview when a card is clicked */}
      {selectedSpree && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-3">
          <div className="relative w-full max-w-sm h-full flex flex-col">
            <button
              onClick={() => setSelectedSpree(null)}
              aria-label="Close preview"
              className="absolute top-4 right-4 z-40 p-2 rounded-full bg-black/60 text-white hover:bg-black/90 transition-all border border-white/20"
            >
              <X className="w-5 h-5" />
            </button>
            <ReelCard spree={selectedSpree} isActive={true} />
          </div>
        </div>
      )}
    </div>
  );
};

