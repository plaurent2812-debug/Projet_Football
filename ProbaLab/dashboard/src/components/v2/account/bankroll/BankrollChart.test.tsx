import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { BankrollChart } from './BankrollChart';

// Stub the lazy chunk so tests stay sync and lightweight.
vi.mock('./BankrollChartImpl', () => ({
  __esModule: true,
  default: ({ curve }: { curve: Array<{ date: string; balance: number }> }) => (
    <div data-testid="bankroll-chart-stub">{curve.length} points</div>
  ),
  BankrollChartImpl: ({
    curve,
  }: {
    curve: Array<{ date: string; balance: number }>;
  }) => <div data-testid="bankroll-chart-stub">{curve.length} points</div>,
}));

// 120 daily points anchored in the past so `7j` and `30j` slices actually differ.
const now = Date.now();
const curve: Array<{ date: string; balance: number }> = Array.from(
  { length: 120 },
  (_, i) => ({
    date: new Date(now - (119 - i) * 86400_000).toISOString(),
    balance: 1000 + i * 2,
  }),
);

describe('BankrollChart', () => {
  it('renders the four range toggles', () => {
    render(<BankrollChart curve={curve} />);
    for (const label of ['7j', '30j', '90j', 'Tout']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    }
  });

  it('defaults to 30j active (aria-pressed)', () => {
    render(<BankrollChart curve={curve} />);
    expect(screen.getByRole('button', { name: '30j' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: '90j' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('switches to 7j when clicked and reduces the points count', async () => {
    const user = userEvent.setup();
    render(<BankrollChart curve={curve} />);
    await waitFor(() =>
      expect(screen.getByTestId('bankroll-chart-stub')).toBeInTheDocument(),
    );
    const ninety = screen.getByRole('button', { name: '90j' });
    await user.click(ninety);
    expect(ninety).toHaveAttribute('aria-pressed', 'true');
    // 90j slice must be strictly larger than 7j slice and smaller than `Tout`.
    const afterNinety = Number(
      screen.getByTestId('bankroll-chart-stub').textContent?.split(' ')[0],
    );
    await user.click(screen.getByRole('button', { name: '7j' }));
    const afterSeven = Number(
      screen.getByTestId('bankroll-chart-stub').textContent?.split(' ')[0],
    );
    expect(afterSeven).toBeLessThan(afterNinety);
  });

  it('shows all points when "Tout" is active', async () => {
    const user = userEvent.setup();
    render(<BankrollChart curve={curve} />);
    await waitFor(() =>
      expect(screen.getByTestId('bankroll-chart-stub')).toBeInTheDocument(),
    );
    await user.click(screen.getByRole('button', { name: 'Tout' }));
    expect(screen.getByTestId('bankroll-chart-stub')).toHaveTextContent(
      '120 points',
    );
  });

  it('renders the lazy chart inside a Suspense boundary', async () => {
    render(<BankrollChart curve={curve} />);
    await waitFor(() =>
      expect(screen.getByTestId('bankroll-chart-stub')).toBeInTheDocument(),
    );
  });

  it('forwards the data-testid prop', () => {
    render(<BankrollChart curve={curve} data-testid="my-chart" />);
    expect(screen.getByTestId('my-chart')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<BankrollChart curve={curve} />);
    await waitFor(() =>
      expect(screen.getByTestId('bankroll-chart-stub')).toBeInTheDocument(),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
