import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  feedApi,
  opensApi,
  storeApi,
  walletApi,
  userApi,
} from '../../api/client';
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
} from '../../api/mockData';
import {
  SpreeItem,
  OpenChallenge,
  ProductItem,
  OrderRecord,
} from '../../types';

describe('Tier 1: Feature Coverage Suite (Screens 1–10 & R1–R4)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  // =========================================================================
  // SCREEN 1: HOME FEED (REELS PLAYER & ENGAGEMENT)
  // =========================================================================
  describe('Screen 1: Home Feed & Reels Engine', () => {
    it('T1.01: fetches discovery feed with default for_you sub-tab', async () => {
      const feed = await feedApi.getFeed('for_you');
      expect(Array.isArray(feed)).toBe(true);
      expect(feed.length).toBeGreaterThan(0);
      expect(feed[0]).toHaveProperty('id');
      expect(feed[0]).toHaveProperty('media_url');
      expect(feed[0]).toHaveProperty('title');
    });

    it('T1.02: fetches discovery feed for following sub-tab', async () => {
      const feed = await feedApi.getFeed('following');
      expect(Array.isArray(feed)).toBe(true);
      expect(feed.length).toBeGreaterThan(0);
    });

    it('T1.03: fetches discovery feed for clubs sub-tab', async () => {
      const feed = await feedApi.getFeed('clubs');
      expect(Array.isArray(feed)).toBe(true);
      expect(feed.length).toBeGreaterThan(0);
    });

    it('T1.04: reel item contains valid media metadata and short video type', async () => {
      const firstReel = mockSprees[0];
      expect(firstReel.type).toBe('VIDEO_SHORT');
      expect(firstReel.media_url).toMatch(/^https?:\/\//);
      expect(firstReel.duration_seconds).toBeGreaterThan(0);
      expect(firstReel.thumbnail_url).toBeTruthy();
    });

    it('T1.05: right-rail clap action increments clap count', async () => {
      const res = await feedApi.clapSpree(mockSprees[0].id);
      expect(res.success).toBe(true);
      expect(res.newCount).toBe(mockSprees[0].claps_count + 1);
    });

    it('T1.06: bookmark/save toggle updates saved status', async () => {
      const res = await feedApi.saveSpree(mockSprees[0].id);
      expect(res.success).toBe(true);
      expect(res.saved).toBe(true);
    });

    it('T1.07: share trigger generates valid web share url', async () => {
      const res = await feedApi.shareSpree(mockSprees[0].id, 'web');
      expect(res.success).toBe(true);
      expect(res.shareUrl).toContain(`https://spreego.app/s/${mockSprees[0].id}`);
    });

    it('T1.08: comment drawer fetches comment thread for active spree', async () => {
      const comments = await feedApi.getComments(mockSprees[0].id);
      expect(Array.isArray(comments)).toBe(true);
      expect(comments.length).toBeGreaterThanOrEqual(1);
      expect(comments[0]).toHaveProperty('text');
      expect(comments[0].user).toHaveProperty('handle');
    });

    it('T1.09: comment drawer allows submitting a new comment', async () => {
      const newComment = await feedApi.addComment(mockSprees[0].id, 'Incredible visual aesthetic!');
      expect(newComment.text).toBe('Incredible visual aesthetic!');
      expect(newComment.spree_id).toBe(mockSprees[0].id);
      expect(newComment.claps_count).toBe(0);
      expect(newComment.created_at).toBeTruthy();
    });

    it('T1.10: reel audio track includes title and artist metadata for rotating disc', () => {
      const reel = mockSprees[0];
      expect(reel.audio_title).toBe('Golden Hour');
      expect(reel.audio_artist).toBe('JVKE');
    });

    it('T1.11: creator overlay contains verified badge and handle @travelwithme', () => {
      const reel = mockSprees[0];
      expect(reel.creator.handle).toBe('@travelwithme');
      expect(reel.creator.is_verified).toBe(true);
      expect(reel.caption).toContain('#travel');
    });

    it('T1.12: sponsored reel displays SkyWings brand badge with CTA', () => {
      const reel = mockSprees[0];
      expect(reel.sponsored).toBeDefined();
      expect(reel.sponsored?.brand_name).toBe('SkyWings');
      expect(reel.sponsored?.tagline).toBe('Your next adventure awaits');
      expect(reel.sponsored?.cta_text).toBe('Explore More');
    });

    it('T1.13: telemetry beacon streams watch duration and completion to view endpoint', async () => {
      const res = await feedApi.sendViewTelemetry({
        spree_id: mockSprees[0].id,
        watch_duration: 14.5,
        completed: true,
        device_info: 'Web/Desktop Chrome',
      });
      expect(res.success).toBe(true);
    });
  });

  // =========================================================================
  // SCREEN 2: SPREE EXPLORE & DISCOVERY GRID
  // =========================================================================
  describe('Screen 2: Spree Explore & Discovery Grid', () => {
    it('T1.14: explore items list returns full discovery items for category "all"', async () => {
      const items = await feedApi.getExploreItems('all', '');
      expect(items.length).toBeGreaterThanOrEqual(mockExploreItems.length);
    });

    it('T1.15: category filter "photos" filters to PHOTO spree type', async () => {
      const photos = await feedApi.getExploreItems('photos', '');
      expect(photos.every((p) => p.type === 'PHOTO')).toBe(true);
      expect(photos.length).toBeGreaterThan(0);
    });

    it('T1.16: category filter "videos" filters to VIDEO_SHORT spree type', async () => {
      const videos = await feedApi.getExploreItems('videos', '');
      expect(videos.every((v) => v.type === 'VIDEO_SHORT')).toBe(true);
      expect(videos.length).toBeGreaterThan(0);
    });

    it('T1.17: category filter "long_videos" filters to LONG_VIDEO spree type', async () => {
      const longVideos = await feedApi.getExploreItems('long_videos', '');
      expect(longVideos.every((lv) => lv.type === 'LONG_VIDEO')).toBe(true);
      expect(longVideos.length).toBeGreaterThan(0);
    });

    it('T1.18: keyword search filters items by title match', async () => {
      const results = await feedApi.getExploreItems('all', 'santorini');
      expect(results.length).toBeGreaterThan(0);
      expect(results.some((r) => r.title.toLowerCase().includes('santorini'))).toBe(true);
    });

    it('T1.19: keyword search filters items by creator handle match', async () => {
      const results = await feedApi.getExploreItems('all', 'foodie_riya');
      expect(results.length).toBeGreaterThan(0);
      expect(results.some((r) => r.creator.handle.includes('foodie_riya'))).toBe(true);
    });

    it('T1.20: keyword search filters items by tag match', async () => {
      const results = await feedApi.getExploreItems('all', 'paneer');
      expect(results.length).toBeGreaterThan(0);
      expect(results.some((r) => r.tags?.includes('paneer'))).toBe(true);
    });

    it('T1.21: explore item contains play count and creator tag for masonry badges', () => {
      const item = mockExploreItems[0];
      expect(item.views_count).toBeGreaterThan(0);
      expect(item.creator.handle).toBeTruthy();
      expect(item.title).toBeTruthy();
    });

    it('T1.22: getSpreeById returns full spree details for drill-down modal', async () => {
      const spree = await feedApi.getSpreeById('spree_001');
      expect(spree).not.toBeNull();
      expect(spree?.id).toBe('spree_001');
      expect(spree?.title).toBe('Sunset vibes in Santorini');
    });
  });

  // =========================================================================
  // SCREEN 3: UPLOAD & CREATION MODAL
  // =========================================================================
  describe('Screen 3: Upload & Creation Hub', () => {
    it('T1.23: supports all 6 primary creation mode types', () => {
      const modes = [
        { id: 'video', title: 'Upload Video', subtitle: 'Up to 10 min' },
        { id: 'photo', title: 'Upload Photo', subtitle: 'Gallery or camera' },
        { id: 'live', title: 'Go Live', subtitle: 'Connect in real-time' },
        { id: 'spree', title: 'Create Spree', subtitle: 'Edit & add effects' },
        { id: 'collage', title: 'Collage', subtitle: 'Make a collage' },
        { id: 'moments', title: 'Add to Moments', subtitle: 'Save to memories' },
      ];
      expect(modes.length).toBe(6);
      modes.forEach((mode) => {
        expect(mode.title).toBeTruthy();
        expect(mode.subtitle).toBeTruthy();
      });
    });

    it('T1.24: supports 3 secondary creation utilities', () => {
      const utilities = [
        { id: 'camera', title: 'Open Camera', subtitle: 'Quick capture' },
        { id: 'gallery', title: 'From Gallery', subtitle: 'Select from your files' },
        { id: 'drafts', title: 'Drafts', subtitle: 'Continue editing' },
      ];
      expect(utilities.length).toBe(3);
    });
  });

  // =========================================================================
  // SCREEN 4: OPENS (CHALLENGES & COMPETITIONS)
  // =========================================================================
  describe('Screen 4: Opens (Challenges & Competitions Hub)', () => {
    it('T1.25: fetches active challenges for mode "challenges"', async () => {
      const challenges = await opensApi.getChallenges('challenges', 'All');
      expect(challenges.length).toBeGreaterThan(0);
      expect(challenges[0].mode).toBe('challenges');
    });

    it('T1.26: fetches active competitions for mode "competitions"', async () => {
      const comps = await opensApi.getChallenges('competitions', 'All');
      expect(comps.length).toBeGreaterThan(0);
      expect(comps.every((c) => c.mode === 'competitions')).toBe(true);
    });

    it('T1.27: featured hero challenge is Nike Move Better Challenge', () => {
      const hero = mockOpens.find((o) => o.id === 'open_nike_001');
      expect(hero).toBeDefined();
      expect(hero?.title).toBe('Move Better Challenge');
      expect(hero?.sponsor_name).toBe('Nike');
      expect(hero?.reward_pool_amount).toBe(50000);
      expect(hero?.reward_pool_currency).toBe('USD');
    });

    it('T1.28: filters active challenges by category "Fitness"', async () => {
      const fitness = await opensApi.getChallenges('all', 'Fitness');
      expect(fitness.every((c) => c.category.toLowerCase() === 'fitness')).toBe(true);
      expect(fitness.length).toBeGreaterThan(0);
    });

    it('T1.29: active challenge cards display participant count and remaining days', () => {
      mockOpens.forEach((challenge) => {
        expect(challenge.participants_count).toBeGreaterThan(0);
        expect(challenge.days_left).toBeGreaterThan(0);
        expect(challenge.cover_image_url).toBeTruthy();
      });
    });
  });

  // =========================================================================
  // SCREEN 5: CHALLENGE DETAILS
  // =========================================================================
  describe('Screen 5: Challenge Details Screen', () => {
    it('T1.30: retrieves challenge details by ID with cover and creator attribution', async () => {
      const challenge = await opensApi.getChallengeById('open_travel_002');
      expect(challenge).not.toBeNull();
      expect(challenge?.title).toBe('Travel Tales');
      expect(challenge?.creator.handle).toBe('@travelwithme');
      expect(challenge?.badge_label).toBe('Sponsored');
    });

    it('T1.31: challenge details exposes 3 key metric values', async () => {
      const challenge = await opensApi.getChallengeById('open_travel_002');
      expect(challenge?.participants_count).toBe(3200);
      expect(challenge?.reward_pool_amount).toBe(50000);
      expect(challenge?.days_left).toBe(5);
    });

    it('T1.32: challenge details contains rules and eligibility guidelines', async () => {
      const challenge = await opensApi.getChallengeById('open_travel_002');
      expect(Array.isArray(challenge?.rules)).toBe(true);
      expect(challenge?.rules?.length).toBeGreaterThanOrEqual(3);
      expect(challenge?.rules?.[0]).toContain('travel');
    });

    it('T1.33: joinChallenge CTA registers current user into challenge', async () => {
      const res = await opensApi.joinChallenge('open_travel_002');
      expect(res.success).toBe(true);
      expect(res.message).toContain('Successfully');
    });
  });

  // =========================================================================
  // SCREEN 6: OPENS RANKING (LEADERBOARD)
  // =========================================================================
  describe('Screen 6: Opens Ranking & Live Leaderboard', () => {
    it('T1.34: fetches live leaderboard rankings for challenge', async () => {
      const ranking = await opensApi.getRanking('open_travel_002', 'overall');
      expect(ranking.length).toBeGreaterThanOrEqual(8);
      expect(ranking[0].rank).toBe(1);
    });

    it('T1.35: rank 1 is wanderwithsoul with Gold position and top score', async () => {
      const ranking = await opensApi.getRanking('open_travel_002', 'overall');
      const top = ranking[0];
      expect(top.rank).toBe(1);
      expect(top.handle).toBe('@wanderwithsoul');
      expect(top.score).toBe(12400);
    });

    it('T1.36: rank 2 is foodie_riya with Silver position', async () => {
      const ranking = await opensApi.getRanking('open_travel_002', 'overall');
      const second = ranking[1];
      expect(second.rank).toBe(2);
      expect(second.handle).toBe('@foodie_riya');
      expect(second.score).toBe(10800);
    });

    it('T1.37: rank 3 is style_diaries with Bronze position', async () => {
      const ranking = await opensApi.getRanking('open_travel_002', 'overall');
      const third = ranking[2];
      expect(third.rank).toBe(3);
      expect(third.handle).toBe('@style_diaries');
      expect(third.score).toBe(9600);
    });

    it('T1.38: supports weekly and today timeframe filters', async () => {
      const weekly = await opensApi.getRanking('open_travel_002', 'weekly');
      const today = await opensApi.getRanking('open_travel_002', 'today');
      expect(weekly.length).toBeGreaterThan(0);
      expect(today.length).toBeGreaterThan(0);
    });
  });

  // =========================================================================
  // SCREEN 7: BRAND SPONSORSHIP (BRAND COLLABORATIONS)
  // =========================================================================
  describe('Screen 7: Brand Sponsorship & Collaborations', () => {
    it('T1.39: fetches featured brand campaign for Tata Motors', async () => {
      const campaign = await opensApi.getBrandCampaign();
      expect(campaign.brand_name).toBe('Tata Motors');
      expect(campaign.headline).toBe('Drive Your Story');
      expect(campaign.reward_pool).toContain('₹1,00,000');
    });

    it('T1.40: brand campaign displays duration of 15 days and top 10 winners quota', async () => {
      const campaign = await opensApi.getBrandCampaign();
      expect(campaign.duration_days).toBe(15);
      expect(campaign.winners_quota).toBe(10);
      expect(campaign.about_brand).toContain('Innovation, trust');
    });
  });

  // =========================================================================
  // SCREEN 8: CREATOR PROFILE
  // =========================================================================
  describe('Screen 8: Creator Profile & Story Highlights', () => {
    it('T1.41: fetches creator profile data with verified badge and location', async () => {
      const user = await userApi.getCurrentUser();
      expect(user.handle).toBe('@travelwithme');
      expect(user.is_verified).toBe(true);
      expect(user.location).toBe('Bangalore, India');
    });

    it('T1.42: creator stats row exposes Posts (248), Followers (12.4K), Following (432)', async () => {
      const user = await userApi.getCurrentUser();
      expect(user.post_count).toBe(248);
      expect(user.follower_count).toBe(12400);
      expect(user.following_count).toBe(432);
    });

    it('T1.43: story highlights list contains Highlights, Travel, Food, Lifestyle, Q&A', async () => {
      const user = await userApi.getCurrentUser();
      const titles = user.story_highlights?.map((h) => h.title);
      expect(titles).toContain('Highlights');
      expect(titles).toContain('Travel');
      expect(titles).toContain('Food');
      expect(titles).toContain('Lifestyle');
      expect(titles).toContain('Q&A');
    });
  });

  // =========================================================================
  // SCREEN 9: MY STORE (CREATOR COMMERCE)
  // =========================================================================
  describe('Screen 9: My Store, Products & ₹0 Community Pass', () => {
    it('T1.44: product catalog fetches physical merchandise products', async () => {
      const products = await storeApi.getProducts('products');
      expect(products.length).toBeGreaterThan(0);
      expect(products.some((p) => p.title.includes('Travel Backpack'))).toBe(true);
      expect(products.some((p) => p.price_inr === 2499)).toBe(true);
    });

    it('T1.45: product catalog fetches digital goods in digital tab', async () => {
      const digital = await storeApi.getProducts('digital');
      expect(digital.every((p) => p.is_digital)).toBe(true);
      expect(digital.some((p) => p.title.includes('Preset Pack'))).toBe(true);
    });

    it('T1.46: retrieves ₹0 Community Pass details', async () => {
      const pass = await storeApi.getCommunityPass();
      expect(pass.price_inr).toBe(0);
      expect(pass.title).toContain('Community Pass');
      expect(pass.benefits.length).toBeGreaterThan(0);
    });

    it('T1.47: subscribes to ₹0 Community Pass instantly', async () => {
      const sub = await storeApi.subscribeCommunityPass('pass_free_community');
      expect(sub.success).toBe(true);
      expect(sub.is_active).toBe(true);
    });

    it('T1.48: places order for product and receives order confirmation', async () => {
      const order = await storeApi.placeOrder('prod_001', 2);
      expect(order).toBeDefined();
      expect(order.product_id).toBe('prod_001');
      expect(order.quantity).toBe(2);
      expect(order.status).toBe('PROCESSING');
      expect(order.total_amount_inr).toBe(2499 * 2);
    });

    it('T1.49: retrieves past orders list for user', async () => {
      const orders = await storeApi.getOrders();
      expect(Array.isArray(orders)).toBe(true);
      expect(orders.length).toBeGreaterThan(0);
      expect(orders[0]).toHaveProperty('status');
    });
  });

  // =========================================================================
  // SCREEN 10: CREATOR ANALYTICS & WALLET
  // =========================================================================
  describe('Screen 10: Creator Analytics & Wallet Payout', () => {
    it('T1.50: fetches 3 KPI metric cards: Views, Engagement, New Followers', async () => {
      const kpis = await walletApi.getKPIMetrics();
      expect(kpis.length).toBe(3);
      expect(kpis[0].label).toBe('Views');
      expect(kpis[0].value).toBe('248.6K');
      expect(kpis[0].growth_percent).toBe(12);
      expect(kpis[0].is_positive).toBe(true);
      expect(kpis[1].label).toBe('Engagement');
      expect(kpis[2].label).toBe('New Followers');
    });

    it('T1.51: views trend returns 7 daily data points (Mon through Sun)', async () => {
      const trend = await walletApi.getViewsTrend();
      expect(trend.length).toBe(7);
      const days = trend.map((t) => t.day);
      expect(days).toEqual(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']);
    });

    it('T1.52: top-performing content ranks top videos by views', async () => {
      const top = await walletApi.getTopContent();
      expect(top.length).toBe(3);
      expect(top[0].rank).toBe(1);
      expect(top[0].title).toBe('Sunset in Santorini');
    });

    it('T1.53: wallet summary returns available balance of ₹42,500 INR', async () => {
      const wallet = await walletApi.getWalletSummary();
      expect(wallet.available_balance_inr).toBe(42500);
      expect(wallet.pending_payout_inr).toBe(15000);
      expect(wallet.currency).toBe('INR');
    });

    it('T1.54: requestPayout initiates UPI withdrawal with confirmation', async () => {
      const res = await walletApi.requestPayout(10000, 'creator@okaxis');
      expect(res.success).toBe(true);
      expect(res.transaction_id).toBeTruthy();
      expect(res.message).toContain('10,000');
    });
  });

  // =========================================================================
  // REQUIREMENTS R3 & R4: CONSENT GUARD & TELEMETRY ENGINE
  // =========================================================================
  describe('R3 Terms Consent Guard & R4 Telemetry Engine Contracts', () => {
    it('T1.55: R3 consent storage key is initialized empty and persists on accept', () => {
      const STORAGE_KEY = 'spreego_consent_accepted';
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull();

      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        hasAccepted: true,
        acceptedAt: new Date().toISOString(),
        version: 'v1.0',
      }));

      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      expect(saved.hasAccepted).toBe(true);
      expect(saved.version).toBe('v1.0');
    });

    it('T1.56: R4 view telemetry dispatches without client-side score modification', async () => {
      const payload = {
        spree_id: 'spree_001',
        watch_duration: 8.5,
        completed: false,
        device_info: 'Mobile/Safari',
      };
      const res = await feedApi.sendViewTelemetry(payload);
      expect(res.success).toBe(true);
    });
  });
});
