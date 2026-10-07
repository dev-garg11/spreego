import { UserProfile } from './user';

export type SpreeType = 'VIDEO_SHORT' | 'PHOTO' | 'LONG_VIDEO' | 'MOMENT' | 'COLLAGE';

export type FeedSubTab = 'for_you' | 'following' | 'clubs';

export type ExploreSubTab = 'for_you' | 'trending' | 'following';

export type CategoryFilterChip = 'all' | 'photos' | 'videos' | 'long_videos';

export interface SponsoredBadge {
  brand_name: string;
  tagline: string;
  cta_text: string;
  cta_link?: string;
  logo_url?: string;
}

export interface SpreeItem {
  id: string;
  creator_id: string;
  creator: UserProfile;
  title: string;
  caption?: string;
  media_url: string;
  thumbnail_url: string;
  type: SpreeType;
  duration_seconds?: number;
  audio_title?: string;
  audio_artist?: string;
  claps_count: number;
  comments_count: number;
  shares_count: number;
  saves_count: number;
  views_count: number;
  has_clapped?: boolean;
  has_saved?: boolean;
  sponsored?: SponsoredBadge;
  tags?: string[];
  created_at: string;
}

export interface CommentItem {
  id: string;
  spree_id: string;
  user: UserProfile;
  text: string;
  claps_count: number;
  created_at: string;
}

export interface ViewTelemetryPayload {
  watch_duration: number;
  completed: boolean;
  device_info?: string;
}
