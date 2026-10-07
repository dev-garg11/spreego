import React, { useState } from 'react';
import { TrendDataPoint } from '../../types';

interface TrendChartProps {
  data: TrendDataPoint[];
}

export const TrendChart: React.FC<TrendChartProps> = ({ data }) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (!data || data.length === 0) return null;

  const maxViews = Math.max(...data.map((d) => d.views), 1);
  const chartHeight = 120;
  const chartWidth = 320;
  const paddingX = 24;
  const stepX = (chartWidth - paddingX * 2) / (data.length - 1);

  // Generate SVG path points
  const points = data.map((d, i) => {
    const x = paddingX + i * stepX;
    const y = chartHeight - (d.views / maxViews) * (chartHeight - 30) - 15;
    return { x, y, data: d };
  });

  const pathD = points.reduce((acc, pt, i) => {
    return i === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
  }, '');

  const areaD = `${pathD} L ${points[points.length - 1].x} ${chartHeight} L ${points[0].x} ${chartHeight} Z`;

  return (
    <div className="w-full flex flex-col space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-white uppercase tracking-wider">Views Trend</span>
        <span className="text-[10px] text-spreego-champagne font-mono font-medium">Last 7 Days</span>
      </div>

      <div className="relative bg-spreego-elevated/60 border border-white/5 rounded-2xl p-3 flex flex-col items-center">
        {/* Tooltip */}
        {hoverIndex !== null && (
          <div className="absolute top-2 right-4 px-2.5 py-1 rounded-xl bg-black/80 border border-spreego-violet/50 backdrop-blur-md text-[10px] text-white font-mono shadow-lg">
            <span>{data[hoverIndex].day}: </span>
            <span className="font-bold text-spreego-violet-light">{data[hoverIndex].formatted_views} views</span>
          </div>
        )}

        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-32 overflow-visible">
          <defs>
            <linearGradient id="violetGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7C3AED" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#7C3AED" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Area Fill */}
          <path d={areaD} fill="url(#violetGradient)" />

          {/* Line Stroke */}
          <path
            d={pathD}
            fill="none"
            stroke="#8B5CF6"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive Points */}
          {points.map((pt, idx) => (
            <g key={idx} onMouseEnter={() => setHoverIndex(idx)} onMouseLeave={() => setHoverIndex(null)}>
              <circle
                cx={pt.x}
                cy={pt.y}
                r={hoverIndex === idx ? 6 : 4}
                className={`transition-all cursor-pointer ${
                  hoverIndex === idx
                    ? 'fill-spreego-champagne stroke-white stroke-2'
                    : 'fill-spreego-violet stroke-[#0B0D13] stroke-2'
                }`}
              />
            </g>
          ))}
        </svg>

        {/* X-axis Day Labels */}
        <div className="w-full flex justify-between px-3 pt-1 text-[10px] font-mono text-spreego-text-secondary border-t border-white/5">
          {data.map((d) => (
            <span key={d.day}>{d.day}</span>
          ))}
        </div>
      </div>
    </div>
  );
};

