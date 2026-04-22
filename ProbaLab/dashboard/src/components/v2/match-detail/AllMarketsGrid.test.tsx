import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { AllMarketsGrid } from './AllMarketsGrid';
import type { MarketProb } from '../../../types/v2/match-detail';

const markets: MarketProb[] = [
  {
    market_key: '1x2.home',
    label: 'Victoire Nice',
    probability: 0.52,
    fair_odds: 1.92,
    best_book_odds: 2.1,
    is_value: true,
    edge: 0.08,
  },
  {
    market_key: '1x2.draw',
    label: 'Match nul',
    probability: 0.26,
    fair_odds: 3.85,
    best_book_odds: 3.5,
    is_value: false,
    edge: null,
  },
  {
    market_key: '1x2.away',
    label: 'Victoire Lens',
    probability: 0.22,
    fair_odds: 4.5,
    best_book_odds: 4.4,
    is_value: false,
    edge: null,
  },
  {
    market_key: 'dc.1X',
    label: 'Double Chance 1X',
    probability: 0.78,
    fair_odds: 1.28,
    best_book_odds: 1.3,
    is_value: true,
    edge: 0.02,
  },
  {
    market_key: 'btts.yes',
    label: 'BTTS Oui',
    probability: 0.58,
    fair_odds: 1.72,
    best_book_odds: 1.85,
    is_value: true,
    edge: 0.05,
  },
  {
    market_key: 'over25',
    label: 'Plus de 2.5 buts',
    probability: 0.55,
    fair_odds: 1.82,
    best_book_odds: 1.95,
    is_value: false,
    edge: null,
  },
];

describe('AllMarketsGrid', () => {
  it('renders the section heading', () => {
    render(<AllMarketsGrid markets={markets} userRole="premium" />);
    expect(
      screen.getByRole('heading', { name: /tous les marchés/i }),
    ).toBeInTheDocument();
  });

  it('premium renders one cell per market', () => {
    render(<AllMarketsGrid markets={markets} userRole="premium" />);
    expect(screen.getAllByTestId('market-cell')).toHaveLength(markets.length);
  });

  it('trial sees all markets with no lock', () => {
    render(<AllMarketsGrid markets={markets} userRole="trial" />);
    expect(screen.getAllByTestId('market-cell')).toHaveLength(markets.length);
    expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
  });

  it('highlights value bets visually', () => {
    render(<AllMarketsGrid markets={markets} userRole="premium" />);
    const cells = screen.getAllByTestId('market-cell');
    // First (is_value=true), second (is_value=false)
    expect(cells[0]).toHaveAttribute('data-value', 'true');
    expect(cells[1]).toHaveAttribute('data-value', 'false');
  });

  it('renders aria-label with probability percent', () => {
    render(<AllMarketsGrid markets={markets} userRole="premium" />);
    expect(
      screen.getByLabelText(/Victoire Nice, probabilité 52%/),
    ).toBeInTheDocument();
  });

  it('renders best_book_odds when available, falls back to fair_odds', () => {
    const m: MarketProb[] = [
      {
        market_key: 'x',
        label: 'M1',
        probability: 0.5,
        fair_odds: 2.0,
        best_book_odds: 2.1,
        is_value: false,
        edge: null,
      },
      {
        market_key: 'y',
        label: 'M2',
        probability: 0.4,
        fair_odds: 2.5,
        best_book_odds: null,
        is_value: false,
        edge: null,
      },
    ];
    render(<AllMarketsGrid markets={m} userRole="premium" />);
    expect(screen.getByText('2.10')).toBeInTheDocument();
    expect(screen.getByText('2.50')).toBeInTheDocument();
  });

  it('free user sees 1x2 markets unlocked and others behind a lock', () => {
    render(<AllMarketsGrid markets={markets} userRole="free" />);
    // 3 * 1x2 + 3 others = 6 cells rendered in DOM
    expect(screen.getAllByTestId('market-cell')).toHaveLength(markets.length);
    // At least one lock overlay visible
    expect(screen.getAllByTestId('lock-overlay').length).toBeGreaterThan(0);
  });

  it('visitor user has everything locked', () => {
    render(<AllMarketsGrid markets={markets} userRole="visitor" />);
    expect(screen.getByTestId('lock-overlay')).toBeInTheDocument();
  });

  it('renders nothing substantive when markets is empty', () => {
    render(<AllMarketsGrid markets={[]} userRole="premium" />);
    expect(screen.queryAllByTestId('market-cell')).toHaveLength(0);
  });

  it('accepts a custom data-testid on the root', () => {
    render(
      <AllMarketsGrid
        markets={markets}
        userRole="premium"
        data-testid="all-markets"
      />,
    );
    expect(screen.getByTestId('all-markets')).toBeInTheDocument();
  });

  it('has no accessibility violations (premium)', async () => {
    const { container } = render(
      <AllMarketsGrid markets={markets} userRole="premium" />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations (free gated)', async () => {
    const { container } = render(
      <AllMarketsGrid markets={markets} userRole="free" />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
