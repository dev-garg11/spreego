import React, { useState } from 'react';
import { ClubItem } from '../../types';
import { mockClubs, mockCollageThreads } from '../../api/mockData';
import { useApp } from '../../context/AppContext';
import {
  Users,
  Gift,
  Layers,
  Check,
  Plus,
} from 'lucide-react';

export const ClubsFeed: React.FC = () => {
  const { showToast } = useApp();
  const [clubs, setClubs] = useState<ClubItem[]>(mockClubs);
  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [activeClubId, setActiveClubId] = useState<string>(mockClubs[0].id);

  const categories = ['All', 'Fitness', 'Food', 'Art & Design', 'Tech'];

  const filteredClubs = clubs.filter((c) =>
    activeCategory === 'All' ? true : c.category.toLowerCase().includes(activeCategory.toLowerCase())
  );

  const handleToggleJoin = (clubId: string) => {
    setClubs((prev) =>
      prev.map((c) => {
        if (c.id === clubId) {
          const next = !c.is_joined;
          showToast(next ? `🎉 Joined ${c.name} Club!` : `Left ${c.name}`);
          return {
            ...c,
            is_joined: next,
            members_count: next ? c.members_count + 1 : c.members_count - 1,
          };
        }
        return c;
      })
    );
  };

  return (
    <div className="w-full flex-1 flex flex-col space-y-4 pb-24">
      {/* Clubs Header Banner */}
      <div className="relative rounded-3xl overflow-hidden p-4 bg-gradient-to-tr from-purple-950/60 via-violet-900/30 to-black border border-spreego-violet/40 shadow-xl flex flex-col space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-spreego-champagne/20 text-spreego-champagne border border-spreego-champagne/30 flex items-center space-x-1">
            <Users className="w-3 h-3" />
            <span>Community Hubs</span>
          </span>
          <span className="text-[10px] font-mono text-slate-300">4 Active Clubs</span>
        </div>

        <div>
          <h2 className="font-display font-extrabold text-lg text-white">
            Creator Clubs &amp; Drops
          </h2>
          <p className="text-xs text-slate-300 leading-relaxed mt-0.5">
            Join niche communities, collaborate on Collage Threads, and unlock member-only drops!
          </p>
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex items-center space-x-1.5 overflow-x-auto scrollbar-none py-1">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeCategory === cat
                ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                : 'bg-spreego-surface text-spreego-text-secondary hover:text-white border border-white/5'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Clubs Cards Carousel / Grid */}
      <div className="grid grid-cols-1 gap-3">
        {filteredClubs.map((club) => (
          <div
            key={club.id}
            onClick={() => setActiveClubId(club.id)}
            className={`p-4 rounded-3xl transition-all border cursor-pointer ${
              activeClubId === club.id
                ? 'bg-spreego-surface border-spreego-violet/60 shadow-lg shadow-violet-950/30'
                : 'bg-spreego-surface/60 border-white/5 hover:border-white/20'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center text-xl shadow-md">
                  {club.icon}
                </div>
                <div>
                  <h3 className="font-display font-bold text-sm text-white flex items-center space-x-1.5">
                    <span>{club.name}</span>
                  </h3>
                  <span className="text-[11px] text-spreego-text-secondary block font-mono">
                    {club.members_count.toLocaleString()} members • {club.posts_count} sprees
                  </span>
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleToggleJoin(club.id);
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center space-x-1 ${
                  club.is_joined
                    ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-spreego-violet text-white hover:brightness-110 shadow-sm'
                }`}
              >
                {club.is_joined ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Joined</span>
                  </>
                ) : (
                  <>
                    <Plus className="w-3.5 h-3.5" />
                    <span>Join Club</span>
                  </>
                )}
              </button>
            </div>

            <p className="text-xs text-slate-300 mt-2 leading-snug">{club.tagline}</p>

            {/* Active Drop Badge */}
            {club.active_drop && (
              <div className="mt-3 p-2.5 rounded-2xl bg-black/40 border border-spreego-champagne/30 flex items-center justify-between">
                <div className="flex items-center space-x-2 truncate">
                  <Gift className="w-4 h-4 text-spreego-champagne shrink-0" />
                  <div className="truncate">
                    <span className="text-[10px] font-bold text-spreego-champagne uppercase block">
                      Active Drop: {club.active_drop.title}
                    </span>
                    <span className="text-[9px] text-slate-400">
                      Reward: {club.active_drop.reward} • {club.active_drop.expires_in}
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    showToast(`Claimed entry for ${club.active_drop?.title}!`);
                  }}
                  className="px-2.5 py-1 rounded-lg bg-spreego-champagne text-black text-[10px] font-bold hover:brightness-110"
                >
                  Enter Drop
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Collaborative Collage Threads Section */}
      <div className="p-4 rounded-3xl bg-spreego-surface border border-white/5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-spreego-violet-light" />
            <h3 className="font-display font-bold text-sm text-white">Collage Threads</h3>
          </div>
          <span className="text-[10px] text-spreego-text-secondary">Evolving Visual Stories</span>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          Users start on a blank canvas, and members stack photos, stickers &amp; videos to build collaborative art!
        </p>

        <div className="grid grid-cols-2 gap-2.5 pt-1">
          {mockCollageThreads.map((thread) => (
            <div
              key={thread.id}
              onClick={() => showToast(`Opening Collage Canvas: ${thread.title}`)}
              className="group relative rounded-2xl overflow-hidden bg-black border border-white/10 cursor-pointer hover:border-spreego-violet/50 transition-all active:scale-[0.98]"
            >
              <div className="relative h-32 w-full">
                <img
                  src={thread.cover_url}
                  alt={thread.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded-full bg-black/60 text-[9px] font-mono text-spreego-champagne border border-white/10">
                  {thread.layers_count} layers
                </span>
                <div className="absolute bottom-2 left-2 right-2">
                  <h4 className="text-xs font-bold text-white line-clamp-1">{thread.title}</h4>
                  <span className="text-[9px] text-slate-300 block truncate">{thread.creator_name}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={() => showToast('Starting new collaborative Collage Canvas...')}
          className="w-full py-2.5 rounded-2xl bg-spreego-elevated border border-white/10 hover:border-spreego-violet text-xs font-semibold text-white flex items-center justify-center space-x-1.5 transition-colors"
        >
          <Plus className="w-3.5 h-3.5 text-spreego-champagne" />
          <span>Start New Collage Thread</span>
        </button>
      </div>
    </div>
  );
};
