import React, { useState, useEffect } from 'react';
import { ProductItem, StoreTab, CommunityPass, OrderRecord } from '../../types';
import { storeApi } from '../../api/client';
import { ProductCard } from './ProductCard';
import { CheckCircle2 } from 'lucide-react';

import { useApp } from '../../context/AppContext';

export const StoreCatalog: React.FC = () => {
  const { showToast } = useApp();
  const [activeTab, setActiveTab] = useState<StoreTab>('products');
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [pass, setPass] = useState<CommunityPass | null>(null);
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [hasSubscribedPass, setHasSubscribedPass] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    if (activeTab === 'orders') {
      storeApi.getOrders().then((res) => {
        setOrders(res || []);
        setLoading(false);
      }).catch(() => {
        setOrders([]);
        setLoading(false);
      });
    } else {
      Promise.all([
        storeApi.getProducts(activeTab).catch(() => []),
        storeApi.getCommunityPass().catch(() => null),
      ]).then(([prods, passData]) => {
        setProducts(prods || []);
        setPass(passData);
        setLoading(false);
      }).catch(() => {
        setLoading(false);
      });
    }
  }, [activeTab]);

  const handleJoinPass = async () => {
    if (pass) {
      try {
        const res = await storeApi.subscribeCommunityPass(pass.id);
        if (res.success) {
          setHasSubscribedPass(true);
          showToast('🎉 ₹0 Creator Community Pass activated for 30 days!');
        }
      } catch (err: any) {
        showToast(err.message || 'Failed to activate pass');
      }
    }
  };

  const handleBuy = async (product: ProductItem) => {
    try {
      const order = await storeApi.placeOrder(product.id, 1);
      showToast(`Order placed for ${product.title}! (ID: ${order.id.slice(0, 8)})`);
    } catch (err: any) {
      showToast(err.message || 'Failed to place order');
    }
  };

  return (
    <div className="w-full flex-1 flex flex-col space-y-4 pb-16">
      {/* Catalog Segmented Tabs */}
      <div className="flex items-center space-x-1 bg-spreego-surface p-1 rounded-2xl border border-white/5">
        {(['products', 'digital', 'orders'] as StoreTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-1.5 rounded-xl text-xs font-semibold capitalize transition-all ${
              activeTab === tab
                ? 'bg-spreego-violet text-white shadow-sm shadow-spreego-violet/40'
                : 'text-spreego-text-secondary hover:text-white'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab !== 'orders' ? (
        <>
          {/* ₹0 Free Creator Community Pass Card */}
          {pass && (
            <div className="relative rounded-3xl overflow-hidden p-4 bg-gradient-to-r from-purple-950/40 via-violet-900/20 to-black border border-spreego-violet/40 shadow-lg flex flex-col space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-spreego-champagne/20 text-spreego-champagne border border-spreego-champagne/30">
                  Creator Membership
                </span>
                <span className="text-xs font-mono font-bold text-white bg-black/60 px-2.5 py-0.5 rounded-full">
                  ₹0 / month
                </span>
              </div>
              <div>
                <h3 className="font-display font-extrabold text-base text-white">{pass.title}</h3>
                <p className="text-xs text-slate-300 mt-0.5">{pass.description}</p>
              </div>

              {/* Benefits summary */}
              <div className="space-y-1 pt-1">
                {pass.benefits.slice(0, 2).map((b, i) => (
                  <div key={i} className="flex items-center space-x-2 text-[11px] text-spreego-text-secondary">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span className="truncate">{b}</span>
                  </div>
                ))}
              </div>

              <button
                onClick={handleJoinPass}
                disabled={hasSubscribedPass}
                className={`w-full py-2.5 rounded-xl text-xs font-bold transition-all shadow-md active:scale-98 ${
                  hasSubscribedPass
                    ? 'bg-emerald-600 text-white'
                    : 'bg-spreego-violet hover:brightness-110 text-white shadow-spreego-violet/30'
                }`}
              >
                {hasSubscribedPass ? '✓ Member Pass Active' : 'Join Community Pass — ₹0'}
              </button>
            </div>
          )}

          {/* Featured Products Section */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white uppercase tracking-wider pl-1">
                Featured {activeTab === 'digital' ? 'Digital Goods' : 'Merchandise'}
              </span>
              <span className="text-[10px] text-spreego-text-secondary">{products.length} Items</span>
            </div>

            {loading ? (
              <div className="py-12 flex justify-center">
                <div className="w-6 h-6 border-2 border-spreego-violet border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {products.map((prod) => (
                  <ProductCard key={prod.id} product={prod} onBuy={handleBuy} />
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        /* Orders List Tab */
        <div className="space-y-3">
          <span className="text-xs font-bold text-white uppercase tracking-wider pl-1">
            My Past Orders ({orders.length})
          </span>
          <div className="space-y-2.5">
            {orders.map((ord) => (
              <div
                key={ord.id}
                className="p-3.5 rounded-2xl bg-spreego-surface border border-white/5 flex items-center justify-between"
              >
                <div className="flex items-center space-x-3">
                  <img
                    src={ord.product_image}
                    alt={ord.product_title}
                    className="w-12 h-12 rounded-xl object-cover border border-white/10 shrink-0"
                  />
                  <div>
                    <h4 className="text-xs font-bold text-white">{ord.product_title}</h4>
                    <span className="text-[10px] text-spreego-text-secondary block font-mono">
                      Qty: {ord.quantity} • ₹{ord.total_amount_inr.toLocaleString()}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-spreego-elevated text-emerald-400 border border-emerald-500/20">
                    {ord.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
