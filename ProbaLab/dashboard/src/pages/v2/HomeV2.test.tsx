import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import HomeV2 from './HomeV2';
import * as v2User from '@/hooks/v2/useV2User';
import type { V2User } from '@/hooks/v2/useV2User';

function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockUser(u: V2User) {
  vi.spyOn(v2User, 'useV2User').mockReturnValue(u);
}

function setViewportWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    value: width,
    configurable: true,
    writable: true,
  });
  window.dispatchEvent(new Event('resize'));
}

describe('HomeV2', () => {
  beforeEach(() => {
    setViewportWidth(1280);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows landing mode for visitors (hero + blurred preview, no stats)', async () => {
    mockUser({ role: 'visitor', isVisitor: true });
    renderWithProviders(<HomeV2 />);
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
      /vraie probabilité/i,
    );
    expect(screen.queryByText(/ROI 30J/i)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByTestId('preview-blur-row').length).toBeGreaterThan(0);
    });
  });

  it('shows dashboard mode for connected free users with PremiumCTA', async () => {
    mockUser({ role: 'free', isVisitor: false });
    renderWithProviders(<HomeV2 />);
    await waitFor(() => expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument());
    expect(await screen.findByText('PSG gagne vs Lens')).toBeInTheDocument();
    expect(screen.getByTestId('premium-cta')).toBeInTheDocument();
  });

  it('shows dashboard for trial users with PremiumCTA', async () => {
    mockUser({ role: 'trial', isVisitor: false, trialDaysLeft: 18 });
    renderWithProviders(<HomeV2 />);
    await waitFor(() => expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument());
    expect(screen.getByTestId('premium-cta')).toBeInTheDocument();
  });

  it('hides PremiumCTA for premium users', async () => {
    mockUser({ role: 'premium', isVisitor: false });
    renderWithProviders(<HomeV2 />);
    await waitFor(() => expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument());
    expect(screen.queryByTestId('premium-cta')).not.toBeInTheDocument();
  });

  it('renders inline layout at 375px', async () => {
    setViewportWidth(375);
    mockUser({ role: 'free', isVisitor: false });
    renderWithProviders(<HomeV2 />);
    await waitFor(() => expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument());
    expect(screen.getByTestId('home-right-col')).toHaveAttribute('data-layout', 'inline');
  });

  it('renders sticky layout at 1280px', async () => {
    setViewportWidth(1280);
    mockUser({ role: 'premium', isVisitor: false });
    renderWithProviders(<HomeV2 />);
    await waitFor(() => expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument());
    expect(screen.getByTestId('home-right-col')).toHaveAttribute('data-layout', 'sticky');
  });
});
