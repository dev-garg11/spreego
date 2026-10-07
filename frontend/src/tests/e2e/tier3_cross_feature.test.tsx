import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  feedApi,
  opensApi,
  storeApi,
  walletApi,
  userApi,
} from '../../api/client';
import { mockSprees, mockOpens, mockProducts } from '../../api/mockData';

describe('Tier 3: Cross-Feature Pairwise Suite (Interactions & Data Flow)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('T3.01: Feed -> Comment -> User Profile (Inspect commenter from reel and fetch profile)', async () => {
    const feed = await feedApi.getFeed('for_you');
    const firstReel = feed[0];
    const comments = await feedApi.getComments(firstReel.id);
    expect(comments.length).toBeGreaterThan(0);

    const commenter = comments[0].user;
    expect(commenter).toHaveProperty('id');
    expect(commenter).toHaveProperty('handle');

    const profile = await userApi.getUserById(commenter.id);
    expect(profile).not.toBeNull();
    expect(profile.handle).toBeTruthy();
  });

  it('T3.02: Feed Sponsored Badge -> Brand Sponsorship Navigation & Details', async () => {
    const feed = await feedApi.getFeed('for_you');
    const sponsoredReel = feed.find((r) => r.sponsored !== undefined);
    expect(sponsoredReel).toBeDefined();
    expect(sponsoredReel?.sponsored?.brand_name).toBe('SkyWings');

    const brandCampaign = await opensApi.getBrandCampaign();
    expect(brandCampaign).toBeDefined();
    expect(brandCampaign.headline).toBeTruthy();
    expect(brandCampaign.reward_pool).toContain('₹');
  });

  it('T3.03: Spree Explore Search -> Media Card Drill-down -> Full Reel Playback', async () => {
    const searchResults = await feedApi.getExploreItems('all', 'Santorini');
    expect(searchResults.length).toBeGreaterThan(0);

    const selectedItem = searchResults[0];
    const fullSpree = await feedApi.getSpreeById(selectedItem.id);
    expect(fullSpree).not.toBeNull();
    expect(fullSpree?.id).toBe(selectedItem.id);
    expect(fullSpree?.media_url).toBeTruthy();
    expect(fullSpree?.duration_seconds).toBeGreaterThan(0);
  });

  it('T3.04: Opens Overview -> Challenge Details -> Join Registration -> Live Leaderboard', async () => {
    const challenges = await opensApi.getChallenges('challenges', 'All');
    const targetChallenge = challenges.find((c) => c.title === 'Travel Tales') || challenges[0];

    const details = await opensApi.getChallengeById(targetChallenge.id);
    expect(details).not.toBeNull();
    expect(details?.title).toBe(targetChallenge.title);

    const joinResult = await opensApi.joinChallenge(targetChallenge.id);
    expect(joinResult.success).toBe(true);

    const leaderboard = await opensApi.getRanking(targetChallenge.id, 'overall');
    expect(Array.isArray(leaderboard)).toBe(true);
    expect(leaderboard.length).toBeGreaterThan(0);
    expect(leaderboard[0].rank).toBe(1);
    expect(leaderboard[0].score).toBeGreaterThan(0);
  });

  it('T3.05: Creator Store Product -> Order Placement -> Order History Tracking', async () => {
    const products = await storeApi.getProducts('products');
    const backpack = products.find((p) => p.title.includes('Backpack')) || products[0];

    const order = await storeApi.placeOrder(backpack.id, 2);
    expect(order.product_id).toBe(backpack.id);
    expect(order.quantity).toBe(2);
    expect(order.total_amount_inr).toBe(backpack.price_inr * 2);

    const ordersList = await storeApi.getOrders();
    expect(ordersList.length).toBeGreaterThan(0);
  });

  it('T3.06: Free Community Pass Subscription -> Member Status Activation', async () => {
    const pass = await storeApi.getCommunityPass();
    expect(pass.price_inr).toBe(0);

    const subscribeRes = await storeApi.subscribeCommunityPass(pass.id);
    expect(subscribeRes.success).toBe(true);
    expect(subscribeRes.is_active).toBe(true);
  });

  it('T3.07: Video Reel Watch Telemetry -> Creator Analytics KPI Verification', async () => {
    const telemetryRes = await feedApi.sendViewTelemetry({
      spree_id: mockSprees[0].id,
      watch_duration: 15.0,
      completed: true,
      device_info: 'Chrome Test Runner',
    });
    expect(telemetryRes.success).toBe(true);

    const kpis = await walletApi.getKPIMetrics();
    expect(kpis.some((k) => k.label === 'Views')).toBe(true);

    const topContent = await walletApi.getTopContent();
    expect(topContent.length).toBeGreaterThan(0);
    expect(topContent[0].rank).toBe(1);
  });

  it('T3.08: Store Revenue Earnings -> Creator Wallet Balance -> UPI Payout Withdrawal', async () => {
    const product = mockProducts[0];
    const order = await storeApi.placeOrder(product.id, 1);
    expect(order.total_amount_inr).toBe(product.price_inr);

    const wallet = await walletApi.getWalletSummary();
    expect(wallet.available_balance_inr).toBeGreaterThan(0);

    const payoutRes = await walletApi.requestPayout(5000, 'creator@okaxis');
    expect(payoutRes.success).toBe(true);
    expect(payoutRes.transaction_id).toBeTruthy();
  });

  it('T3.09: Creator Profile Follow Inspection -> Following Feed Sub-Tab Content', async () => {
    const currentUser = await userApi.getCurrentUser();
    expect(currentUser.follower_count).toBeGreaterThan(0);

    const followingFeed = await feedApi.getFeed('following');
    expect(Array.isArray(followingFeed)).toBe(true);
    expect(followingFeed.length).toBeGreaterThan(0);
  });

  it('T3.10: R3 Consent Acceptance -> Unlocks Feed Queries and User Session State', async () => {
    const CONSENT_KEY = 'spreego_consent_accepted';
    expect(localStorage.getItem(CONSENT_KEY)).toBeNull();

    localStorage.setItem(
      CONSENT_KEY,
      JSON.stringify({
        hasAccepted: true,
        acceptedAt: new Date().toISOString(),
        version: 'v1.0',
      })
    );

    const storedConsent = JSON.parse(localStorage.getItem(CONSENT_KEY) || '{}');
    expect(storedConsent.hasAccepted).toBe(true);

    const initialFeed = await feedApi.getFeed('for_you');
    expect(initialFeed.length).toBeGreaterThan(0);
  });

  it('T3.11: Explore Category Filter Transition (Photos -> Videos -> Long Videos -> All)', async () => {
    const photos = await feedApi.getExploreItems('photos', '');
    expect(photos.every((p) => p.type === 'PHOTO')).toBe(true);

    const videos = await feedApi.getExploreItems('videos', '');
    expect(videos.every((v) => v.type === 'VIDEO_SHORT')).toBe(true);

    const longVideos = await feedApi.getExploreItems('long_videos', '');
    expect(longVideos.every((lv) => lv.type === 'LONG_VIDEO')).toBe(true);

    const all = await feedApi.getExploreItems('all', '');
    expect(all.length).toBeGreaterThanOrEqual(photos.length + videos.length);
  });

  it('T3.12: Opens Mode Transition (Challenges vs Competitions) & Category Filtering', async () => {
    const challenges = await opensApi.getChallenges('challenges', 'All');
    expect(challenges.every((c) => c.mode === 'challenges')).toBe(true);

    const competitions = await opensApi.getChallenges('competitions', 'All');
    expect(competitions.every((c) => c.mode === 'competitions')).toBe(true);

    const fitness = await opensApi.getChallenges('all', 'Fitness');
    expect(fitness.every((c) => c.category.toLowerCase() === 'fitness')).toBe(true);
  });
});

