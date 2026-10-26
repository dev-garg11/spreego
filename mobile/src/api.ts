export interface Creator {
  id: string;
  username: string;
  handle: string;
  display_name: string;
  avatar_url: string;
}

export interface FeedItem {
  id: string;
  title: string;
  caption?: string;
  media_url: string;
  thumbnail_url: string;
  type: string;
  creator: Creator;
  claps_count: number;
  comments_count: number;
  shares_count: number;
  views_count: number;
  sponsored?: boolean;
}

export interface OpenItem {
  id: string;
  title: string;
  description?: string | null;
  cover_image_url?: string | null;
  status: string;
  participants_count: number;
  submissions_count: number;
}

export const DEMO_USER: Creator & { follower_count: number; following_count: number; post_count: number } = {
  id: 'demo-user',
  username: 'aarav_fitness',
  handle: '@aarav_fitness',
  display_name: 'Aarav Sharma',
  avatar_url: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=240&q=80',
  follower_count: 12400,
  following_count: 180,
  post_count: 248,
};

const DEMO_FEED: FeedItem[] = [
  { id: 'demo-1', title: 'Golden hour, quiet mind', caption: 'A slow evening above the city.', media_url: 'https://images.unsplash.com/photo-1500534623283-312aade485b7?w=1200&q=85', thumbnail_url: 'https://images.unsplash.com/photo-1500534623283-312aade485b7?w=1200&q=85', type: 'PHOTO', creator: DEMO_USER, claps_count: 1240, comments_count: 42, shares_count: 18, views_count: 18400 },
  { id: 'demo-2', title: 'Move with intention', caption: 'Small habits become cinematic days.', media_url: 'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1200&q=85', thumbnail_url: 'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1200&q=85', type: 'PHOTO', creator: { ...DEMO_USER, id: 'demo-maya', username: 'maya.crafts', handle: '@maya.crafts', display_name: 'Maya Crafts', avatar_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=240&q=80' }, claps_count: 874, comments_count: 28, shares_count: 12, views_count: 9200 },
];

export const API_ORIGIN = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export function mediaUrl(value?: string | null) {
  if (!value) return '';
  if (value.startsWith('http://') || value.startsWith('https://')) return value;
  return `${API_ORIGIN}${value.startsWith('/') ? value : `/${value}`}`;
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(`${API_ORIGIN}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = typeof body?.detail === 'string' ? body.detail : body?.message;
      throw new Error(detail || `Request failed (${response.status})`);
    }
    return body as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

function normalizeCreator(value: any): Creator {
  const username = value?.username || value?.handle?.replace(/^@/, '') || 'spreego_creator';
  return {
    id: String(value?.id || 'creator'),
    username,
    handle: value?.handle || `@${username}`,
    display_name: value?.display_name || value?.full_name || username,
    avatar_url: mediaUrl(value?.avatar_url || DEMO_USER.avatar_url),
  };
}

function normalizeFeedItem(value: any): FeedItem {
  return {
    id: String(value?.id),
    title: value?.title || 'Untitled Spree',
    caption: value?.caption || value?.description || undefined,
    media_url: mediaUrl(value?.media_url),
    thumbnail_url: mediaUrl(value?.thumbnail_url || value?.media_url),
    type: value?.type === 'VIDEO_LONG' ? 'LONG_VIDEO' : value?.type || 'PHOTO',
    creator: normalizeCreator(value?.creator || value?.user || { id: value?.creator_id }),
    claps_count: Number(value?.claps_count || 0),
    comments_count: Number(value?.comments_count || 0),
    shares_count: Number(value?.shares_count || 0),
    views_count: Number(value?.views_count || 0),
    sponsored: Boolean(value?.sponsored),
  };
}

function normalizeOpen(value: any): OpenItem {
  return {
    id: String(value?.id),
    title: value?.title || 'Community Open',
    description: value?.description,
    cover_image_url: value?.cover_image_url ? mediaUrl(value.cover_image_url) : null,
    status: value?.status || 'ACTIVE',
    participants_count: Number(value?.participants_count || 0),
    submissions_count: Number(value?.submissions_count || 0),
  };
}

export { DEMO_FEED };

export const api = {
  async getFeed(): Promise<FeedItem[]> {
    try {
      const response = await request<any[]>('/api/v1/sprees/feed?tab=for_you');
      return response.map(normalizeFeedItem);
    } catch {
      return DEMO_FEED;
    }
  },

  async getOpens(): Promise<OpenItem[]> {
    try {
      const response = await request<any[]>('/api/v1/opens?status=ACTIVE');
      return response.map(normalizeOpen);
    } catch {
      return [];
    }
  },

  async login(identifier: string, password: string) {
    return request<{ access_token: string; refresh_token?: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ identifier, password }),
    });
  },

  async clap(id: string, token: string) {
    const response = await request<any>(`/api/v1/sprees/${id}/clap`, { method: 'POST' }, token);
    return { newCount: Number(response?.newCount || response?.new_count || 0) };
  },

  async publishMedia(token: string, file: { uri: string; name: string; type: string }) {
    const formData = new FormData();
    formData.append('file', { uri: file.uri, name: file.name, type: file.type } as unknown as Blob);
    formData.append('purpose', file.type.startsWith('video') ? 'spree_video' : 'spree_thumbnail');
    const uploaded = await request<any>('/api/v1/uploads/direct', { method: 'POST', body: formData }, token);
    return request('/api/v1/sprees', {
      method: 'POST',
      body: JSON.stringify({
        type: file.type.startsWith('video') ? 'VIDEO_SHORT' : 'PHOTO',
        title: file.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' '),
        media_url: uploaded.media_url,
        thumbnail_url: file.type.startsWith('video') ? undefined : uploaded.media_url,
        visibility: 'PUBLIC',
      }),
    }, token);
  },
};
