import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  feedApi,
  notificationApi,
  storeApi,
  walletApi,
} from '../../api/client';

function jsonResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    json: async () => body,
  } as Response;
}

describe('Frontend API contract normalization', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
    localStorage.setItem('spreego_token', 'test-access-token');
  });

  it('normalizes backend feed, creator and media fields for the reel UI', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse([
        {
          id: 'spree-1',
          creator_id: 'user-1',
          type: 'VIDEO_LONG',
          title: 'Backend title',
          description: 'Backend description',
          media_url: '/static/uploads/demo.mp4',
          thumbnail_url: null,
          creator: {
            id: 'user-1',
            username: 'creator_one',
            full_name: 'Creator One',
            avatar_url: null,
          },
          metrics: { views_count: 12, claps_count: 3 },
        },
      ]),
    );

    const [item] = await feedApi.getFeed();

    expect(item.type).toBe('LONG_VIDEO');
    expect(item.caption).toBe('Backend description');
    expect(item.creator.handle).toBe('@creator_one');
    expect(item.creator.display_name).toBe('Creator One');
    expect(item.media_url).toMatch(/\/static\/uploads\/demo\.mp4$/);
    expect(item.thumbnail_url).toBe(item.media_url);
    expect(item.views_count).toBe(12);
    expect(item.claps_count).toBe(3);
  });

  it('normalizes backend comments into the CommentDrawer shape', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse([
        {
          id: 'comment-1',
          spree_id: 'spree-1',
          user_id: 'user-1',
          username: 'creator_one',
          avatar_url: null,
          text: 'Nice shot',
          created_at: '2026-10-26T10:00:00Z',
        },
      ]),
    );

    const [comment] = await feedApi.getComments('spree-1');

    expect(comment.user.id).toBe('user-1');
    expect(comment.user.username).toBe('creator_one');
    expect(comment.user.handle).toBe('@creator_one');
    expect(comment.user.avatar_url).toBeTruthy();
    expect(comment.claps_count).toBe(0);
  });

  it('normalizes commerce, membership, payout and notification responses', async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse([
          {
            id: 'order-1',
            total_amount: 2499,
            status: 'PROCESSING',
            created_at: '2026-10-26T10:00:00Z',
            items: [
              {
                product_id: 'product-1',
                quantity: 1,
                unit_price: 2499,
                product: { title: 'Travel Backpack', images: ['/static/uploads/bag.jpg'] },
              },
            ],
          },
        ]),
      )
      .mockResolvedValueOnce(jsonResponse({ status: 'ACTIVE' }))
      .mockResolvedValueOnce(
        jsonResponse({
          id: 'payout-1',
          status: 'PENDING',
          amount: 1000,
          payout_method: { upi_id: 'creator@upi' },
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ message: 'All notifications marked as read.', updated_count: 2 }));

    const [order] = await storeApi.getOrders();
    const subscription = await storeApi.subscribeCommunityPass('plan-1');
    const payout = await walletApi.requestPayout(1000, 'creator@upi');
    const notifications = await notificationApi.markAllAsRead();

    expect(order.product_title).toBe('Travel Backpack');
    expect(order.total_amount_inr).toBe(2499);
    expect(subscription).toEqual({ success: true, is_active: true });
    expect(payout).toMatchObject({ success: true, transaction_id: 'payout-1' });
    expect(notifications).toEqual({ success: true });
  });
});
