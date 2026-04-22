import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ValueBetsList } from './ValueBetsList';
import type { ValueBet } from '../../../types/v2/match-detail';

const bets: ValueBet[] = [
  {
    market_key: '1x2.home',
    label: 'Victoire Nice',
    probability: 0.52,
    best_odds: 2.1,
    edge: 0.08,
  },
  {
    market_key: 'btts.yes',
    label: 'Les deux équipes marquent',
    probability: 0.58,
    best_odds: 1.85,
    edge: 0.05,
  },
  {
    market_key: 'over25',
    label: 'Plus de 2.5 buts',
    probability: 0.55,
    best_odds: 1.95,
    edge: 0.04,
  },
];

describe('ValueBetsList', () => {
  it('renders the section heading', () => {
    render(<ValueBetsList valueBets={bets} userRole="premium" />);
    expect(
      screen.getByRole('heading', { name: /value bets/i }),
    ).toBeInTheDocument();
  });

  it('premium sees every value bet and no lock overlay', () => {
    render(<ValueBetsList valueBets={bets} userRole="premium" />);
    expect(screen.getAllByTestId('value-bet-row')).toHaveLength(bets.length);
    expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
  });

  it('trial sees every value bet and no lock overlay', () => {
    render(<ValueBetsList valueBets={bets} userRole="trial" />);
    expect(screen.getAllByTestId('value-bet-row')).toHaveLength(bets.length);
    expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
  });

  it('renders a ValueBadge and OddsChip per row', () => {
    render(<ValueBetsList valueBets={bets} userRole="premium" />);
    const valueBadges = screen.getAllByTestId('value-badge');
    const oddsChips = screen.getAllByTestId('odds-chip');
    expect(valueBadges).toHaveLength(bets.length);
    expect(oddsChips).toHaveLength(bets.length);
  });

  it('free user sees the first bet unlocked and rest behind a lock', () => {
    render(<ValueBetsList valueBets={bets} userRole="free" />);
    // All rows still in DOM (so blurred rows still take layout)
    expect(screen.getAllByTestId('value-bet-row')).toHaveLength(bets.length);
    const lock = screen.getByTestId('lock-overlay');
    expect(lock).toBeInTheDocument();
    expect(lock.textContent).toMatch(/premium/i);
  });

  it('free user with only one value bet has no lock', () => {
    render(
      <ValueBetsList valueBets={[bets[0]]} userRole="free" />,
    );
    expect(screen.queryByTestId('lock-overlay')).not.toBeInTheDocument();
  });

  it('visitor sees a full lock overlay with signup message', () => {
    render(<ValueBetsList valueBets={bets} userRole="visitor" />);
    const lock = screen.getByTestId('lock-overlay');
    expect(lock).toBeInTheDocument();
    expect(lock.textContent).toMatch(/compte/i);
  });

  it('renders an empty state when no value bets are available', () => {
    render(<ValueBetsList valueBets={[]} userRole="premium" />);
    expect(
      screen.getByText(/aucun value bet détecté/i),
    ).toBeInTheDocument();
  });

  it('exposes match context in aria-label when matchTitle is provided', () => {
    render(
      <ValueBetsList
        valueBets={bets}
        userRole="premium"
        matchTitle="Nice vs Lens"
      />,
    );
    const root = screen.getByTestId('value-bets-list');
    expect(root).toHaveAttribute(
      'aria-label',
      expect.stringMatching(/Nice vs Lens/),
    );
  });

  it('accepts a custom data-testid on the root', () => {
    render(
      <ValueBetsList
        valueBets={bets}
        userRole="premium"
        data-testid="vbl"
      />,
    );
    expect(screen.getByTestId('vbl')).toBeInTheDocument();
  });

  it('has no accessibility violations (premium)', async () => {
    const { container } = render(
      <ValueBetsList valueBets={bets} userRole="premium" />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations (free gated)', async () => {
    const { container } = render(
      <ValueBetsList valueBets={bets} userRole="free" />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
