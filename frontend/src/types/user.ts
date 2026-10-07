export interface UserProfile {
  id: string;
  username: string;
  handle: string;
  display_name: string;
  bio?: string;
  avatar_url: string;
  is_verified?: boolean;
  location?: string;
  follower_count: number;
  following_count: number;
  post_count: number;
  story_highlights?: Array<{
    id: string;
    title: string;
    cover_url: string;
  }>;
  created_at?: string;
}

export interface UserStats {
  post_count: number;
  follower_count: number;
  following_count: number;
}
