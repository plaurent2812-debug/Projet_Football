import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { BetsTable } from './BetsTable';
import type { BetRow } from '@/hooks/v2/useBankrollBets';

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
  {
    id: 'bet-003',
    fixture_id: 'fx-3',
    match_title: 'OL - Rennes',
    market: 'DC',
    selection: '1X',
    odds: 1.4,
    stake: 40,
    result: 'PENDING',
    placed_at: '2026-04-22T08:00:00Z',
    resolved_at: null,
  },
];

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

describe('BetsTable', () => {
  it('renders a row per bet with match title, market and selection', () => {
    render(wrap(<BetsTable bets={bets} />));
    expect(screen.getByText('PSG - Lens')).toBeInTheDocument();
    expect(screen.getByText('Arsenal - Chelsea')).toBeInTheDocument();
    expect(screen.getByText('OL - Rennes')).toBeInTheDocument();
  });

  it('renders the four filter chips', () => {
    render(wrap(<BetsTable bets={bets} />));
    expect(screen.getByRole('button', { name: /tous/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /en cours/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^gagnés$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /perdus/i })).toBeInTheDocument();
  });

  it('defaults to "all" filter (aria-pressed=true)', () => {
    render(wrap(<BetsTable bets={bets} />));
    expect(screen.getByRole('button', { name: /tous/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('filters to only WIN rows when "Gagnés" is clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<BetsTable bets={bets} />));
    await user.click(screen.getByRole('button', { name: /^gagnés$/i }));
    expect(screen.getByText('PSG - Lens')).toBeInTheDocument();
    expect(screen.queryByText('Arsenal - Chelsea')).not.toBeInTheDocument();
    expect(screen.queryByText('OL - Rennes')).not.toBeInTheDocument();
  });

  it('filters to only PENDING rows when "En cours" is clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<BetsTable bets={bets} />));
    await user.click(screen.getByRole('button', { name: /en cours/i }));
    expect(screen.getByText('OL - Rennes')).toBeInTheDocument();
    expect(screen.queryByText('PSG - Lens')).not.toBeInTheDocument();
  });

  it('renders an empty state when no bet matches the filter', async () => {
    const user = userEvent.setup();
    const onlyLosses: BetRow[] = [bets[1]];
    render(wrap(<BetsTable bets={onlyLosses} />));
    await user.click(screen.getByRole('button', { name: /^gagnés$/i }));
    expect(screen.getByTestId('bets-empty')).toBeInTheDocument();
  });

  it('tags each row with a data-status attribute for styling', () => {
    render(wrap(<BetsTable bets={bets} />));
    expect(screen.getByTestId('bet-row-bet-001')).toHaveAttribute(
      'data-status',
      'WIN',
    );
    expect(screen.getByTestId('bet-row-bet-002')).toHaveAttribute(
      'data-status',
      'LOSS',
    );
    expect(screen.getByTestId('bet-row-bet-003')).toHaveAttribute(
      'data-status',
      'PENDING',
    );
  });

  it('opens the action menu on trigger click and lists the three actions', async () => {
    const user = userEvent.setup();
    render(wrap(<BetsTable bets={bets} />));
    const trigger = screen.getByTestId('bet-actions-bet-003');
    await user.click(trigger);
    const menu = screen.getByRole('menu');
    expect(within(menu).getByRole('menuitem', { name: /gagné/i })).toBeInTheDocument();
    expect(within(menu).getByRole('menuitem', { name: /perdu/i })).toBeInTheDocument();
    expect(within(menu).getByRole('menuitem', { name: /supprimer/i })).toBeInTheDocument();
  });

  it('calls onUpdateResult with WIN when "Marquer gagné" is clicked', async () => {
    const user = userEvent.setup();
    const onUpdateResult = vi.fn();
    render(wrap(<BetsTable bets={bets} onUpdateResult={onUpdateResult} />));
    await user.click(screen.getByTestId('bet-actions-bet-003'));
    await user.click(screen.getByRole('menuitem', { name: /gagné/i }));
    expect(onUpdateResult).toHaveBeenCalledWith('bet-003', 'WIN');
  });

  it('calls onUpdateResult with LOSS when "Marquer perdu" is clicked', async () => {
    const user = userEvent.setup();
    const onUpdateResult = vi.fn();
    render(wrap(<BetsTable bets={bets} onUpdateResult={onUpdateResult} />));
    await user.click(screen.getByTestId('bet-actions-bet-003'));
    await user.click(screen.getByRole('menuitem', { name: /perdu/i }));
    expect(onUpdateResult).toHaveBeenCalledWith('bet-003', 'LOSS');
  });

  it('calls onDelete when "Supprimer" is clicked', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(wrap(<BetsTable bets={bets} onDelete={onDelete} />));
    await user.click(screen.getByTestId('bet-actions-bet-002'));
    await user.click(screen.getByRole('menuitem', { name: /supprimer/i }));
    expect(onDelete).toHaveBeenCalledWith('bet-002');
  });

  it('closes the menu after selecting an action', async () => {
    const user = userEvent.setup();
    render(wrap(<BetsTable bets={bets} onUpdateResult={vi.fn()} />));
    await user.click(screen.getByTestId('bet-actions-bet-003'));
    await user.click(screen.getByRole('menuitem', { name: /gagné/i }));
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('formats the stake as euros', () => {
    render(wrap(<BetsTable bets={bets} />));
    expect(screen.getAllByText(/25[,.]00\s*€/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/30[,.]00\s*€/).length).toBeGreaterThan(0);
  });

  it('formats the odds with two decimals', () => {
    render(wrap(<BetsTable bets={bets} />));
    expect(screen.getAllByText(/1\.85/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/1\.92/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/1\.40/).length).toBeGreaterThan(0);
  });

  it('exposes a custom data-testid when provided', () => {
    render(wrap(<BetsTable bets={bets} data-testid="bets-table-custom" />));
    expect(screen.getByTestId('bets-table-custom')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<BetsTable bets={bets} />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
