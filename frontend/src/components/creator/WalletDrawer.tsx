import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle2, Wallet, ArrowDownRight } from 'lucide-react';
import { walletApi } from '../../api/client';

interface WalletDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  availableBalance: number;
}

export const WalletDrawer: React.FC<WalletDrawerProps> = ({
  isOpen,
  onClose,
  availableBalance,
}) => {
  const [amount, setAmount] = useState('10000');
  const [upiId, setUpiId] = useState('creator@okaxis');
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleWithdraw = async (e: React.FormEvent) => {
    e.preventDefault();
    const numAmount = parseFloat(amount);
    if (!numAmount || numAmount <= 0) {
      alert('Please enter a valid amount');
      return;
    }
    if (numAmount > availableBalance) {
      alert('Requested amount exceeds available balance');
      return;
    }

    setLoading(true);
    try {
      const res = await walletApi.requestPayout(numAmount, upiId);
      if (res.success) {
        setSuccessMsg(res.message);
        setTimeout(() => {
          setSuccessMsg(null);
          onClose();
        }, 2000);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-md">
          <div className="absolute inset-0" onClick={onClose} />

          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className="relative z-10 w-full max-w-lg bg-spreego-surface rounded-t-3xl border-t border-white/10 p-6 flex flex-col space-y-4 max-h-[85vh]"
          >
            <div className="w-12 h-1 bg-white/20 rounded-full mx-auto" />

            <div className="flex items-center justify-between pb-2 border-b border-white/5">
              <div className="flex items-center space-x-2">
                <Wallet className="w-5 h-5 text-spreego-champagne" />
                <h3 className="font-display font-bold text-base text-white">Withdraw Earnings</h3>
              </div>
              <button
                onClick={onClose}
                aria-label="Close drawer"
                className="p-1 rounded-full text-spreego-text-secondary hover:text-white hover:bg-spreego-elevated"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {successMsg ? (
              <div className="p-6 rounded-2xl bg-emerald-950/30 border border-emerald-500/40 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <h4 className="font-bold text-sm text-white">Payout Initiated!</h4>
                <p className="text-xs text-slate-300">{successMsg}</p>
              </div>
            ) : (
              <form onSubmit={handleWithdraw} className="space-y-4">
                <div className="p-4 rounded-2xl bg-spreego-elevated border border-white/5 flex items-center justify-between">
                  <span className="text-xs text-spreego-text-secondary">Available for Payout</span>
                  <span className="font-mono font-bold text-base text-white">
                    ₹{availableBalance.toLocaleString()}
                  </span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-spreego-text-secondary">
                    Withdrawal Amount (₹ INR)
                  </label>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    max={availableBalance}
                    min={1}
                    className="w-full bg-spreego-elevated border border-white/10 rounded-xl px-3.5 py-2.5 text-sm font-mono text-white focus:outline-none focus:border-spreego-violet"
                    placeholder="Enter amount"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-spreego-text-secondary">
                    UPI Virtual Payment Address (VPA)
                  </label>
                  <input
                    type="text"
                    value={upiId}
                    onChange={(e) => setUpiId(e.target.value)}
                    className="w-full bg-spreego-elevated border border-white/10 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-spreego-violet"
                    placeholder="e.g. username@okhdfcbank"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-spreego-violet to-spreego-violet-light font-display font-bold text-xs text-white shadow-lg shadow-violet-900/30 hover:brightness-110 active:scale-98 transition-all flex items-center justify-center space-x-2"
                >
                  <ArrowDownRight className="w-4 h-4 text-spreego-champagne" />
                  <span>{loading ? 'Processing Payout...' : `Confirm Withdrawal ₹${parseFloat(amount || '0').toLocaleString()}`}</span>
                </button>
              </form>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
