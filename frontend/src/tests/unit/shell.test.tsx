import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import App from '../../App';
import { feedApi, opensApi, storeApi, walletApi } from '../../api/client';

describe('Milestone M1 — SPREEGO Shell & Taste-Design Foundation', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('renders brand logo and navigation shell with 5 tabs', () => {
    // Set consent so we can observe main shell directly
    localStorage.setItem('spreego_consent_accepted', JSON.stringify({ accepted: true, version: 'v1.0' }));

    render(<App />);

    // TopNav brand monogram & title
    expect(screen.getByText('SPREEGO')).toBeInTheDocument();

    // 5 BottomNav items
    expect(screen.getByRole('button', { name: /^home$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^spree$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create spree/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^opens$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^profile$/i })).toBeInTheDocument();
  });

  it('switches tabs when clicking on BottomNav items', async () => {
    localStorage.setItem('spreego_consent_accepted', JSON.stringify({ accepted: true, version: 'v1.0' }));
    render(<App />);

    // Starts on Home (For You tab in TopNav)
    expect(screen.getByText('For You')).toBeInTheDocument();

    // Click on Spree tab
    const spreeTab = screen.getByRole('button', { name: /^spree$/i });
    fireEvent.click(spreeTab);
    expect(screen.getByText('Long Videos')).toBeInTheDocument();

    // Click on Opens tab
    const opensTab = screen.getByRole('button', { name: /opens/i });
    fireEvent.click(opensTab);
    expect(screen.getByRole('heading', { name: /opens/i })).toBeInTheDocument();

    // Click on Profile tab
    const profileTab = screen.getByRole('button', { name: /profile/i });
    fireEvent.click(profileTab);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /store/i })).toBeInTheDocument();
    });
  });

  it('opens creation modal bottom sheet when clicking the center Create button', async () => {
    localStorage.setItem('spreego_consent_accepted', JSON.stringify({ accepted: true, version: 'v1.0' }));
    render(<App />);

    const createButton = screen.getByRole('button', { name: /create spree/i });
    fireEvent.click(createButton);

    expect(screen.getByText('Create New Spree')).toBeInTheDocument();
    expect(screen.getByText('Upload Video')).toBeInTheDocument();

    // Close button dismisses modal
    const closeBtn = screen.getByRole('button', { name: /close creation sheet/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText('Create New Spree')).not.toBeInTheDocument();
    });
  });

  it('displays R3 Consent Guard Modal on initial visit and persists acceptance', async () => {
    // Empty localStorage -> Consent modal must display
    render(<App />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Welcome to SPREEGO')).toBeInTheDocument();
    expect(screen.getByText('Community Guidelines')).toBeInTheDocument();
    expect(screen.getByText('Privacy Policy')).toBeInTheDocument();
    expect(screen.getByText('Interaction Telemetry')).toBeInTheDocument();

    // Accept CTA
    const acceptBtn = screen.getByRole('button', { name: /accept & enter spreego/i });
    fireEvent.click(acceptBtn);

    // Modal unmounts
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    // Check localStorage persistence
    const saved = localStorage.getItem('spreego_consent_accepted');
    expect(saved).toBeTruthy();
    const parsed = JSON.parse(saved!);
    expect(parsed.accepted).toBe(true);
    expect(parsed.version).toBe('v1.0');
  });

  it('warns user when declining consent in ConsentGuardModal', async () => {
    render(<App />);

    const declineBtn = screen.getByRole('button', { name: /decline & limit features/i });
    fireEvent.click(declineBtn);

    expect(screen.getByText(/consent is required to unlock full interactive feeds/i)).toBeInTheDocument();
    expect(localStorage.getItem('spreego_consent_accepted')).toBeNull();
  });

  it('toggles sound mute state from TopNav', () => {
    localStorage.setItem('spreego_consent_accepted', JSON.stringify({ accepted: true, version: 'v1.0' }));
    render(<App />);

    const soundBtn = screen.getByRole('button', { name: /mute audio/i });
    fireEvent.click(soundBtn);

    // Now button switches to Unmute Audio
    expect(screen.getByRole('button', { name: /unmute audio/i })).toBeInTheDocument();
  });

  it('API client returns authentic fallback data offline', async () => {
    const feed = await feedApi.getFeed();
    expect(feed.length).toBeGreaterThan(0);
    expect(feed[0].title).toBe('Sunset vibes in Santorini');
    expect(feed[0].creator.handle).toBe('@travelwithme');

    const opens = await opensApi.getChallenges();
    expect(opens.length).toBeGreaterThan(0);
    expect(opens[0].title).toBe('Move Better Challenge');

    const products = await storeApi.getProducts();
    expect(products.length).toBeGreaterThan(0);
    expect(products[0].title).toBe('Travel Backpack');

    const wallet = await walletApi.getWalletSummary();
    expect(wallet.available_balance_inr).toBe(42500);
  });
});
