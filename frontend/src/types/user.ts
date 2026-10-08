export interface StoryItem {
  id: string;
  media_url: string;
  type: 'image' | 'video';
  caption?: string;
  timestamp: string;
  location?: string;
}

export interface StoryHighlightItem {
  id: string;
  title: string;
  cover_url: string;
  stories: StoryItem[];
}

export interface UserProfile {
  id: string;
  username: string;
  handle: string;
  display_name: string;
  bio?: string;
  avatar_url: string;
  is_verified?: boolean;
  trust_score?: number; // e.g. 98.4%
  location?: string;
  spreemates_count?: number;
  follower_count: number;
  following_count: number;
  post_count: number;
  story_highlights?: StoryHighlightItem[];
  created_at?: string;
}

export interface UserStats {
  post_count: number;
  follower_count: number;
  following_count: number;
  spreemates_count?: number;
}

export interface NotificationItem {
  id: string;
  type: 'CLAP' | 'COMMENT' | 'BUZZER' | 'DROP' | 'MISSION' | 'OPEN' | 'SYSTEM';
  title: string;
  message: string;
  actor_name?: string;
  actor_avatar?: string;
  created_at: string;
  is_read: boolean;
  reward_badge?: string;
  action_url?: string;
}

export interface ClubItem {
  id: string;
  name: string;
  tagline: string;
  icon: string;
  cover_image: string;
  members_count: number;
  posts_count: number;
  category: string;
  is_joined: boolean;
  active_drop?: {
    title: string;
    reward: string;
    expires_in: string;
  };
  pinned_thread?: string;
  top_creators?: Array<{
    name: string;
    avatar: string;
  }>;
}

export interface MomentsPage {
  id: string;
  book_title: string;
  page_number: number;
  image_url: string;
  text: string;
  date: string;
}

export interface CollageThreadItem {
  id: string;
  title: string;
  creator_name: string;
  creator_avatar: string;
  collaborators_count: number;
  layers_count: number;
  cover_url: string;
  tags: string[];
}
