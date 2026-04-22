import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { StatsComparative } from './StatsComparative';
import type { ComparativeStat } from '../../../types/v2/match-detail';

const stats: ComparativeStat[] = [
  { label: 'xG 5 derniers', home_value: 1.8, away_value: 1.2 },
  { label: 'Possession', home_value: 58, away_value: 42, unit: '%' },
];

describe('StatsComparative', () => {
  it('renders one row per stat', () => {
    render(<StatsComparative stats={stats} />);
    expect(screen.getAllByTestId('stat-row')).toHaveLength(2);
  });

  it('renders aria-label per stat with values and unit when present', () => {
    render(<StatsComparative stats={stats} />);
    expect(
      screen.getByLabelText('xG 5 derniers : domicile 1.8, extérieur 1.2'),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Possession : domicile 58%, extérieur 42%'),
    ).toBeInTheDocument();
  });

  it('renders stat label text', () => {
    render(<StatsComparative stats={stats} />);
    expect(screen.getByText('xG 5 derniers')).toBeInTheDocument();
    expect(screen.getByText('Possession')).toBeInTheDocument();
  });

  it('renders numeric values on each side', () => {
    render(<StatsComparative stats={stats} />);
    expect(screen.getByText('1.8')).toBeInTheDocument();
    expect(screen.getByText('1.2')).toBeInTheDocument();
    expect(screen.getByText('58%')).toBeInTheDocument();
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('renders nothing when stats empty', () => {
    const { container } = render(<StatsComparative stats={[]} />);
    expect(container.querySelectorAll('[data-testid="stat-row"]')).toHaveLength(
      0,
    );
  });

  it('handles both values = 0 without crashing', () => {
    render(
      <StatsComparative
        stats={[{ label: 'xG 5 derniers', home_value: 0, away_value: 0 }]}
      />,
    );
    expect(
      screen.getByLabelText('xG 5 derniers : domicile 0, extérieur 0'),
    ).toBeInTheDocument();
  });

  it('accepts an optional label (section heading)', () => {
    render(<StatsComparative stats={stats} label="Stats 5 derniers" />);
    expect(screen.getByRole('heading', { name: 'Stats 5 derniers' })).toBeInTheDocument();
  });

  it('accepts a custom data-testid on the root', () => {
    render(<StatsComparative stats={stats} data-testid="stats" />);
    expect(screen.getByTestId('stats')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<StatsComparative stats={stats} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
