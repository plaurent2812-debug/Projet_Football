import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { KPIStrip5 } from './KPIStrip5';
import type { BankrollSummary } from '@/hooks/v2/useBankroll';

const positive: BankrollSummary = {
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

const negative: BankrollSummary = {
  ...positive,
  current_balance: 820,
  roi_30d: -8.2,
  win_rate: 42.1,
  drawdown_max_pct: -18.5,
};

describe('KPIStrip5', () => {
  it('renders the five tiles with their labels', () => {
    render(<KPIStrip5 bankroll={positive} />);
    expect(screen.getByText(/Bankroll/i)).toBeInTheDocument();
    expect(screen.getByText(/ROI 30J/i)).toBeInTheDocument();
    expect(screen.getByText(/Win rate/i)).toBeInTheDocument();
    expect(screen.getByText(/Drawdown/i)).toBeInTheDocument();
    expect(screen.getByText(/Kelly actif/i)).toBeInTheDocument();
  });

  it('formats the bankroll value with the EUR currency', () => {
    render(<KPIStrip5 bankroll={positive} />);
    // fr-FR narrow-no-break space between digits and symbol, comma decimal.
    expect(screen.getByText(/1\s?284[,.]00\s*€/)).toBeInTheDocument();
  });

  it('shows delta vs initial balance', () => {
    render(<KPIStrip5 bankroll={positive} />);
    // +284€ relative to 1000 initial
    expect(screen.getByText(/\+284/)).toBeInTheDocument();
  });

  it('marks a positive ROI 30d tile with tone=positive', () => {
    render(<KPIStrip5 bankroll={positive} data-testid="kpi-strip" />);
    const tile = screen.getByTestId('tile-roi-30d');
    expect(tile.querySelector('[data-tone]')).toHaveAttribute('data-tone', 'positive');
  });

  it('marks a negative ROI 30d tile with tone=negative', () => {
    render(<KPIStrip5 bankroll={negative} />);
    const tile = screen.getByTestId('tile-roi-30d');
    expect(tile.querySelector('[data-tone]')).toHaveAttribute('data-tone', 'negative');
  });

  it('marks drawdown as negative tone (loss)', () => {
    render(<KPIStrip5 bankroll={positive} />);
    const tile = screen.getByTestId('tile-drawdown');
    expect(tile.querySelector('[data-tone]')).toHaveAttribute('data-tone', 'negative');
  });

  it('exposes the data-testid prop when provided', () => {
    render(<KPIStrip5 bankroll={positive} data-testid="my-kpi" />);
    expect(screen.getByTestId('my-kpi')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<KPIStrip5 bankroll={positive} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
