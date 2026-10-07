import { UserProfile } from './user';
import { SpreeItem } from './spree';

export type OpenType = 'CHALLENGE' | 'COMPETITION' | 'SPONSORED';
export type OpenStatus = 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED';

export interface Open {
  id: string;
  creator_id: string;
  type: OpenType;
  title: string;
  description?: string | null;
  cover_image_url?: string | null;
  rules?: string[] | null;
  start_at: string;
  end_at: string;
  status: OpenStatus;
  reward_info?: string | null;
  max_participants?: number | null;
  scoring_config: Record<string, number>;
  participants_count: number;
  submissions_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;

  // Optional UI helper properties
  badge_label?: string;
  days_left?: number;
  creator?: UserProfile | null;
  mode?: string;
  category?: string;
  reward_pool_amount?: number;
  reward_pool_currency?: string;
  sponsor_name?: string;
}

// Backward-compatible alias
export type OpenChallenge = Open;

export interface OpenRankingItem {
  rank: number;
  score: number;
  submission_id: string;
  spree_id: string;
  user_id: string;
  creator_id: string;
  creator?: {
    id: string;
    username?: string | null;
    full_name?: string | null;
    avatar_url?: string | null;
  } | null;
  spree?: SpreeItem | null;
  spree_title?: string | null;
  metrics?: {
    views_count: number;
    completed_views_count: number;
    watch_completion_rate: number;
    claps_count: number;
    comments_count: number;
    saves_count: number;
    shares_count: number;
  } | null;
  created_at?: string | null;

  // UI convenience aliases
  username?: string;
  avatar?: string;
  handle?: string;
  spree_thumbnail?: string;
}

export interface JoinOpenResponse {
  message: string;
  open_id: string;
  user_id: string;
  joined_at?: string | null;
  success?: boolean;
}

export interface OpenSubmissionResponse {
  id: string;
  open_id: string;
  user_id: string;
  spree_id: string;
  score: number;
  rank?: number | null;
  created_at: string;
}

export interface CreateOpenPayload {
  type?: OpenType;
  title: string;
  description?: string | null;
  cover_image_url?: string | null;
  rules?: string[] | null;
  start_at?: string | null;
  end_at: string;
  status?: OpenStatus;
  reward_info?: string | null;
  max_participants?: number | null;
  scoring_config?: Record<string, number> | null;
}

export interface BrandCampaign {
  id: string;
  brand_name: string;
  brand_logo_url: string;
  campaign_title: string;
  hero_image_url: string;
  headline: string;
  description: string;
  reward_pool: string;
  duration_days: number;
  winners_quota: number;
  about_brand: string;
  is_demo?: boolean;
}
