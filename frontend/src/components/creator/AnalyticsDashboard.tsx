import React, { useState, useEffect } from 'react';
import { KPIMetric, TrendDataPoint, TopPerformingItem, WalletSummary } from '../../types';
import { walletApi } from '../../api/client';
import { TrendChart } from './TrendChart';
import { WalletDrawer } from './WalletDrawer';
import { TrendingUp, Wallet, ArrowUpRight, Play } from 'lucide-react';

export const AnalyticsDashboard: React.FC = () => {
  const [kpis, setKpis] = useState<KPIMetric[]>([]);
  const [trend, setTrend] = useState<TrendDataPoint[]>([]);
  const [topContent, setTopContent] = useState<TopPerformingItem[]>([]);
  const [wallet, setWallet] = useState<WalletSummary | null>(null);
  const [isWalletOpen, setIsWalletOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      walletApi.getKPIMetrics(),
      walletApi.getViewsTrend(),
      walletApi.getTopContent(),
      walletApi.getWalletSummary(),
    ]).then(([kpiData, trendData, topData, walletData]) => {
      setKpis(kpiData);
      setTrend(trendData);
      setTopContent(topData);
      setWallet(walletData);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="py-16 flex justify-center">
        <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="w-full flex-1 flex flex-col space-y-4 pb-16">
      {/* 3 KPI Metric Cards */}
      <div className="grid grid-cols-3 gap-2">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="p-3 rounded-2xl bg-spreego-surface border border-white/5 flex flex-col justify-between space-y-1"
          >
            <span className="text-[10px] text-spreego-text-secondary truncate">{kpi.label}</span>
            <span className="font-mono font-extrabold text-sm text-white">{kpi.value}</span>
            <div className="flex items-center space-x-1 text-[9px] font-mono text-emerald-400">
              <TrendingUp className="w-2.5 h-2.5" />
              <span>+{kpi.growth_percent}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* 7-Day Interactive Views Trend Line Chart */}
      <TrendChart data={trend} />

      {/* Wallet Payout Card */}
      {wallet && (
        <div className="p-4 rounded-3xl bg-gradient-to-tr from-[#12151E] via-[#1A1F2C] to-[#12151E] border border-white/10 shadow-lg flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-bold text-spreego-champagne tracking-wider flex items-center space-x-1">
              <Wallet className="w-3.5 h-3.5" />
              <span>Creator Wallet</span>
            </span>
            <div className="font-mono font-extrabold text-xl text-white">
              ₹{wallet.available_balance_inr.toLocaleString()}
            </div>
            <span className="text-[10px] text-spreego-text-secondary block">
              Pending: ₹{wallet.pending_payout_inr.toLocaleString()}
            </span>
          </div>

          <button
            onClick={() => setIsWalletOpen(true)}
            className="px-4 py-2 rounded-xl bg-spreego-violet hover:brightness-110 active:scale-95 text-white font-semibold text-xs shadow-md shadow-violet-900/30 flex items-center space-x-1.5 transition-all"
          >
            <span>Withdraw</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-spreego-champagne" />
          </button>
        </div>
      )}

      {/* Top-Performing Content List */}
      <div className="space-y-2">
        <span className="text-xs font-bold text-white uppercase tracking-wider pl-1">
          Top Performing Content
        </span>
        <div className="space-y-2">
          {topContent.map((item) => (
            <div
              key={item.rank}
              className="p-2.5 rounded-2xl bg-spreego-surface border border-white/5 flex items-center justify-between"
            >
              <div className="flex items-center space-x-3">
                <span className="w-5 text-center font-mono font-bold text-xs text-spreego-champagne">
                  #{item.rank}
                </span>
                <img
                  src={item.thumbnail_url}
                  alt={item.title}
                  className="w-10 h-10 rounded-xl object-cover border border-white/10 shrink-0"
                />
                <div>
                  <h4 className="text-xs font-semibold text-white line-clamp-1">{item.title}</h4>
                  <span className="text-[10px] text-spreego-text-secondary font-mono">
                    {item.views_display} • {item.likes_display}
                  </span>
                </div>
              </div>

              <div className="p-2 rounded-full bg-spreego-elevated text-spreego-text-secondary">
                <Play className="w-3 h-3 fill-white text-white" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Withdrawal Drawer */}
      {wallet && (
        <WalletDrawer
          isOpen={isWalletOpen}
          onClose={() => setIsWalletOpen(false)}
          availableBalance={wallet.available_balance_inr}
        />
      )}
    </div>
  );
};
