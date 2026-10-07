import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Heart } from 'lucide-react';
import { CommentItem } from '../../types';
import { feedApi } from '../../api/client';

interface CommentDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  spreeId: string;
}

export const CommentDrawer: React.FC<CommentDrawerProps> = ({ isOpen, onClose, spreeId }) => {
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && spreeId) {
      feedApi.getComments(spreeId).then((data) => setComments(data));
    }
  }, [isOpen, spreeId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    setLoading(true);
    try {
      const newComment = await feedApi.addComment(spreeId, inputText.trim());
      setComments((prev) => [newComment, ...prev]);
      setInputText('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm">
          {/* Backdrop dismissal */}
          <div className="absolute inset-0" onClick={onClose} />

          {/* Drawer Content */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className="relative z-10 w-full max-w-lg bg-spreego-surface rounded-t-3xl border-t border-white/10 p-5 flex flex-col max-h-[75vh]"
          >
            {/* Grab handle */}
            <div className="w-12 h-1 bg-white/20 rounded-full mx-auto mb-3" />

            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <h3 className="font-display font-bold text-base text-white">
                Comments <span className="text-xs font-mono text-spreego-text-secondary">({comments.length})</span>
              </h3>
              <button
                onClick={onClose}
                aria-label="Close comments"
                className="p-1 rounded-full text-spreego-text-secondary hover:text-white hover:bg-spreego-elevated"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Comments List */}
            <div className="flex-1 overflow-y-auto py-3 space-y-4 pr-1">
              {comments.map((comment) => (
                <div key={comment.id} className="flex space-x-3 items-start">
                  <img
                    src={comment.user.avatar_url}
                    alt={comment.user.username}
                    className="w-8 h-8 rounded-full object-cover border border-white/10"
                  />
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-white">{comment.user.username}</span>
                      <span className="text-[10px] text-spreego-text-secondary">{comment.user.handle}</span>
                    </div>
                    <p className="text-xs text-slate-200 mt-1 leading-relaxed">{comment.text}</p>
                  </div>
                  <div className="flex flex-col items-center space-y-0.5 text-spreego-text-secondary">
                    <button className="p-1 hover:text-spreego-violet">
                      <Heart className="w-3.5 h-3.5" />
                    </button>
                    {comment.claps_count > 0 && (
                      <span className="text-[10px] font-mono">{comment.claps_count}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Input Bar */}
            <form onSubmit={handleSubmit} className="pt-3 border-t border-white/5 flex items-center space-x-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Add a comment..."
                className="flex-1 bg-spreego-elevated border border-white/10 rounded-xl px-3 py-2 text-xs text-white placeholder-spreego-text-secondary focus:outline-none focus:border-spreego-violet transition-colors"
                maxLength={2000}
              />
              <button
                type="submit"
                disabled={!inputText.trim() || loading}
                className="p-2 rounded-xl bg-spreego-violet text-white hover:brightness-110 disabled:opacity-40 transition-all active:scale-95"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

