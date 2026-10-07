import React from 'react';

interface VinylDiscProps {
  isPlaying: boolean;
  coverUrl?: string;
  onClick?: () => void;
}

export const VinylDisc: React.FC<VinylDiscProps> = ({ isPlaying, coverUrl, onClick }) => {
  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label="Sound track disc"
      className="relative flex items-center justify-center cursor-pointer group select-none"
    >
      {/* Outer Vinyl Record */}
      <div
        className={`w-11 h-11 rounded-full bg-gradient-to-tr from-[#12151E] via-[#1A1F2C] to-[#0B0D13] p-1 border border-white/20 shadow-lg shadow-black/60 flex items-center justify-center ${
          isPlaying ? 'animate-spin' : ''
        }`}
        style={{ animationDuration: '6s', animationTimingFunction: 'linear' }}
      >
        {/* Subtle record grooves */}
        <div className="w-full h-full rounded-full border border-white/10 flex items-center justify-center p-1.5">
          {/* Album Cover Center */}
          <div className="w-5 h-5 rounded-full overflow-hidden bg-spreego-violet flex items-center justify-center border border-white/30">
            {coverUrl ? (
              <img src={coverUrl} alt="Album" className="w-full h-full object-cover" />
            ) : (
              <div className="w-1.5 h-1.5 rounded-full bg-spreego-champagne" />
            )}
          </div>
        </div>
      </div>

      {/* Floating 4-bar equalizer indicator */}
      <div className="absolute -top-2.5 right-0 flex items-end space-x-0.5 bg-black/60 backdrop-blur-sm px-1.5 py-0.5 rounded-full border border-white/10">
        <span
          className={`w-0.5 bg-spreego-violet rounded-full transition-all ${
            isPlaying ? 'h-3 animate-pulse' : 'h-1'
          }`}
          style={{ animationDuration: '0.4s' }}
        />
        <span
          className={`w-0.5 bg-spreego-champagne rounded-full transition-all ${
            isPlaying ? 'h-4 animate-pulse' : 'h-1'
          }`}
          style={{ animationDuration: '0.6s' }}
        />
        <span
          className={`w-0.5 bg-spreego-violet-light rounded-full transition-all ${
            isPlaying ? 'h-2 animate-pulse' : 'h-1'
          }`}
          style={{ animationDuration: '0.5s' }}
        />
        <span
          className={`w-0.5 bg-white rounded-full transition-all ${
            isPlaying ? 'h-3.5 animate-pulse' : 'h-1'
          }`}
          style={{ animationDuration: '0.35s' }}
        />
      </div>
    </div>
  );
};

