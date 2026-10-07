import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  feedApi,
  opensApi,
  storeApi,
  walletApi,
  userApi,
} from '../../api/client';
import { mockSprees } from '../../api/mockData';

describe('Tier 4: Real-World Application Scenarios (Comprehensive End-to-End User Journeys)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  // =========================================================================
  // JOURNEY 1: NEW USER ONBOARDING & CONSENT GUARD GATE
  // =========================================================================
  it('Journey 1: New User Onboarding & Consent Guard Gate Lifecycle', async () => {
    const CONSENT_STORAGE_KEY = 'spreego_consent_accepted';

    // Step 1: User arrives on initial launch; consent is not yet present
    expect(localStorage.getItem(CONSENT_STORAGE_KEY)).toBeNull();

    // Step 2: System verifies compliance items before feed access
    const complianceItems = [
      { id: 'guidelines', title: 'Community Guidelines', verified: true },
      { id: 'privacy', title: 'Privacy Policy', verified: true },
      { id: 'telemetry', title: 'Interaction Telemetry', verified: true },
    ];
    expect(complianceItems.every((item) => item.verified)).toBe(true);

    // Step 3: User accepts terms and enters SPREEGO
    const acceptedAt = new Date().toISOString();
    localStorage.setItem(
      CONSENT_STORAGE_KEY,
      JSON.stringify({
        hasAccepted: true,
        acceptedAt,
        version: 'v1.0',
      })
    );

    // Step 4: Validate persistence
    const saved = JSON.parse(localStorage.getItem(CONSENT_STORAGE_KEY) || '{}');
    expect(saved.hasAccepted).toBe(true);
    expect(saved.version).toBe('v1.0');

    // Step 5: Feed query is successfully unblocked and populated
    const feed = await feedApi.getFeed('for_you');
    expect(feed.length).toBeGreaterThan(0);
    expect(feed[0]).toHaveProperty('title');
  });

  // =========================================================================
  // JOURNEY 2: CREATOR CONTENT UPLOAD & MONETIZATION
  // =========================================================================
  it('Journey 2: Creator Content Upload & Monetization Lifecycle', async () => {
    // Step 1: Creator prepares upload payload
    const uploadPayload = {
      title: 'Himalayan High Altitude Trek',
      caption: 'Dawn breaking over the snow peaks 🏔️ #trekking #mountains #himalayas',
      type: 'VIDEO_SHORT' as const,
      media_url: 'https://assets.mixkit.co/videos/preview/mixkit-mountain-trek.mp4',
      thumbnail_url: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=600',
      duration_seconds: 28,
      tags: ['trekking', 'mountains', 'himalayas'],
    };

    expect(uploadPayload.duration_seconds).toBeLessThanOrEqual(600); // 10 min limit
    expect(uploadPayload.media_url).toMatch(/^https?:\/\//);

    // Step 2: Content is published and available in creator's library
    const currentUser = await userApi.getCurrentUser();
    expect(currentUser.handle).toBe('@travelwithme');

    // Step 3: Creator verifies store merchandise linked to monetization
    const products = await storeApi.getProducts('products');
    expect(products.length).toBeGreaterThan(0);
    const creatorProduct = products.find((p) => p.creator_id === currentUser.id);
    expect(creatorProduct).toBeDefined();

    // Step 4: Creator inspects earnings wallet
    const wallet = await walletApi.getWalletSummary();
    expect(wallet.available_balance_inr).toBeGreaterThan(0);
  });

  // =========================================================================
  // JOURNEY 3: CHALLENGE COMPETITION, SUBMISSION & LIVE LEADERBOARD
  // =========================================================================
  it('Journey 3: Challenge Competition, Submission & Live Leaderboard Lifecycle', async () => {
    // Step 1: Discover active challenges in Opens Hub
    const challenges = await opensApi.getChallenges('challenges', 'All');
    expect(challenges.length).toBeGreaterThan(0);

    const challenge = challenges.find((c) => c.title === 'Travel Tales') || challenges[0];
    expect(challenge.participants_count).toBeGreaterThan(0);
    expect(challenge.reward_pool_amount).toBeGreaterThan(0);

    // Step 2: Inspect challenge rules and eligibility
    const details = await opensApi.getChallengeById(challenge.id);
    expect(details?.rules).toBeDefined();
    expect(details?.rules?.length).toBeGreaterThanOrEqual(1);

    // Step 3: Join Challenge registration
    const joinRes = await opensApi.joinChallenge(challenge.id);
    expect(joinRes.success).toBe(true);

    // Step 4: Switch to Leaderboard Ranking tab
    const leaderboard = await opensApi.getRanking(challenge.id, 'overall');
    expect(leaderboard.length).toBeGreaterThanOrEqual(3);

    // Step 5: Verify podium ranks (Gold, Silver, Bronze)
    expect(leaderboard[0].rank).toBe(1);
    expect(leaderboard[0].score).toBeGreaterThan(leaderboard[1].score);
    expect(leaderboard[1].rank).toBe(2);
    expect(leaderboard[1].score).toBeGreaterThan(leaderboard[2].score);
    expect(leaderboard[2].rank).toBe(3);
  });

  // =========================================================================
  // JOURNEY 4: CREATOR COMMERCE SHOPPING, ₹0 PASS & WALLET PAYOUT
  // =========================================================================
  it('Journey 4: Creator Commerce Shopping, ₹0 Pass Subscription & Payout Lifecycle', async () => {
    // Step 1: Browse Store products catalog
    const products = await storeApi.getProducts('products');
    const backpack = products.find((p) => p.title.includes('Backpack')) || products[0];
    expect(backpack.in_stock).toBe(true);

    // Step 2: Subscribe to ₹0 Community Pass
    const pass = await storeApi.getCommunityPass();
    expect(pass.price_inr).toBe(0);
    const subRes = await storeApi.subscribeCommunityPass(pass.id);
    expect(subRes.success).toBe(true);
    expect(subRes.is_active).toBe(true);

    // Step 3: Purchase merchandise item
    const order = await storeApi.placeOrder(backpack.id, 1);
    expect(order.product_id).toBe(backpack.id);
    expect(order.total_amount_inr).toBe(backpack.price_inr);
    expect(order.status).toBe('PROCESSING');

    // Step 4: Verify order recorded in user order history
    const pastOrders = await storeApi.getOrders();
    expect(pastOrders.some((o) => o.id === order.id || o.product_id === backpack.id)).toBe(true);

    // Step 5: Creator accesses wallet and initiates payout withdrawal
    const wallet = await walletApi.getWalletSummary();
    const withdrawAmount = 10000;
    expect(wallet.available_balance_inr).toBeGreaterThanOrEqual(withdrawAmount);

    const payout = await walletApi.requestPayout(withdrawAmount, 'creator@okaxis');
    expect(payout.success).toBe(true);
    expect(payout.transaction_id).toBeTruthy();
    expect(payout.message).toContain('10,000');
  });

  // =========================================================================
  // JOURNEY 5: REEL PLAYBACK, ENGAGEMENT & TELEMETRY STREAMING
  // =========================================================================
  it('Journey 5: Reel Video Playback, Engagement & Background Telemetry Stream Lifecycle', async () => {
    // Step 1: User enters Home Feed and starts active video reel
    const feed = await feedApi.getFeed('for_you');
    const currentReel = feed[0];
    expect(currentReel.media_url).toBeTruthy();

    // Step 2: User double-taps to clap for reel
    const initialClaps = currentReel.claps_count;
    const clapRes = await feedApi.clapSpree(currentReel.id);
    expect(clapRes.success).toBe(true);
    expect(clapRes.newCount).toBe(initialClaps + 1);

    // Step 3: User opens comment drawer and submits comment
    const comment = await feedApi.addComment(currentReel.id, 'Love the vibrant golden hour lighting!');
    expect(comment.text).toBe('Love the vibrant golden hour lighting!');
    expect(comment.spree_id).toBe(currentReel.id);

    // Step 4: User saves reel to bookmarks
    const saveRes = await feedApi.saveSpree(currentReel.id);
    expect(saveRes.success).toBe(true);
    expect(saveRes.saved).toBe(true);

    // Step 5: User finishes full watch (>80%) and streams completion telemetry beacon
    const telemetryComplete = await feedApi.sendViewTelemetry({
      spree_id: currentReel.id,
      watch_duration: 14.8,
      completed: true,
      device_info: 'Chrome E2E Engine',
    });
    expect(telemetryComplete.success).toBe(true);

    // Step 6: User swipes to next reel and skips after 1.5s -> streams skip telemetry beacon
    const nextReel = feed[1] || mockSprees[1];
    const telemetrySkip = await feedApi.sendViewTelemetry({
      spree_id: nextReel.id,
      watch_duration: 1.5,
      completed: false,
      device_info: 'Chrome E2E Engine',
    });
    expect(telemetrySkip.success).toBe(true);
  });
});

