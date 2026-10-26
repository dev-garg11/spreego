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

const API_ORIGIN = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const BASE_URL = `${API_ORIGIN}/api/v1`;
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';
const OFFLINE_FALLBACKS_ENABLED = DEMO_MODE || import.meta.env.MODE === 'test';
const TEST_MODE = import.meta.env.MODE === 'test';

function hasMockedFetch(): boolean {
  return typeof fetch === 'function' && 'mock' in fetch;
}
const DEMO_TOKEN = (import.meta.env.VITE_DEMO_TOKEN || '').trim();

export function getAuthToken(): string | null {
  if (typeof window !== 'undefined' && window.localStorage) {
    const saved = window.localStorage.getItem('spreego_token');
    if (saved && saved.trim()) return saved.trim();
  }
  return DEMO_MODE && DEMO_TOKEN ? DEMO_TOKEN : null;
}

export function setAuthToken(token: string): void {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('spreego_token', token);
      window.dispatchEvent(new Event('spreego-auth-changed'));
    } catch {
      // storage quota
    }
  }
}

export function clearAuthSession(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem('spreego_token');
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  } finally {
    window.dispatchEvent(new Event('spreego-auth-changed'));
  }
}

const REFRESH_TOKEN_KEY = 'spreego_refresh_token';

export const authApi = {
  async register(payload: {
    identifier: string;
    username: string;
    password: string;
    fullName: string;
  }): Promise<void> {
    const response = await apiFetch<{ access_token: string; refresh_token: string }>(`${API_ORIGIN}/auth/register`, {
      method: 'POST',
      body: JSON.stringify({
        identifier: payload.identifier.trim(),
        username: payload.username.trim().replace(/^@/, '').toLowerCase(),
        password: payload.password,
        full_name: payload.fullName.trim(),
      }),
    });
    setAuthToken(response.access_token);
    try {
      window.localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token);
    } catch {
      // Storage may be disabled; the access token still works for the session.
    }
  },

  async login(identifier: string, password: string): Promise<void> {
    const response = await apiFetch<{ access_token: string; refresh_token: string }>(`${API_ORIGIN}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ identifier: identifier.trim(), password }),
    });
    setAuthToken(response.access_token);
    try {
      window.localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token);
    } catch {
      // Storage may be disabled; the access token still works for the session.
    }
  },

  async requestPasswordReset(identifier: string): Promise<string> {
    const response = await apiFetch<{ message: string }>(`${API_ORIGIN}/auth/forgot-password`, {
      method: 'POST',
      body: JSON.stringify({ identifier: identifier.trim() }),
    });
    return response.message;
  },

  async resetPassword(identifier: string, otpCode: string, newPassword: string): Promise<string> {
    const response = await apiFetch<{ message: string }>(`${API_ORIGIN}/auth/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ identifier: identifier.trim(), otp_code: otpCode.trim(), new_password: newPassword }),
    });
    return response.message;
  },

  async sendOtp(identifier: string): Promise<void> {
    await apiFetch(`${API_ORIGIN}/auth/send-otp`, {
      method: 'POST',
      body: JSON.stringify({ identifier }),
    });
  },

  async verifyOtp(
    identifier: string,
    otpCode: string,
    profile?: { fullName?: string; username?: string }
  ): Promise<void> {
    const body: Record<string, string> = { identifier, otp_code: otpCode };
    if (profile?.fullName?.trim()) body.full_name = profile.fullName.trim();
    if (profile?.username?.trim()) body.username = profile.username.trim().replace(/^@/, '').toLowerCase();
    const response = await apiFetch<{ access_token: string; refresh_token: string }>(`${API_ORIGIN}/auth/verify-otp`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    setAuthToken(response.access_token);
    try {
      window.localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token);
    } catch {
      // Storage may be disabled; the access token still works for the session.
    }
  },

  async logout(): Promise<void> {
    const refreshToken = typeof window !== 'undefined' ? window.localStorage.getItem(REFRESH_TOKEN_KEY) : null;
    try {
      await apiFetch(`${API_ORIGIN}/auth/logout`, {
        method: 'POST',
        body: JSON.stringify(refreshToken ? { refresh_token: refreshToken } : {}),
      });
    } finally {
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem('spreego_token');
        window.localStorage.removeItem(REFRESH_TOKEN_KEY);
        window.dispatchEvent(new Event('spreego-auth-changed'));
      }
    }
  },
};

function resolveUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (API_ORIGIN) return `${API_ORIGIN}${path}`;
  if (typeof window !== 'undefined' && window.location?.origin && window.location.origin !== 'null' && !window.location.origin.includes('undefined')) {
    return `${window.location.origin}${path}`;
  }
  return `http://localhost:8000${path}`;
}

function resolveMediaAssetUrl(path: string | undefined): string {
  if (!path) return '';
  return path.startsWith('http://') || path.startsWith('https://') ? path : resolveUrl(path);
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
  if (TEST_MODE && !hasMockedFetch()) {
    throw new ApiError('Test mode uses local fallback data.', 0);
  }
  const token = getAuthToken();
  const customHeaders = (options.headers as Record<string, string>) || {};
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
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
  if (TEST_MODE && !hasMockedFetch()) return fallbackData;
  try {
    return await apiFetch<T>(url, options);
  } catch (err) {
    // Fallback for network/offline (0), missing endpoint (404), or server 500 in demo mode
    const apiErr = err as ApiError;
    const method = (options.method || 'GET').toUpperCase();
    const isReadRequest = method === 'GET' || method === 'HEAD';
    if ((TEST_MODE || (OFFLINE_FALLBACKS_ENABLED && isReadRequest)) && (apiErr.status === 0 || apiErr.status === 404 || apiErr.status >= 500)) {
      console.info(`[SPREEGO API] Fallback used for ${url}:`, apiErr.message);
      return fallbackData;
    }
    throw err;
  }
}

const DEFAULT_AVATAR = 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150';
const DEFAULT_THUMBNAIL = 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800';

function normalizeCreator(raw: any, fallbackId = 'usr_creator'): UserProfile {
  const source = raw?.profile || raw || {};
  const username = String(
    source.username || source.handle?.replace(/^@/, '') || `creator_${fallbackId.slice(0, 6)}`,
  );

  return {
    id: String(source.id || raw?.id || fallbackId),
    username,
    handle: source.handle || `@${username}`,
    display_name: source.display_name || source.full_name || username,
    avatar_url: source.avatar_url || DEFAULT_AVATAR,
    bio: source.bio,
    is_verified: source.is_verified ?? raw?.is_verified,
    follower_count: source.follower_count ?? source.followers_count ?? 0,
    following_count: source.following_count ?? source.following_count ?? 0,
    post_count: source.post_count ?? source.posts_count ?? 0,
  };
}

function normalizeSpreeItem(raw: any): SpreeItem {
  const metrics = raw?.metrics || {};
  const creatorId = String(raw?.creator_id || raw?.creator?.id || 'usr_creator');
  const backendType = raw?.type;
  const type = backendType === 'VIDEO_LONG' ? 'LONG_VIDEO' : backendType;

  return {
    ...raw,
    id: String(raw?.id || ''),
    creator_id: creatorId,
    creator: normalizeCreator(raw?.creator, creatorId),
    title: raw?.title || 'Untitled Spree',
    caption: raw?.caption ?? raw?.description ?? raw?.title ?? '',
    media_url: resolveMediaAssetUrl(raw?.media_url),
    thumbnail_url: resolveMediaAssetUrl(raw?.thumbnail_url || raw?.media_url || DEFAULT_THUMBNAIL),
    type: type || 'VIDEO_SHORT',
    duration_seconds: raw?.duration_seconds ?? raw?.duration,
    tags: Array.isArray(raw?.tags) ? raw.tags : [],
    views_count: raw?.views_count ?? metrics.views_count ?? 0,
    claps_count: raw?.claps_count ?? metrics.claps_count ?? raw?.clap_count ?? 0,
    comments_count: raw?.comments_count ?? metrics.comments_count ?? raw?.comment_count ?? 0,
    shares_count: raw?.shares_count ?? metrics.shares_count ?? raw?.share_count ?? 0,
    saves_count: raw?.saves_count ?? metrics.saves_count ?? raw?.save_count ?? 0,
    created_at: raw?.created_at || new Date(0).toISOString(),
  };
}

function normalizeComment(raw: any): CommentItem {
  const userId = String(raw?.user_id || raw?.user?.id || 'usr_creator');
  const commentUser = raw?.user || {
    id: userId,
    username: raw?.username,
    full_name: raw?.full_name,
    avatar_url: raw?.avatar_url,
  };
  return {
    ...raw,
    id: String(raw?.id || `comment_${Date.now()}`),
    spree_id: String(raw?.spree_id || ''),
    user: normalizeCreator(commentUser, userId),
    text: raw?.text || '',
    claps_count: raw?.claps_count ?? 0,
    created_at: raw?.created_at || new Date(0).toISOString(),
  };
}

function normalizeOrder(raw: any): OrderRecord {
  const items = Array.isArray(raw?.items) ? raw.items : [];
  const firstItem = items[0] || {};
  const product = firstItem.product || {};
  const itemCount = items.reduce((total: number, item: any) => total + Number(item?.quantity || 0), 0);
  const title = product.title || raw?.product_title || (items.length > 1 ? `${items.length} products` : 'Order');

  return {
    id: String(raw?.id || ''),
    product_id: String(firstItem.product_id || raw?.product_id || ''),
    product_title: title,
    product_image: resolveMediaAssetUrl(product.images?.[0] || raw?.product_image || DEFAULT_THUMBNAIL),
    price_inr: Number(firstItem.unit_price ?? raw?.price_inr ?? 0),
    quantity: Number(firstItem.quantity ?? raw?.quantity ?? itemCount ?? 1),
    total_amount_inr: Number(raw?.total_amount ?? raw?.total_amount_inr ?? 0),
    status: raw?.status || 'CREATED',
    created_at: raw?.created_at || new Date(0).toISOString(),
  };
}

function normalizeSubscriptionResult(raw: any): { success: boolean; is_active: boolean } {
  return {
    success: raw?.success ?? raw?.status === 'ACTIVE',
    is_active: raw?.is_active ?? raw?.status === 'ACTIVE',
  };
}

function normalizePayoutResult(
  raw: any,
  amount: number,
  upiId: string,
): { success: boolean; transaction_id: string; message: string } {
  if (raw?.success !== undefined || raw?.transaction_id) {
    return raw;
  }

  const transactionId = String(raw?.id || `txn_${Date.now()}`);
  return {
    success: true,
    transaction_id: transactionId,
    message: `Payout of ₹${amount.toLocaleString()} initiated to ${upiId}`,
  };
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

    return raw.map(normalizeSpreeItem);
  },

  async getExploreItems(
    category: string = 'all',
    query: string = '',
    subTab: string = 'for_you'
  ): Promise<SpreeItem[]> {
    const typeMap: Record<string, string> = {
      photos: 'PHOTO',
      videos: 'VIDEO_SHORT',
      long_videos: 'LONG_VIDEO',
    };
    const backendTypeMap: Record<string, string> = {
      photos: 'PHOTO',
      videos: 'VIDEO_SHORT',
      long_videos: 'VIDEO_LONG',
    };
    let items = [...mockExploreItems];
    if (category !== 'all') {
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

    const params = new URLSearchParams({ tab: subTab });
    const mappedType = backendTypeMap[category];
    if (mappedType) params.set('type', mappedType);
    if (query.trim()) params.set('q', query.trim());

    const raw = await safeFetch<any[]>(
      `${BASE_URL}/sprees?${params.toString()}`,
      { method: 'GET' },
      items
    );

    return raw.map(normalizeSpreeItem);
  },

  async getSpreeById(id: string): Promise<SpreeItem | null> {
    const fallback = mockExploreItems.find((s) => s.id === id) || mockSprees[0] || null;
    const raw = await safeFetch<any>(
      `${BASE_URL}/sprees/${id}`,
      { method: 'GET' },
      fallback
    );
    return raw ? normalizeSpreeItem(raw) : null;
  },

  async getCreatorSprees(creatorId: string): Promise<SpreeItem[]> {
    const raw = await safeFetch<any[]>(
      `${BASE_URL}/sprees?creator_id=${encodeURIComponent(creatorId)}`,
      { method: 'GET' },
      mockExploreItems.filter((item) => item.creator_id === creatorId)
    );
    return raw.map(normalizeSpreeItem);
  },

  async createSpree(payload: {
    type: 'VIDEO_SHORT' | 'VIDEO_LONG' | 'PHOTO' | 'SERIES';
    title: string;
    description?: string;
    media_url: string;
    thumbnail_url?: string;
    duration?: number;
    visibility?: 'PUBLIC' | 'FOLLOWERS_ONLY' | 'PRIVATE';
    category?: string;
    tags?: string[];
  }): Promise<SpreeItem> {
    const raw = await apiFetch<any>(`${BASE_URL}/sprees`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return normalizeSpreeItem(raw);
  },

  async clapSpree(id: string): Promise<{ success: boolean; newCount: number }> {
    const item = mockSprees.find((s) => s.id === id);
    const count = item ? item.claps_count + 1 : 12401;
    const raw = await safeFetch<any>(
      `${BASE_URL}/sprees/${id}/clap`,
      { method: 'POST' },
      { success: true, newCount: count }
    );
    return {
      success: raw?.success ?? raw?.clapped ?? true,
      newCount: raw?.newCount ?? raw?.new_count ?? count,
    };
  },

  async saveSpree(id: string): Promise<{ success: boolean; saved: boolean }> {
    return safeFetch<{ success: boolean; saved: boolean }>(
      `${BASE_URL}/sprees/${id}/save`,
      { method: 'POST' },
      { success: true, saved: true }
    );
  },

  async unsaveSpree(id: string): Promise<{ success: boolean; saved: boolean }> {
    return apiFetch<{ success: boolean; saved: boolean }>(
      `${BASE_URL}/sprees/${id}/save`,
      { method: 'DELETE' }
    );
  },

  async shareSpree(id: string, platform: string = 'web'): Promise<{ success: boolean; shareUrl: string }> {
    const raw = await safeFetch<any>(
      `${BASE_URL}/sprees/${id}/share`,
      { method: 'POST', body: JSON.stringify({ platform }) },
      { success: true, shareUrl: `https://spreego.app/s/${id}` }
    );
    return {
      success: raw?.success ?? true,
      shareUrl: raw?.shareUrl || raw?.share_url || `https://spreego.app/s/${id}`,
    };
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

    const raw = await safeFetch<any[]>(
      `${BASE_URL}/sprees/${spreeId}/comments`,
      { method: 'GET' },
      fallback
    );
    return raw.map(normalizeComment);
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

    const raw = await safeFetch<any>(
      `${BASE_URL}/sprees/${spreeId}/comments`,
      { method: 'POST', body: JSON.stringify({ text }) },
      fallback
    );
    return normalizeComment(raw);
  },

  async sendViewTelemetry(
    payload: ViewTelemetryPayload & { spree_id: string },
    requestOptions: Pick<RequestInit, 'keepalive'> = {}
  ): Promise<{ success: boolean }> {
    const raw = await safeFetch<any>(
      `${BASE_URL}/sprees/${payload.spree_id}/view`,
      {
        method: 'POST',
        ...requestOptions,
        body: JSON.stringify({
          watch_duration: payload.watch_duration,
          completed: payload.completed,
          device_info: payload.device_info || 'Web/Desktop Chrome',
        }),
      },
      { success: true }
    );
    return { success: raw?.success ?? true };
  },
};

/* =====================================================================
   MEDIA UPLOAD API
===================================================================== */
export const uploadApi = {
  async directUpload(file: File, purpose: 'spree_video' | 'spree_thumbnail'): Promise<{
    file_id: string;
    status: string;
    media_url: string;
    file_name: string;
    original_name: string;
    content_type: string;
    file_size: number;
    purpose: string;
  }> {
    const body = new FormData();
    body.append('file', file);
    body.append('purpose', purpose);
    return apiFetch(`${BASE_URL}/uploads/direct`, { method: 'POST', body });
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
      if (OFFLINE_FALLBACKS_ENABLED && (apiErr.status === 0 || apiErr.status >= 500)) {
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
      if (OFFLINE_FALLBACKS_ENABLED && (apiErr.status === 0 || apiErr.status === 404 || apiErr.status >= 500)) {
        const fallback = mockOpens.find((o) => o.id === id) || mockOpens[0];
        return fallback;
      }
      throw err;
    }
  },

  async joinChallenge(challengeId: string): Promise<JoinOpenResponse> {
    const res = await safeFetch<JoinOpenResponse>(`${BASE_URL}/opens/${challengeId}/join`, {
      method: 'POST',
    }, {
      success: true,
      message: 'Successfully joined the open.',
      open_id: challengeId,
      user_id: 'usr_demo',
      joined_at: new Date().toISOString(),
    });
    return { ...res, success: true };
  },

  async submitSpree(openId: string, spreeId: string): Promise<OpenSubmissionResponse> {
    return await safeFetch<OpenSubmissionResponse>(`${BASE_URL}/opens/${openId}/submissions`, {
      method: 'POST',
      body: JSON.stringify({ spree_id: spreeId }),
    }, {
      id: `submission_${Date.now()}`,
      open_id: openId,
      user_id: 'usr_demo',
      spree_id: spreeId,
      score: 0,
      created_at: new Date().toISOString(),
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
      const items = await apiFetch<any[]>(`${BASE_URL}/opens/${openId}/feed${qs}`, {
        method: 'GET',
      });
      return items.map(normalizeSpreeItem);
    } catch (err) {
      const apiErr = err as ApiError;
      if (OFFLINE_FALLBACKS_ENABLED && (apiErr.status === 0 || apiErr.status >= 500)) {
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
        spree: item.spree ? normalizeSpreeItem(item.spree) : item.spree,
        username: item.creator?.full_name || item.creator?.username || item.username || item.user_id,
        handle: item.creator?.username ? `@${item.creator.username}` : item.handle || `@user_${item.user_id.slice(0, 6)}`,
        avatar: item.creator?.avatar_url || item.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150',
        spree_thumbnail: item.spree?.thumbnail_url || item.spree_thumbnail || 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=300',
      }));
    } catch (err) {
      const apiErr = err as ApiError;
      if (OFFLINE_FALLBACKS_ENABLED && (apiErr.status === 0 || apiErr.status >= 500)) {
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
      if (OFFLINE_FALLBACKS_ENABLED && (apiErr.status === 0 || apiErr.status >= 500)) {
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

    const normalizedItems = rawItems.map((p: any) => ({
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

    return category === 'digital'
      ? normalizedItems.filter((product) => product.is_digital)
      : normalizedItems;
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
        price_inr: plan.price ?? plan.monthly_price ?? mockCommunityPass.price_inr,
        interval: plan.billing_period || plan.interval || 'month',
        description: plan.description || mockCommunityPass.description,
        benefits: plan.perks || plan.benefits || mockCommunityPass.benefits,
        is_active: plan.is_active ?? true,
      };
    }
    return mockCommunityPass;
  },

  async subscribeCommunityPass(planId: string = 'pass_free_community'): Promise<{ success: boolean; is_active: boolean }> {
    const raw = await safeFetch<any>(
      `${BASE_URL}/memberships/subscribe`,
      { method: 'POST', body: JSON.stringify({ plan_id: planId }) },
      { success: true, is_active: true }
    );
    return normalizeSubscriptionResult(raw);
  },

  async getOrders(): Promise<OrderRecord[]> {
    const raw = await safeFetch<any[]>(
      `${BASE_URL}/orders/my`,
      { method: 'GET' },
      mockOrders
    );
    return raw.map(normalizeOrder);
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

    const raw = await safeFetch<any>(
      `${BASE_URL}/orders`,
      {
        method: 'POST',
        body: JSON.stringify({
          items: [{ product_id: productId, quantity }],
        }),
      },
      fallback
    );
    return normalizeOrder(raw);
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
    const raw = await safeFetch<any>(
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
    return normalizePayoutResult(raw, amount, upiId);
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
    const raw = await safeFetch<any>(
      `${BASE_URL}/users/${id}`,
      { method: 'GET' },
      mockCurrentUser
    );
    return normalizeCreator(raw, id);
  },

  async followUser(id: string): Promise<{ success: boolean; message: string }> {
    const raw = await safeFetch<any>(
      `${BASE_URL}/users/${id}/follow`,
      { method: 'POST' },
      { success: true, message: 'Followed creator successfully' }
    );
    return { success: raw?.success ?? true, message: raw?.message || 'Followed creator successfully' };
  },

  async unfollowUser(id: string): Promise<{ success: boolean; message: string }> {
    const raw = await apiFetch<any>(
      `${BASE_URL}/users/${id}/follow`,
      { method: 'DELETE' }
    );
    return { success: raw?.success ?? true, message: raw?.message || 'Unfollowed creator successfully' };
  },

  async updateCurrentUser(payload: {
    display_name?: string;
    username?: string;
    bio?: string;
    avatar_url?: string;
  }): Promise<UserProfile> {
    const res = await apiFetch<any>(`${BASE_URL}/users/me`, {
      method: 'PATCH',
      body: JSON.stringify({
        full_name: payload.display_name,
        username: payload.username,
        bio: payload.bio,
        avatar_url: payload.avatar_url,
      }),
    });
    return {
      ...mockCurrentUser,
      ...res,
      username: res.username || mockCurrentUser.username,
      handle: `@${res.username || mockCurrentUser.username}`,
      display_name: res.full_name || mockCurrentUser.display_name,
      avatar_url: res.avatar_url || mockCurrentUser.avatar_url,
      bio: res.bio || '',
      follower_count: res.followers_count ?? mockCurrentUser.follower_count,
      following_count: res.following_count ?? mockCurrentUser.following_count,
    };
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
    const raw = await safeFetch<any>(
      `${BASE_URL}/notifications/read-all`,
      { method: 'POST' },
      { success: true }
    );
    return { success: raw?.success ?? true };
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
