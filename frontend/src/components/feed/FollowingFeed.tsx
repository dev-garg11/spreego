import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { SpreeItem } from '../../types';
import { mockSprees, mockStoryCollections } from '../../api/mockData';
import { ReelCard } from './ReelCard';
import { StoryViewerModal } from '../creator/StoryViewerModal';
import { Users, Sparkles, Flame, Plus, Check } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const FollowingFeed: React.FC = () => {
  const { showToast } = useApp();
  const [selectedHighlight, setSelectedHighlight] = useState<any>(null);
  const [followedCreators, setFollowedCreators] = useState([
    { id: 'f1', name: 'Maya Crafts', handle: '@maya_art', avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150', hasUnseenStory: true },
    { id: 'f2', name: 'Foodie Riya', handle: '@foodie_riya', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150', hasUnseenStory: true },
    { id: 'f3', name: 'Aarav Fitness', handle: '@aarav_fit', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150', hasUnseenStory: false },
    { id: 'f4', name: 'Elena Fit', handle: '@elena_core', avatar: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150', hasUnseenStory: true },
  ]);

  const [activeReelIdx, setActiveReelIdx] = useState(0);

  // Filter sprees to following creators
  const followingSprees: SpreeItem[] = mockSprees.slice(0, 3);

  const handleOpenStory = (creatorIdx: number) => {
    const highlight = mockStoryCollections[creatorIdx % mockStoryCollections.length];
    setSelectedHighlight(highlight);
  };

  return (
    <div className="w-full flex-1 flex flex-col space-y-3 pb-20">
      {/* Top Spreemates Live Stories Bar */}
      <div className="bg-spreego-surface/80 backdrop-blur-md rounded-2xl border border-white/5 p-3 flex flex-col space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold text-spreego-champagne uppercase tracking-wider flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Spreemates Stories</span>
          </span>
          <span className="text-[10px] text-spreego-text-secondary">Updated real-time</span>
        </div>

        <div className="flex items-center space-x-3 overflow-x-auto scrollbar-none py-1">
          {/* Your Story Trigger */}
          <div className="flex flex-col items-center space-y-1 cursor-pointer shrink-0">
            <div className="relative w-14 h-14 rounded-full p-0.5 border border-dashed border-spreego-violet flex items-center justify-center bg-spreego-elevated">
              <img
                src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
                alt="My Story"
                className="w-full h-full rounded-full object-cover"
              />
              <span className="absolute bottom-0 right-0 p-0.5 rounded-full bg-spreego-violet text-white">
                <Plus className="w-3 h-3" />
              </span>
            </div>
            <span className="text-[10px] text-white font-medium">Your Story</span>
          </div>

          {/* Followed Creators Stories */}
          {followedCreators.map((creator, idx) => (
            <div
              key={creator.id}
              onClick={() => handleOpenStory(idx)}
              className="flex flex-col items-center space-y-1 cursor-pointer shrink-0 group"
            >
              <div
                className={`w-14 h-14 rounded-full p-0.5 transition-transform group-hover:scale-105 ${
                  creator.hasUnseenStory
                    ? 'bg-gradient-to-tr from-spreego-violet via-pink-500 to-spreego-champagne shadow-md'
                    : 'bg-white/10'
                }`}
              >
                <img
                  src={creator.avatar}
                  alt={creator.name}
                  className="w-full h-full rounded-full object-cover border-2 border-black"
                />
              </div>
              <span className="text-[10px] text-slate-200 font-medium truncate max-w-[56px] text-center">
                {creator.name.split(' ')[0]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Following Feed Content Header */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-bold text-white flex items-center space-x-1.5">
          <Users className="w-4 h-4 text-spreego-violet-light" />
          <span>Latest from Creators You Follow</span>
        </span>
        <span className="text-[10px] font-mono text-spreego-champagne bg-spreego-champagne/10 px-2 py-0.5 rounded-full border border-spreego-champagne/20">
          Following Only
        </span>
      </div>

      {/* Following Sprees Container */}
      <div className="space-y-4">
        {followingSprees.map((spree, index) => (
          <div key={spree.id} className="relative rounded-3xl overflow-hidden bg-black border border-white/10 shadow-xl">
            <ReelCard
              spree={spree}
              isActive={activeReelIdx === index}
              onExploreSponsored={() => showToast('Opening sponsor campaign...')}
            />
          </div>
        ))}
      </div>

      {/* Story Viewer Modal */}
      <StoryViewerModal
        isOpen={Boolean(selectedHighlight)}
        highlight={selectedHighlight}
        onClose={() => setSelectedHighlight(null)}
      />
    </div>
  );
};
