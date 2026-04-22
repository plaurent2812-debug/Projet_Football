import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { axe } from 'jest-axe';
import PremiumV2 from './PremiumV2';

vi.mock('@/hooks/v2/useTrackRecordLive', () => ({
  useTrackRecordLive: () => ({
    isLoading: false,
    isError: false,
    data: {
      clv30d: 2.1,
      roi90d: 12.4,
      brier30d: 0.208,
      safeRate90d: 71.8,
      roiCurve90d: [
        { date: '2026-01-22', roi: 0 },
        { date: '2026-04-22', roi: 12.4 },
      ],
      lastUpdatedAt: new Date().toISOString(),
    },
  }),
}));

vi.mock('@/components/v2/premium/ROIChart', () => ({
  __esModule: true,
  default: () => <div data-testid="roi-chart-stub" />,
  ROIChart: () => <div data-testid="roi-chart-stub" />,
}));

function wrap(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('PremiumV2 page', () => {
  it('renders the page data-testid', () => {
    render(wrap(<PremiumV2 />));
    expect(screen.getByTestId('premium-v2-page')).toBeInTheDocument();
  });

  it('composes hero, live track record, pricing, guarantee and FAQ in order', () => {
    render(wrap(<PremiumV2 />));
    expect(screen.getByTestId('premium-hero')).toBeInTheDocument();
    expect(screen.getByTestId('live-track-record')).toBeInTheDocument();
    expect(screen.getByTestId('pricing-cards')).toBeInTheDocument();
    expect(screen.getByTestId('transparency-guarantee')).toBeInTheDocument();
    expect(screen.getByTestId('faq-short')).toBeInTheDocument();
  });

  it('sets #track-record anchor as smooth-scroll target of the hero CTA', () => {
    render(wrap(<PremiumV2 />));
    const tracker = screen.getByTestId('live-track-record');
    expect(tracker).toHaveAttribute('id', 'track-record');
  });

  it('renders the positioning h1 and the guarantee + FAQ mentions', () => {
    render(wrap(<PremiumV2 />));
    expect(
      screen.getByRole('heading', { level: 1, name: /parier avec une vraie probabilité/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/mois offert/i)).toBeInTheDocument();
    expect(screen.getAllByRole('article').length).toBeGreaterThanOrEqual(3);
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<PremiumV2 />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
