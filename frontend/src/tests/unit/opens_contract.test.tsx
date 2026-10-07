import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import React from 'react';
import { opensApi, ApiError } from '../../api/client';
import { OpensOverview } from '../../components/opens/OpensOverview';
import { ChallengeDetails } from '../../components/opens/ChallengeDetails';
import { RankingLeaderboard } from '../../components/opens/RankingLeaderboard';
import { Open, OpenRankingItem } from '../../types';

describe('Opens Feature — Unified Backend & Frontend Contract', () => {
  const sampleOpen: Open = {
    id: 'open-test-uuid-001',
    creator_id: 'creator-uuid-001',
    type: 'CHALLENGE',
    title: 'Kinetic Movement Open',
    description: 'Showcase fluid parkour and kinetic movement.',
    cover_image_url: 'https://images.unsplash.com/photo-1552674605-db6ffd4facb5?w=800',
    rules: ['Must be in 9:16 vertical ratio', 'Original audio preferred', 'Minimum 15 seconds'],
    start_at: '2026-10-01T00:00:00Z',
    end_at: '2026-10-25T23:59:59Z',
    status: 'ACTIVE',
    reward_info: '₹75,000 Reward Pool',
    max_participants: 500,
    scoring_config: { claps: 2.0, views: 1.0, shares: 3.0, completion: 5.0 },
    participants_count: 128,
    submissions_count: 42,
    is_active: true,
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
  };

  const sampleRankings: OpenRankingItem[] = [
    {
      rank: 1,
      score: 1420.5,
      submission_id: 'sub-001',
      spree_id: 'spree-001',
      user_id: 'user-001',
      creator_id: 'user-001',
      creator: {
        id: 'user-001',
        username: 'parkour_pro',
        full_name: 'Aarav Movement',
        avatar_url: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150',
      },
      spree_title: 'Roof Jump Santorini',
      metrics: {
        views_count: 2400,
        completed_views_count: 1800,
        watch_completion_rate: 0.75,
        claps_count: 420,
        comments_count: 35,
        saves_count: 88,
        shares_count: 45,
      },
      created_at: '2026-10-02T10:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('1. API Client Contract Verification', () => {
    it('creates Open with required validation and proper POST body', async () => {
      // Validate title is required
      await expect(
        opensApi.createOpen({
          title: '',
          end_at: '2026-12-01T00:00:00Z',
        })
      ).rejects.toThrow('Title is required');

      // Validate end_at must be in future
      await expect(
        opensApi.createOpen({
          title: 'Past Open',
          start_at: '2026-10-05T00:00:00Z',
          end_at: '2026-10-01T00:00:00Z',
        })
      ).rejects.toThrow('end_at must be strictly after start_at');
    });

    it('getOpens calls backend with type, status, and pagination params without unsupported mode or category', async () => {
      const spy = vi.spyOn(window, 'fetch').mockResolvedValueOnce({
        ok: true,
        json: async () => [sampleOpen],
      } as Response);

      const res = await opensApi.getOpens({
        type: 'CHALLENGE',
        status: 'ACTIVE',
        page: 1,
        limit: 10,
      });

      expect(spy).toHaveBeenCalled();
      const calledUrl = spy.mock.calls[0][0] as string;
      expect(calledUrl).toContain('/api/v1/opens?');
      expect(calledUrl).toContain('type=CHALLENGE');
      expect(calledUrl).toContain('status=ACTIVE');
      expect(calledUrl).toContain('page=1');
      expect(calledUrl).toContain('limit=10');
      // Must not contain unsupported query params
      expect(calledUrl).not.toContain('mode=');
      expect(calledUrl).not.toContain('category=');
      expect(res).toHaveLength(1);
      expect(res[0].id).toBe(sampleOpen.id);
    });

    it('getRanking calls /api/v1/opens/{id}/ranking without timeframe query parameter', async () => {
      const spy = vi.spyOn(window, 'fetch').mockResolvedValueOnce({
        ok: true,
        json: async () => sampleRankings,
      } as Response);

      const items = await opensApi.getRanking('open-test-uuid-001');

      expect(spy).toHaveBeenCalled();
      const calledUrl = spy.mock.calls[0][0] as string;
      expect(calledUrl).toContain('/api/v1/opens/open-test-uuid-001/ranking');
      expect(calledUrl).not.toContain('timeframe=');
      expect(items).toHaveLength(1);
      expect(items[0].rank).toBe(1);
      expect(items[0].score).toBe(1420.5);
    });

    it('submitSpree issues POST /api/v1/opens/{id}/submissions with { spree_id } payload', async () => {
      const spy = vi.spyOn(window, 'fetch').mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'sub-123',
          open_id: 'open-test-uuid-001',
          user_id: 'user-001',
          spree_id: 'spree-456',
          score: 10.0,
          rank: 1,
          created_at: new Date().toISOString(),
        }),
      } as Response);

      const res = await opensApi.submitSpree('open-test-uuid-001', 'spree-456');

      expect(spy).toHaveBeenCalled();
      const [url, init] = spy.mock.calls[0];
      expect(url).toContain('/api/v1/opens/open-test-uuid-001/submissions');
      expect(init?.method).toBe('POST');
      expect(JSON.parse(init?.body as string)).toEqual({ spree_id: 'spree-456' });
      expect(res.spree_id).toBe('spree-456');
    });

    it('exposes real error messages and HTTP status codes on failure without silent mock masking', async () => {
      vi.spyOn(window, 'fetch').mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'You have already joined this Open.' }),
      } as Response);

      await expect(opensApi.joinChallenge('open-test-uuid-001')).rejects.toThrow(
        'You have already joined this Open.'
      );
    });
  });

  describe('2. UI Component Integration & State Handling', () => {
    it('OpensOverview renders list of opens and switches between CHALLENGE and COMPETITION tabs', async () => {
      vi.spyOn(opensApi, 'getOpens').mockImplementation(async (params) => {
        if (params.type === 'COMPETITION') {
          return [{ ...sampleOpen, id: 'comp-001', type: 'COMPETITION', title: 'Street Dance Cup' }];
        }
        return [sampleOpen];
      });

      render(<OpensOverview />);

      // Starts on Challenges tab
      await waitFor(() => {
        expect(screen.getAllByText('Kinetic Movement Open').length).toBeGreaterThan(0);
      });

      // Click on Competitions tab
      const compBtn = screen.getByRole('button', { name: /^competitions$/i });
      fireEvent.click(compBtn);

      await waitFor(() => {
        expect(screen.getAllByText('Street Dance Cup').length).toBeGreaterThan(0);
      });
    });

    it('ChallengeDetails renders actual backend Open fields, rules array, and metric counts', async () => {
      vi.spyOn(opensApi, 'getChallengeById').mockResolvedValueOnce(sampleOpen);
      vi.spyOn(opensApi, 'getOpenFeed').mockResolvedValueOnce([]);

      render(<ChallengeDetails challengeId={sampleOpen.id} onBack={() => {}} />);

      await waitFor(() => {
        expect(screen.getAllByText('Kinetic Movement Open').length).toBeGreaterThan(0);
      });

      // Rules rendered as individual list items
      expect(screen.getByText('Must be in 9:16 vertical ratio')).toBeInTheDocument();
      expect(screen.getByText('Original audio preferred')).toBeInTheDocument();

      // Counts rendered
      expect(screen.getByText('128')).toBeInTheDocument(); // participants
      expect(screen.getAllByText('₹75,000 Reward Pool').length).toBeGreaterThan(0);
    });

    it('ChallengeDetails join flow updates UI state and disables duplicate requests', async () => {
      vi.spyOn(opensApi, 'getChallengeById').mockResolvedValueOnce(sampleOpen);
      vi.spyOn(opensApi, 'getOpenFeed').mockResolvedValueOnce([]);
      const joinSpy = vi.spyOn(opensApi, 'joinChallenge').mockResolvedValueOnce({
        message: 'Successfully registered for challenge!',
        open_id: sampleOpen.id,
        user_id: 'test-user',
        joined_at: new Date().toISOString(),
      });

      render(<ChallengeDetails challengeId={sampleOpen.id} onBack={() => {}} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /join challenge now/i })).toBeInTheDocument();
      });

      const joinBtn = screen.getByRole('button', { name: /join challenge now/i });
      fireEvent.click(joinBtn);

      await waitFor(() => {
        expect(screen.getByText('Registered in Challenge')).toBeInTheDocument();
      });

      expect(joinSpy).toHaveBeenCalledTimes(1);
      // Button is now disabled to prevent duplicate join
      expect(screen.getByRole('button', { name: /registered in challenge/i })).toBeDisabled();
    });

    it('RankingLeaderboard renders live ranked items with dynamic scores without timeframe filters', async () => {
      vi.spyOn(opensApi, 'getRanking').mockResolvedValueOnce(sampleRankings);

      render(<RankingLeaderboard challengeId="open-test-uuid-001" />);

      await waitFor(() => {
        expect(screen.getByText('Aarav Movement')).toBeInTheDocument();
      });

      expect(screen.getByText('1,421 pts')).toBeInTheDocument();
      expect(screen.getByText(/Roof Jump Santorini/i)).toBeInTheDocument();

      // Timeframe buttons (overall/weekly/today) must NOT be present
      expect(screen.queryByRole('button', { name: /^weekly$/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /^today$/i })).not.toBeInTheDocument();
    });

    it('ChallengeDetails displays 404 error cleanly when Open not found', async () => {
      vi.spyOn(opensApi, 'getChallengeById').mockRejectedValueOnce(
        new ApiError('Open not found (404)', 404)
      );

      render(<ChallengeDetails challengeId="non-existent-uuid" onBack={() => {}} />);

      await waitFor(() => {
        expect(screen.getByText('Unable to Load Open')).toBeInTheDocument();
        expect(screen.getByText('Open not found (404)')).toBeInTheDocument();
      });
    });
  });
});
