import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ROIByMarketChart } from './ROIByMarketChart';
import type { ROIByMarketItem } from '@/hooks/v2/useROIByMarket';

// Stub the lazy Recharts chunk.
vi.mock('./ROIByMarketChartImpl', () => ({
  __esModule: true,
  default: ({ data }: { data: ROIByMarketItem[] }) => (
    <div data-testid="roi-by-market-stub">{data.length} bars</div>
  ),
  ROIByMarketChartImpl: ({ data }: { data: ROIByMarketItem[] }) => (
    <div data-testid="roi-by-market-stub">{data.length} bars</div>
  ),
}));

const sample: ROIByMarketItem[] = [
  { market: '1X2', roi_pct: 14.2, n: 18, wins: 11, losses: 6, voids: 1 },
  { market: 'O/U', roi_pct: 8.5, n: 12, wins: 7, losses: 5, voids: 0 },
  { market: 'BTTS', roi_pct: 4.1, n: 8, wins: 4, losses: 4, voids: 0 },
  { market: 'DC', roi_pct: -1.8, n: 6, wins: 3, losses: 3, voids: 0 },
  { market: 'Score', roi_pct: -12.3, n: 4, wins: 1, losses: 3, voids: 0 },
];

describe('ROIByMarketChart', () => {
  it('renders one row per market', () => {
    render(<ROIByMarketChart data={sample} />);
    for (const label of ['1X2', 'O/U', 'BTTS', 'DC', 'Score']) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it('displays signed percentages for each row', () => {
    render(<ROIByMarketChart data={sample} />);
    expect(screen.getByText(/\+14\.2\s*%/)).toBeInTheDocument();
    expect(screen.getByText(/\+8\.5\s*%/)).toBeInTheDocument();
    expect(screen.getByText(/-1\.8\s*%/)).toBeInTheDocument();
    expect(screen.getByText(/-12\.3\s*%/)).toBeInTheDocument();
  });

  it('uses tone=positive for positive ROIs and negative for losing markets', () => {
    render(<ROIByMarketChart data={sample} />);
    expect(screen.getByTestId('roi-row-1X2')).toHaveAttribute(
      'data-tone',
      'positive',
    );
    expect(screen.getByTestId('roi-row-DC')).toHaveAttribute(
      'data-tone',
      'negative',
    );
    expect(screen.getByTestId('roi-row-Score')).toHaveAttribute(
      'data-tone',
      'negative',
    );
  });

  it('exposes the sample count (n) in each row', () => {
    render(<ROIByMarketChart data={sample} />);
    // Scoped to the 1X2 row so ambiguous digits (e.g. "12") in other rows
    // do not collide with this assertion.
    expect(
      screen.getByTestId('roi-row-1X2').textContent,
    ).toMatch(/18\s*paris/);
    expect(
      screen.getByTestId('roi-row-O/U').textContent,
    ).toMatch(/12\s*paris/);
  });

  it('shows an empty state when there is no data', () => {
    render(<ROIByMarketChart data={[]} />);
    expect(screen.getByText(/aucune donn.*disponible/i)).toBeInTheDocument();
  });

  it('loads the Recharts chunk inside a Suspense boundary', async () => {
    render(<ROIByMarketChart data={sample} />);
    await waitFor(() =>
      expect(screen.getByTestId('roi-by-market-stub')).toBeInTheDocument(),
    );
  });

  it('forwards the data-testid prop', () => {
    render(<ROIByMarketChart data={sample} data-testid="my-roi" />);
    expect(screen.getByTestId('my-roi')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<ROIByMarketChart data={sample} />);
    await waitFor(() =>
      expect(screen.getByTestId('roi-by-market-stub')).toBeInTheDocument(),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
