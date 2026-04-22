import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { BankrollTab } from './BankrollTab';
import type { BankrollSummary } from '@/hooks/v2/useBankroll';
import type { BetRow } from '@/hooks/v2/useBankrollBets';
import type { ROIByMarketItem } from '@/hooks/v2/useROIByMarket';

// Stub the heavy modal layer from the header so we can focus on the
// page composition.
vi.mock(
  '@/components/v2/account/bankroll/BankrollHeader',
  () => ({
    BankrollHeader: () => <div data-testid="mock-bankroll-header">header</div>,
  }),
);

// Stub the lazy chart chunks — keeps tests sync.
vi.mock(
  '@/components/v2/account/bankroll/BankrollChartImpl',
  () => ({
    __esModule: true,
    default: ({ curve }: { curve: unknown[] }) => (
      <div data-testid="bankroll-chart-stub">{curve.length} points</div>
    ),
  }),
);
vi.mock(
  '@/components/v2/account/bankroll/ROIByMarketChartImpl',
  () => ({
    __esModule: true,
    default: ({ data }: { data: unknown[] }) => (
      <div data-testid="roi-by-market-stub">{data.length} bars</div>
    ),
  }),
);

const bankroll: BankrollSummary = {
  current_balance: 1284,
  initial_balance: 1000,
  roi_30d: 12.4,
  roi_90d: 9.8,
  win_rate: 58.7,
  drawdown_max_pct: -4.2,
  kelly_fraction_active: 0.25,
  total_bets: 48,
  wins: 26,
  losses: 19,
  voids: 3,
};

const bets: BetRow[] = [
  {
    id: 'bet-001',
    fixture_id: 'fx-1',
    match_title: 'PSG - Lens',
    market: '1X2',
    selection: 'Home',
    odds: 1.85,
    stake: 25,
    result: 'WIN',
    placed_at: '2026-04-19T10:00:00Z',
    resolved_at: '2026-04-19T21:00:00Z',
  },
  {
    id: 'bet-002',
    fixture_id: 'fx-2',
    match_title: 'Arsenal - Chelsea',
    market: 'O/U',
    selection: 'Over 2.5',
    odds: 1.92,
    stake: 30,
    result: 'LOSS',
    placed_at: '2026-04-20T11:00:00Z',
    resolved_at: '2026-04-20T20:30:00Z',
  },
];

const roiByMarket: ROIByMarketItem[] = [
  { market: '1X2', roi_pct: 14.2, n: 18, wins: 11, losses: 6, voids: 1 },
];

const useBankrollMock = vi.fn();
const useBankrollBetsMock = vi.fn();
const useROIByMarketMock = vi.fn();

vi.mock('@/hooks/v2/useBankroll', () => ({
  useBankroll: () => useBankrollMock(),
}));
vi.mock('@/hooks/v2/useBankrollBets', () => ({
  useBankrollBets: () => useBankrollBetsMock(),
  useUpdateBet: () => ({ mutate: vi.fn() }),
  useDeleteBet: () => ({ mutate: vi.fn() }),
}));
vi.mock('@/hooks/v2/useROIByMarket', () => ({
  useROIByMarket: () => useROIByMarketMock(),
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

describe('BankrollTab', () => {
  it('renders header, KPI strip, charts, bets table when everything is ready', () => {
    useBankrollMock.mockReturnValue({ data: bankroll, isLoading: false });
    useBankrollBetsMock.mockReturnValue({ data: bets, isLoading: false });
    useROIByMarketMock.mockReturnValue({ data: roiByMarket, isLoading: false });

    render(wrap(<BankrollTab />));
    expect(screen.getByTestId('bankroll-tab')).toBeInTheDocument();
    expect(screen.getByTestId('mock-bankroll-header')).toBeInTheDocument();
    expect(screen.getByTestId('kpi-strip-5')).toBeInTheDocument();
    expect(screen.getByTestId('bankroll-chart')).toBeInTheDocument();
    expect(screen.getByTestId('roi-by-market')).toBeInTheDocument();
    expect(screen.getByTestId('bets-table')).toBeInTheDocument();
    expect(screen.getByText('PSG - Lens')).toBeInTheDocument();
  });

  it('renders a skeleton block while the bankroll summary is loading', () => {
    useBankrollMock.mockReturnValue({ data: undefined, isLoading: true });
    useBankrollBetsMock.mockReturnValue({ data: [], isLoading: false });
    useROIByMarketMock.mockReturnValue({ data: [], isLoading: false });

    render(wrap(<BankrollTab />));
    expect(screen.getByTestId('bankroll-skeleton')).toBeInTheDocument();
    expect(screen.queryByTestId('kpi-strip-5')).not.toBeInTheDocument();
  });

  it('renders an error state when the bankroll summary fails', () => {
    useBankrollMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('boom'),
    });
    useBankrollBetsMock.mockReturnValue({ data: [], isLoading: false });
    useROIByMarketMock.mockReturnValue({ data: [], isLoading: false });

    render(wrap(<BankrollTab />));
    expect(screen.getByTestId('bankroll-error')).toBeInTheDocument();
  });

  it('renders an empty state message when there is no bet', () => {
    useBankrollMock.mockReturnValue({ data: bankroll, isLoading: false });
    useBankrollBetsMock.mockReturnValue({ data: [], isLoading: false });
    useROIByMarketMock.mockReturnValue({ data: [], isLoading: false });

    render(wrap(<BankrollTab />));
    expect(screen.getByTestId('bankroll-empty')).toBeInTheDocument();
  });

  it('exposes data-testid="bankroll-tab" on the root', () => {
    useBankrollMock.mockReturnValue({ data: bankroll, isLoading: false });
    useBankrollBetsMock.mockReturnValue({ data: bets, isLoading: false });
    useROIByMarketMock.mockReturnValue({ data: roiByMarket, isLoading: false });
    render(wrap(<BankrollTab />));
    expect(screen.getByTestId('bankroll-tab')).toBeInTheDocument();
  });

  it('has no axe violations in the ready state', async () => {
    useBankrollMock.mockReturnValue({ data: bankroll, isLoading: false });
    useBankrollBetsMock.mockReturnValue({ data: bets, isLoading: false });
    useROIByMarketMock.mockReturnValue({ data: roiByMarket, isLoading: false });
    const { container } = render(wrap(<BankrollTab />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
