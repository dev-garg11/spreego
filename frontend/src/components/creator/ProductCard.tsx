import React from 'react';
import { ProductItem } from '../../types';
import { Star, ShoppingBag } from 'lucide-react';

interface ProductCardProps {
  product: ProductItem;
  onBuy: (product: ProductItem) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onBuy }) => {
  return (
    <div className="rounded-2xl overflow-hidden bg-spreego-surface border border-white/5 flex flex-col justify-between group hover:border-white/15 transition-all shadow-sm">
      {/* Thumbnail */}
      <div className="relative h-36 w-full overflow-hidden bg-black">
        <img
          src={product.image_url}
          alt={product.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        {product.badge && (
          <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider bg-spreego-violet text-white">
            {product.badge}
          </span>
        )}
        <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-black/60 backdrop-blur-sm text-spreego-champagne flex items-center space-x-1">
          <Star className="w-2.5 h-2.5 fill-spreego-champagne" />
          <span>{product.rating}</span>
        </span>
      </div>

      {/* Info & Buy Button */}
      <div className="p-3 flex flex-col space-y-2">
        <div>
          <h4 className="text-xs font-bold text-white line-clamp-1">{product.title}</h4>
          <span className="text-[10px] text-spreego-text-secondary line-clamp-1 mt-0.5">
            {product.description || 'Exclusive creator merchandise'}
          </span>
        </div>

        <div className="flex items-center justify-between pt-1 border-t border-white/5">
          <div>
            <span className="text-xs font-mono font-bold text-white">
              ₹{product.price_inr.toLocaleString()}
            </span>
            <span className="text-[9px] text-emerald-400 block font-medium">
              {product.in_stock ? 'In Stock' : 'Out of Stock'}
            </span>
          </div>

          <button
            onClick={() => onBuy(product)}
            disabled={!product.in_stock}
            className="p-2 rounded-xl bg-spreego-elevated hover:bg-spreego-violet text-white transition-colors active:scale-95 disabled:opacity-40"
            aria-label={`Buy ${product.title}`}
          >
            <ShoppingBag className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
