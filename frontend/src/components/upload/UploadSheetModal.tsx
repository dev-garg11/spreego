import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Video,
  Image,
  Radio,
  Sparkles,
  LayoutGrid,
  Clock,
  Camera,
  FolderOpen,
  FileEdit,
  ChevronRight,
  UploadCloud,
  CheckCircle2,
} from 'lucide-react';

interface UploadSheetModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const UploadSheetModal: React.FC<UploadSheetModalProps> = ({ isOpen, onClose }) => {
  const [, setSelectedMode] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);

  const creationModes = [
    {
      id: 'video',
      title: 'Upload Video',
      subtitle: 'Up to 10 min',
      icon: Video,
      color: 'from-violet-600 to-indigo-600',
    },
    {
      id: 'photo',
      title: 'Upload Photo',
      subtitle: 'Gallery or camera',
      icon: Image,
      color: 'from-blue-600 to-cyan-600',
    },
    {
      id: 'live',
      title: 'Go Live',
      subtitle: 'Connect in real-time',
      icon: Radio,
      color: 'from-pink-600 to-rose-600',
    },
    {
      id: 'spree',
      title: 'Create Spree',
      subtitle: 'Edit & add effects',
      icon: Sparkles,
      color: 'from-purple-600 to-violet-600',
    },
    {
      id: 'collage',
      title: 'Collage',
      subtitle: 'Make a collage',
      icon: LayoutGrid,
      color: 'from-emerald-600 to-teal-600',
    },
    {
      id: 'moments',
      title: 'Add to Moments',
      subtitle: 'Save to memories',
      icon: Clock,
      color: 'from-amber-600 to-orange-600',
    },
  ];

  const quickTools = [
    { id: 'camera', title: 'Open Camera', subtitle: 'Quick capture', icon: Camera },
    { id: 'gallery', title: 'From Gallery', subtitle: 'Select from your files', icon: FolderOpen },
    { id: 'drafts', title: 'Drafts', subtitle: 'Continue editing', icon: FileEdit },
  ];

  const handleSelectMode = (modeId: string) => {
    setSelectedMode(modeId);
    setIsUploading(true);
    setTimeout(() => {
      setIsUploading(false);
      setUploadComplete(true);
      setTimeout(() => {
        setUploadComplete(false);
        setSelectedMode(null);
        onClose();
        alert(`Successfully uploaded in ${modeId} mode!`);
      }, 1200);
    }, 1500);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-md">
          {/* Backdrop Dismiss */}
          <div className="absolute inset-0" onClick={onClose} />

          {/* Modal Container */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className="relative z-10 w-full max-w-lg bg-spreego-surface rounded-t-3xl border-t border-white/10 p-6 flex flex-col space-y-4 max-h-[90vh] overflow-y-auto"
          >
            {/* Grab Handle */}
            <div className="w-12 h-1 bg-white/20 rounded-full mx-auto" />

            {/* Header */}
            <div className="flex items-center justify-between">
              <h3 className="font-display font-bold text-lg text-white">Create New Spree</h3>
              <button
                onClick={onClose}
                aria-label="Close creation sheet"
                className="p-1 rounded-full text-spreego-text-secondary hover:text-white hover:bg-spreego-elevated transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Uploading Simulation State */}
            {isUploading && (
              <div className="p-8 flex flex-col items-center justify-center space-y-3 bg-spreego-elevated rounded-2xl border border-spreego-violet/30">
                <UploadCloud className="w-8 h-8 text-spreego-violet animate-bounce" />
                <span className="text-sm font-semibold text-white">Uploading media to SPREEGO...</span>
                <div className="w-48 h-1.5 bg-black/40 rounded-full overflow-hidden">
                  <div className="w-full h-full bg-spreego-violet animate-pulse" />
                </div>
              </div>
            )}

            {uploadComplete && (
              <div className="p-8 flex flex-col items-center justify-center space-y-3 bg-spreego-elevated rounded-2xl border border-emerald-500/30">
                <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                <span className="text-sm font-semibold text-white">Upload Complete!</span>
              </div>
            )}

            {!isUploading && !uploadComplete && (
              <>
                {/* 6-Option Creation Grid */}
                <div className="grid grid-cols-3 gap-2.5">
                  {creationModes.map((mode) => {
                    const IconComponent = mode.icon;
                    return (
                      <button
                        key={mode.id}
                        onClick={() => handleSelectMode(mode.id)}
                        className="group flex flex-col items-center justify-center p-3 rounded-2xl bg-spreego-elevated border border-white/5 hover:border-spreego-violet/50 active:scale-95 transition-all text-center space-y-2 shadow-sm"
                      >
                        <div
                          className={`w-10 h-10 rounded-xl bg-gradient-to-tr ${mode.color} flex items-center justify-center text-white shadow-md shadow-black/40 group-hover:scale-105 transition-transform`}
                        >
                          <IconComponent className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-xs font-semibold text-white block leading-tight">
                            {mode.title}
                          </span>
                          <span className="text-[10px] text-spreego-text-secondary block mt-0.5">
                            {mode.subtitle}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* "Other Ways to Create" Section */}
                <div className="pt-2 flex flex-col space-y-1.5">
                  <span className="text-xs font-semibold text-spreego-text-secondary uppercase tracking-wider pl-1">
                    Other Ways to Create
                  </span>
                  <div className="bg-spreego-elevated rounded-2xl border border-white/5 divide-y divide-white/5 overflow-hidden">
                    {quickTools.map((tool) => {
                      const Icon = tool.icon;
                      return (
                        <button
                          key={tool.id}
                          onClick={() => handleSelectMode(tool.id)}
                          className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors group"
                        >
                          <div className="flex items-center space-x-3">
                            <div className="p-2 rounded-xl bg-white/5 text-spreego-champagne group-hover:bg-spreego-violet/20 group-hover:text-spreego-violet-light transition-colors">
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="text-left">
                              <span className="text-xs font-medium text-white block">{tool.title}</span>
                              <span className="text-[10px] text-spreego-text-secondary block">
                                {tool.subtitle}
                              </span>
                            </div>
                          </div>
                          <ChevronRight className="w-4 h-4 text-spreego-text-secondary group-hover:text-white transition-colors" />
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Promo Incentive Banner */}
                <div className="p-3.5 rounded-2xl bg-gradient-to-r from-spreego-violet/20 via-purple-900/10 to-transparent border border-spreego-violet/30 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-white block">Turn moments into Spree</span>
                    <span className="text-[10px] text-spreego-text-secondary block">
                      Create something amazing today!
                    </span>
                  </div>
                  <Sparkles className="w-5 h-5 text-spreego-champagne shrink-0" />
                </div>
              </>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
