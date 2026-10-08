import {
  SpreeItem,
  CommentItem,
  Open,
  OpenChallenge,
  OpenRankingItem,
  JoinOpenResponse,
  OpenSubmissionResponse,
  CreateOpenPayload,
  OpenType,
  BrandCampaign,
  ProductItem,
  CommunityPass,
  OrderRecord,
  KPIMetric,
  TrendDataPoint,
  TopPerformingItem,
  WalletSummary,
  UserProfile,
  ViewTelemetryPayload,
} from '../types';
import {
  mockCurrentUser,
  mockSprees,
  mockExploreItems,
  mockOpens,
  mockLeaderboard,
  mockBrandCampaign,
  mockProducts,
  mockCommunityPass,
  mockOrders,
  mockKPIMetrics,
  mockViewsTrend,
  mockTopPerforming,
  mockWalletSummary,
  mockNotifications,
  mockClubs,
} from './mockData';

const BASE_URL = '/api/v1';

// Seeded verified user token (Aarav Sharma / @aarav_fitness in PostgreSQL)
const DEFAULT_DEMO_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYjE3YzVhZi01NmY4LTRiNTgtYjM2YS00YzUxNTJkZjAwYjIiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxODIyOTI2MTM0LCJpYXQiOjE3OTEzOTAxMzQsImp0aSI6InNwcmVlZ29fYWdteHlpN3IifQ.RRafjEgX3Ym_WCFiHJBf8qq__u2wJ_kBntPbWV-epYk';

export function getAuthToken(): string {
  if (typeof window !== 'undefined' && window.localStorage) {
    const saved = window.localStorage.getItem('spreego_token');
    if (saved && saved.trim()) return saved.trim();
    try {
      window.localStorage.setItem('spreego_token', DEFAULT_DEMO_TOKEN);
    } catch {
      // storage quota or restricted
    }
  }
  return DEFAULT_DEMO_TOKEN;
}

export function setAuthToken(token: string): void {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('spreego_token', token);
    } catch {
      // storage quota
    }
  }
}

function resolveUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null' && !window.location.origin.includes('undefined')) {
    return `${window.location.origin}${path}`;
  }
  return `http://localhost:8000${path}`;
}

export class ApiError extends Error {
  status: number;
  detail?: any;
  constructor(message: string, status: number, detail?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const customHeaders = (options.headers as Record<string, string>) || {};
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token && !customHeaders['Authorization'] ? { Authorization: `Bearer ${token}` } : {}),
    ...customHeaders,
  };

  let res: Response;
  try {
    res = await fetch(resolveUrl(url), {
      ...options,
      headers,
    });
  } catch (err) {
    throw new ApiError(`Network request failed: ${(err as Error).message}`, 0, err);
  }

  if (!res.ok) {
    let errorDetail: any = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      // ignore json parse error
    }
    const message = typeof errorDetail === 'string' ? errorDetail : `Request failed with status ${res.status}`;
    throw new ApiError(message, res.status, errorDetail);
  }

  return (await res.json()) as T;
}

async function safeFetch<T>(
  url: string,
  options: RequestInit = {},
  fallbackData: T
): Promise<T> {
  try {
    return await apiFetch<T>(url, options);
  } catch (err) {
    // Fallback for network/offline (0), missing endpoint (404), or server 500 in demo mode
    const apiErr = err as ApiError;
    if (apiErr.status === 0 || apiErr.status === 404 || apiErr.status >= 500) {
      console.info(`[SPREEGO API] Fallback used for ${url}:`, apiErr.message);
      return fallbackData;
    }
    throw err;
  }
}

/* =====================================================================
   FEED & SPREE API
===================================================================== */
export const feedApi = {
  async getFeed(subTab: string = 'for_you'): Promise<SpreeItem[]> {
    const raw = await safeFetch<any[]>(
      `${BASE_URL}/sprees/feed?tab=${subTab}`,
      { method: 'GET' },
      mockSprees
    );

    return raw.map((item: any) => ({
      ...item,
      creator: item.creator || {
        id: item.creator_id || 'usr_creator',
        username: item.creator_username || 'creator',
        handle: item.creator_username ? `@${item.creator_username}` : `@creator_${(item.creator_id || item.id || 'usr').slice(0, 6)}`,
        avatar_url: item.creator_avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150',
      },
      views_count: item.views_count ?? 18400,
      claps_count: item.claps_count ?? item.clap_count ?? 12400,
      comments_count: item.comments_count ?? item.comment_count ?? 342,
      shares_count: item.shares_count ?? item.share_count ?? 189,
    }));
  },

  async getExploreItems(category: string = 'all', query: string = ''): Promise<SpreeItem[]> {
    let items = [...mockExploreItems];
    if (category !== 'all') {
      const typeMap: Record<string, string> = {
        photos: 'PHOTO',
        videos: 'VIDEO_SHORT',
        long_videos: 'LONG_VIDEO',
      };
      const mapped = typeMap[category];
      if (mapped) {
        items = items.filter((item) => item.type === mapped);
      }
    }
    if (query.trim()) {
      const q = query.toLowerCase();
      items = items.filter(
        (item) =>
          item.title.toLowerCase().includes(q) ||
          item.creator?.username?.toLowerCase().includes(q) ||
          item.creator?.handle?.toLowerCase().includes(q) ||
          (item.tags && item.tags.some((t) => t.toLowerCase().includes(q)))
      );
    }

    const raw = await safeFetch<any[]>(
      `${BASE_URL}/sprees?category=${category}&q=${encodeURIComponent(query)}`,
      { method: 'GET' },
      items
    );

    return raw.map((item: any) => ({
      ...item,
      creator: item.creator || {
        id: item.creator_id || 'usr_creator',
        username: 'creator',
        handle: `@creator_${(item.creator_id || item.id || 'usr').slice(0, 6)}`,
        avatar_url: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150',
      },
      views_count: item.views_count ?? 1420,
      claps_count: item.claps_count ?? 320,
      comments_count: item.comments_count ?? 24,
      shares_count: item.shares_count ?? 12,
    }));
  },

  async getSpreeById(id: string): Promise<SpreeItem | null> {
    const fallback = mockExploreItems.find((s) => s.id === id) || mockSprees[0] || null;
    return safeFetch<SpreeItem | null>(
      `${BASE_URL}/sprees/${id}`,
      { method: 'GET' },
      fallback
    );
  },

  async clapSpree(id: string): Promise<{ success: boolean; newCount: number }> {
    const item = mockSprees.find((s) => s.id === id);
    const count = item ? item.claps_count + 1 : 12401;
    return safeFetch<{ success: boolean; newCount: number }>(
      `${BASE_URL}/sprees/${id}/clap`,
      { method: 'POST' },
      { success: true, newCount: count }
    );
  },

  async saveSpree(id: string): Promise<{ success: boolean; saved: boolean }> {
    return safeFetch<{ success: boolean; saved: boolean }>(
      `${BASE_URL}/sprees/${id}/save`,
      { method: 'POST' },
      { success: true, saved: true }
    );
  },

  async shareSpree(id: string, platform: string = 'web'): Promise<{ success: boolean; shareUrl: string }> {
    return safeFetch<{ success: boolean; shareUrl: string }>(
      `${BASE_URL}/sprees/${id}/share`,
      { method: 'POST', body: JSON.stringify({ platform }) },
      { success: true, shareUrl: `https://spreego.app/s/${id}` }
    );
  },

  async getComments(spreeId: string): Promise<CommentItem[]> {
    const fallback: CommentItem[] = [
      {
        id: 'c_1',
        spree_id: spreeId,
        user: mockCurrentUser,
        text: 'The colors in this sunset are breathtaking! 🌅',
        claps_count: 42,
        created_at: '2026-10-06T10:00:00Z',
      },
      {
        id: 'c_2',
        spree_id: spreeId,
        user: {
          id: 'usr_maya',
          username: 'Maya Crafts',
          handle: '@artistic_soul',
          display_name: 'Maya',
          avatar_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80',
          follower_count: 14200,
          following_count: 190,
          post_count: 67,
        },
        text: 'What lens was this shot with? Amazing quality.',
        claps_count: 18,
        created_at: '2026-10-06T10:30:00Z',
      },
    ];

    return safeFetch<CommentItem[]>(
      `${BASE_URL}/sprees/${spreeId}/comments`,
      { method: 'GET' },
      fallback
    );
  },

  async addComment(spreeId: string, text: string): Promise<CommentItem> {
    const fallback: CommentItem = {
      id: `c_${Date.now()}`,
      spree_id: spreeId,
      user: mockCurrentUser,
      text,
      claps_count: 0,
      created_at: new Date().toISOString(),
    };

    return safeFetch<CommentItem>(
      `${BASE_URL}/sprees/${spreeId}/comments`,
      { method: 'POST', body: JSON.stringify({ text }) },
      fallback
    );
  },

  async sendViewTelemetry(payload: ViewTelemetryPayload & { spree_id: string }): Promise<{ success: boolean }> {
    return safeFetch<{ success: boolean }>(
      `${BASE_URL}/sprees/${payload.spree_id}/view`,
      {
        method: 'POST',
        body: JSON.stringify({
          watch_duration: payload.watch_duration,
          completed: payload.completed,
          device_info: payload.device_info || 'Web/Desktop Chrome',
        }),
      },
      { success: true }
    );
  },
};

/* =====================================================================
   OPENS & CHALLENGES API
===================================================================== */
export const opensApi = {
  async getOpens(params: {
    type?: OpenType;
    status?: string;
    page?: number;
    skip?: number;
    limit?: number;
  } = {}): Promise<Open[]> {
    const q = new URLSearchParams();
    if (params.type) q.set('type', params.type);
    if (params.status) q.set('status', params.status);
    if (params.page !== undefined) q.set('page', String(params.page));
    if (params.skip !== undefined) q.set('skip', String(params.skip));
    if (params.limit !== undefined) q.set('limit', String(params.limit));

    const qs = q.toString() ? `?${q.toString()}` : '';
    try {
      return await apiFetch<Open[]>(`${BASE_URL}/opens${qs}`, { method: 'GET' });
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.status === 0 || apiErr.status >= 500) {
        let items = [...mockOpens];
        if (params.type) items = items.filter((o) => o.type === params.type);
        if (params.status) items = items.filter((o) => o.status === params.status);
        return items;
      }
      throw err;
    }
  },

  async getChallenges(mode: string = 'challenges', category: string = 'All'): Promise<OpenChallenge[]> {
    // Map frontend tab mode to backend OpenType:
    const type: OpenType | undefined =
      mode === 'competitions' ? 'COMPETITION' : mode === 'challenges' ? 'CHALLENGE' : undefined;
    const items = await this.getOpens({ type, status: 'ACTIVE' });
    if (category && category.toLowerCase() !== 'all') {
      return items.filter((o) => o.category?.toLowerCase() === category.toLowerCase());
    }
    return items;
  },

  async getChallengeById(id: string): Promise<Open> {
    try {
      return await apiFetch<Open>(`${BASE_URL}/opens/${id}`, { method: 'GET' });
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.status === 0 || apiErr.status === 404 || apiErr.status >= 500) {
        const fallback = mockOpens.find((o) => o.id === id) || mockOpens[0];
        return fallback;
      }
      throw err;
    }
  },

  async joinChallenge(challengeId: string): Promise<JoinOpenResponse> {
    try {
      const res = await apiFetch<JoinOpenResponse>(`${BASE_URL}/opens/${challengeId}/join`, {
        method: 'POST',
      });
      return {
        ...res,
        success: true,
      };
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.status === 0) {
        return {
          success: true,
          message: 'Successfully registered for challenge! (offline demo mode)',
          open_id: challengeId,
          user_id: 'usr_me_001',
          joined_at: new Date().toISOString(),
        };
      }
      throw err;
    }
  },

  async submitSpree(openId: string, spreeId: string): Promise<OpenSubmissionResponse> {
    return await apiFetch<OpenSubmissionResponse>(`${BASE_URL}/opens/${openId}/submissions`, {
      method: 'POST',
      body: JSON.stringify({ spree_id: spreeId }),
    });
  },

  async getOpenFeed(
    openId: string,
    params: { page?: number; skip?: number; limit?: number } = {}
  ): Promise<SpreeItem[]> {
    const q = new URLSearchParams();
    if (params.page !== undefined) q.set('page', String(params.page));
    if (params.skip !== undefined) q.set('skip', String(params.skip));
    if (params.limit !== undefined) q.set('limit', String(params.limit));

    const qs = q.toString() ? `?${q.toString()}` : '';
    try {
      return await apiFetch<SpreeItem[]>(`${BASE_URL}/opens/${openId}/feed${qs}`, {
        method: 'GET',
      });
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.status === 0 || apiErr.status >= 500) {
        return mockSprees.slice(0, 4);
      }
      throw err;
    }
  },

  async getRanking(challengeId: string): Promise<OpenRankingItem[]> {
    try {
      const items = await apiFetch<OpenRankingItem[]>(`${BASE_URL}/opens/${challengeId}/ranking`, {
        method: 'GET',
      });
      // Normalize any nested creator/spree fields for display
      return items.map((item) => ({
        ...item,
        username: item.creator?.full_name || item.creator?.username || item.username || item.user_id,
        handle: item.creator?.username ? `@${item.creator.username}` : item.handle || `@user_${item.user_id.slice(0, 6)}`,
        avatar: item.creator?.avatar_url || item.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150',
        spree_thumbnail: item.spree?.thumbnail_url || item.spree_thumbnail || 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=300',
      }));
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.status === 0 || apiErr.status >= 500) {
        return mockLeaderboard;
      }
      throw err;
    }
  },

  async createOpen(payload: CreateOpenPayload): Promise<Open> {
    if (!payload.title || !payload.title.trim()) {
      throw new ApiError('Title is required', 400);
    }
    if (!payload.end_at) {
      throw new ApiError('End date is required', 400);
    }
    const start = payload.start_at ? new Date(payload.start_at) : new Date();
    const end = new Date(payload.end_at);
    if (end <= start) {
      throw new ApiError('end_at must be strictly after start_at', 400);
    }

    return await apiFetch<Open>(`${BASE_URL}/opens`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getBrandCampaign(): Promise<BrandCampaign> {
    try {
      return await apiFetch<BrandCampaign>(`${BASE_URL}/sponsorships/featured`, {
        method: 'GET',
      });
    } catch (err) {
      const apiErr = err as ApiError;
      if (apiErr.status === 0 || apiErr.status >= 500) {
        return mockBrandCampaign;
      }
      throw err;
    }
  },
};

/* =====================================================================
   CREATOR COMMERCE & STORE API
===================================================================== */
export const storeApi = {
  async getProducts(category: string = 'products'): Promise<ProductItem[]> {
    let items = [...mockProducts];
    if (category === 'digital') {
      items = items.filter((p) => p.is_digital);
    }
    const rawItems = await safeFetch<any[]>(
      `${BASE_URL}/products?category=${category}`,
      { method: 'GET' },
      items
    );

    return rawItems.map((p: any) => ({
      id: p.id,
      creator_id: p.creator_id || 'usr_creator_001',
      title: p.title,
      description: p.description || '',
      price_inr: p.price_inr ?? p.price ?? 0,
      image_url: p.image_url || (p.images && p.images[0]) || 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=300',
      in_stock: p.in_stock ?? p.is_in_stock ?? (p.inventory !== undefined ? p.inventory > 0 : true),
      inventory_count: p.inventory_count ?? p.inventory ?? 25,
      is_digital: p.is_digital ?? (p.type === 'DIGITAL'),
      rating: p.rating ?? 4.9,
      sales_count: p.sales_count ?? 128,
      badge: p.badge,
    }));
  },

  async getCommunityPass(): Promise<CommunityPass> {
    const plans = await safeFetch<any>(
      `${BASE_URL}/memberships/plans`,
      { method: 'GET' },
      [mockCommunityPass]
    );
    if (Array.isArray(plans) && plans.length > 0) {
      const plan = plans.find((p: any) => p.is_free || p.price === 0) || plans[0];
      return {
        id: plan.id || mockCommunityPass.id,
        creator_id: plan.creator_id || mockCommunityPass.creator_id,
        title: plan.name || plan.title || mockCommunityPass.title,
        price_inr: plan.price ?? mockCommunityPass.price_inr,
        interval: plan.billing_period || plan.interval || mockCommunityPass.interval,
        description: plan.description || mockCommunityPass.description,
        benefits: plan.perks || plan.benefits || mockCommunityPass.benefits,
        is_active: plan.is_active ?? true,
      };
    }
    return mockCommunityPass;
  },

  async subscribeCommunityPass(planId: string = 'pass_free_community'): Promise<{ success: boolean; is_active: boolean }> {
    return safeFetch<{ success: boolean; is_active: boolean }>(
      `${BASE_URL}/memberships/subscribe`,
      { method: 'POST', body: JSON.stringify({ plan_id: planId }) },
      { success: true, is_active: true }
    );
  },

  async getOrders(): Promise<OrderRecord[]> {
    return safeFetch<OrderRecord[]>(
      `${BASE_URL}/orders/my`,
      { method: 'GET' },
      mockOrders
    );
  },

  async placeOrder(productId: string, quantity: number = 1): Promise<OrderRecord> {
    const product = mockProducts.find((p) => p.id === productId) || mockProducts[0];
    const fallback: OrderRecord = {
      id: `ord_${Date.now()}`,
      product_id: productId,
      product_title: product.title,
      product_image: product.image_url,
      price_inr: product.price_inr,
      quantity,
      total_amount_inr: product.price_inr * quantity,
      status: 'PROCESSING',
      created_at: new Date().toISOString(),
    };

    return safeFetch<OrderRecord>(
      `${BASE_URL}/orders`,
      {
        method: 'POST',
        body: JSON.stringify({
          items: [{ product_id: productId, quantity }],
        }),
      },
      fallback
    );
  },
};

/* =====================================================================
   CREATOR ANALYTICS & WALLET API
===================================================================== */
export const walletApi = {
  async getKPIMetrics(): Promise<KPIMetric[]> {
    return safeFetch<KPIMetric[]>(
      `${BASE_URL}/analytics/kpi`,
      { method: 'GET' },
      mockKPIMetrics
    );
  },

  async getViewsTrend(): Promise<TrendDataPoint[]> {
    return safeFetch<TrendDataPoint[]>(
      `${BASE_URL}/analytics/views-trend`,
      { method: 'GET' },
      mockViewsTrend
    );
  },

  async getTopContent(): Promise<TopPerformingItem[]> {
    return safeFetch<TopPerformingItem[]>(
      `${BASE_URL}/analytics/top-content`,
      { method: 'GET' },
      mockTopPerforming
    );
  },

  async getWalletSummary(): Promise<WalletSummary> {
    const res = await safeFetch<any>(
      `${BASE_URL}/wallet`,
      { method: 'GET' },
      mockWalletSummary
    );
    return {
      available_balance_inr: res.available_balance_inr ?? res.available_balance ?? mockWalletSummary.available_balance_inr,
      pending_payout_inr: res.pending_payout_inr ?? res.pending_payout_balance ?? mockWalletSummary.pending_payout_inr,
      currency: res.currency || mockWalletSummary.currency,
      upi_id: res.upi_id || mockWalletSummary.upi_id,
    };
  },

  async requestPayout(amount: number, upiId: string): Promise<{ success: boolean; transaction_id: string; message: string }> {
    return safeFetch<{ success: boolean; transaction_id: string; message: string }>(
      `${BASE_URL}/wallet/payout`,
      {
        method: 'POST',
        body: JSON.stringify({
          amount,
          payout_method: { type: 'UPI', upi_id: upiId },
        }),
      },
      {
        success: true,
        transaction_id: `txn_${Date.now()}`,
        message: `Payout of ₹${amount.toLocaleString()} initiated to ${upiId}`,
      }
    );
  },
};

/* =====================================================================
   USER PROFILE API
===================================================================== */
export const userApi = {
  async getCurrentUser(): Promise<UserProfile> {
    const res = await safeFetch<any>(
      `/auth/me`,
      { method: 'GET' },
      mockCurrentUser
    );
    if (res && res.profile) {
      return {
        id: res.id,
        username: res.profile.username || 'aarav_fitness',
        handle: `@${res.profile.username || 'aarav_fitness'}`,
        display_name: res.profile.full_name || 'Aarav Sharma',
        avatar_url: res.profile.avatar_url || mockCurrentUser.avatar_url,
        bio: res.profile.bio || mockCurrentUser.bio,
        follower_count: 12400,
        following_count: 180,
        post_count: 248,
        location: 'Bangalore, India',
        is_verified: res.is_verified ?? true,
        story_highlights: mockCurrentUser.story_highlights,
      };
    }
    return res as UserProfile;
  },

  async getUserById(id: string): Promise<UserProfile> {
    return safeFetch<UserProfile>(
      `${BASE_URL}/users/${id}`,
      { method: 'GET' },
      mockCurrentUser
    );
  },

  async followUser(id: string): Promise<{ success: boolean; message: string }> {
    return safeFetch<{ success: boolean; message: string }>(
      `${BASE_URL}/users/${id}/follow`,
      { method: 'POST' },
      { success: true, message: 'Followed creator successfully' }
    );
  },
};

/* =====================================================================
   NOTIFICATIONS API
===================================================================== */
export const notificationApi = {
  async getNotifications(): Promise<any[]> {
    const res = await safeFetch<any[]>(
      `${BASE_URL}/notifications`,
      { method: 'GET' },
      mockNotifications
    );
    return res || mockNotifications;
  },

  async getUnreadCount(): Promise<number> {
    const res = await safeFetch<{ unread_count: number }>(
      `${BASE_URL}/notifications/unread-count`,
      { method: 'GET' },
      { unread_count: 3 }
    );
    return res.unread_count ?? 3;
  },

  async markAllAsRead(): Promise<{ success: boolean }> {
    return safeFetch<{ success: boolean }>(
      `${BASE_URL}/notifications/read-all`,
      { method: 'POST' },
      { success: true }
    );
  },
};

/* =====================================================================
   CLUBS & COMMUNITY API
===================================================================== */
export const clubApi = {
  async getClubs(): Promise<any[]> {
    return safeFetch<any[]>(
      `${BASE_URL}/clubs`,
      { method: 'GET' },
      mockClubs
    );
  },

  async joinClub(clubId: string): Promise<{ success: boolean; message: string }> {
    return safeFetch<{ success: boolean; message: string }>(
      `${BASE_URL}/clubs/${clubId}/join`,
      { method: 'POST' },
      { success: true, message: 'Joined Club successfully!' }
    );
  },
};
