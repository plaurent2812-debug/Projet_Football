import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { axe } from 'jest-axe';
import { LiveTrackRecord } from './LiveTrackRecord';
import type { TrackRecordLive } from '@/hooks/v2/useTrackRecordLive';

vi.mock('@/hooks/v2/useTrackRecordLive', () => ({
  useTrackRecordLive: vi.fn(),
}));
import { useTrackRecordLive } from '@/hooks/v2/useTrackRecordLive';

// The chart is lazy — stub it to keep the test lightweight and sync.
vi.mock('./ROIChart', () => ({
  __esModule: true,
  default: ({ data }: { data: Array<{ date: string; roi: number }> }) => (
    <div data-testid="roi-chart-stub">{data.length} points</div>
  ),
  ROIChart: ({ data }: { data: Array<{ date: string; roi: number }> }) => (
    <div data-testid="roi-chart-stub">{data.length} points</div>
  ),
}));

const sample: TrackRecordLive = {
  clv30d: 2.1,
  roi90d: 12.4,
  brier30d: 0.208,
  safeRate90d: 71.8,
  roiCurve90d: Array.from({ length: 90 }, (_, i) => ({
    date: `2026-01-${String((i % 28) + 1).padStart(2, '0')}`,
    roi: i * 0.1,
  })),
  lastUpdatedAt: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
};

function wrap(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const mockedHook = useTrackRecordLive as unknown as ReturnType<typeof vi.fn>;

describe('LiveTrackRecord', () => {
  beforeEach(() => {
    mockedHook.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows a skeleton while loading', () => {
    mockedHook.mockReturnValue({ isLoading: true, isError: false, data: undefined });
    render(wrap(<LiveTrackRecord />));
    expect(screen.getByTestId('live-track-record-skeleton')).toBeInTheDocument();
  });

  it('shows an error message when the hook fails', () => {
    mockedHook.mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    });
    render(wrap(<LiveTrackRecord />));
    expect(
      screen.getByText(/impossible de charger le track record/i),
    ).toBeInTheDocument();
  });

  it('renders 4 stat tiles, the chart and the toggle', async () => {
    mockedHook.mockReturnValue({ isLoading: false, isError: false, data: sample });
    render(wrap(<LiveTrackRecord />));

    expect(screen.getByText(/CLV 30j/i)).toBeInTheDocument();
    expect(screen.getByText(/ROI 90j/i)).toBeInTheDocument();
    expect(screen.getByText(/Brier 30j/i)).toBeInTheDocument();
    expect(screen.getByText(/Safe 90j/i)).toBeInTheDocument();

    // 3 period toggle buttons.
    expect(screen.getByRole('button', { name: '30j' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '90j' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '1 an' })).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByTestId('roi-chart-stub')).toBeInTheDocument(),
    );
  });

  it('switches the active period when the toggle is clicked', async () => {
    mockedHook.mockReturnValue({ isLoading: false, isError: false, data: sample });
    const user = userEvent.setup();
    render(wrap(<LiveTrackRecord />));

    const ninety = screen.getByRole('button', { name: '90j' });
    const thirty = screen.getByRole('button', { name: '30j' });

    // 90j is the default.
    expect(ninety).toHaveAttribute('aria-pressed', 'true');
    expect(thirty).toHaveAttribute('aria-pressed', 'false');

    await user.click(thirty);
    expect(thirty).toHaveAttribute('aria-pressed', 'true');
    expect(ninety).toHaveAttribute('aria-pressed', 'false');
  });

  it('renders the LIVE label, the pulsing dot and the last-updated mention', () => {
    mockedHook.mockReturnValue({ isLoading: false, isError: false, data: sample });
    render(wrap(<LiveTrackRecord />));
    expect(screen.getByText(/track record live/i)).toBeInTheDocument();
    // 2 matches expected: eyebrow "TRACK RECORD LIVE" + standalone "LIVE" near the dot.
    expect(screen.getAllByText(/LIVE/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/dernière maj/i)).toBeInTheDocument();
    expect(screen.getByTestId('live-dot')).toBeInTheDocument();
  });

  it('renders the cherry-picking transparency note with the repo link', () => {
    mockedHook.mockReturnValue({ isLoading: false, isError: false, data: sample });
    render(wrap(<LiveTrackRecord />));
    const link = screen.getByRole('link', { name: /github\.com\/probalab/i });
    expect(link).toHaveAttribute('href', expect.stringContaining('github.com/probalab'));
    expect(screen.getByText(/sans cherry-picking/i)).toBeInTheDocument();
  });

  it('has no axe violations on loaded state', async () => {
    mockedHook.mockReturnValue({ isLoading: false, isError: false, data: sample });
    const { container } = render(wrap(<LiveTrackRecord />));
    await waitFor(() => screen.getByTestId('roi-chart-stub'));
    expect(await axe(container)).toHaveNoViolations();
  });
});
