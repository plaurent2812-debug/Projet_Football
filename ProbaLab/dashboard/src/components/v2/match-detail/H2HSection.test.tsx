import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { H2HSection } from './H2HSection';
import type { H2HSummary } from '../../../types/v2/match-detail';

const h2h: H2HSummary = {
  home_wins: 7,
  draws: 2,
  away_wins: 1,
  last_matches: [
    {
      date_utc: '2025-11-04',
      home_team: 'Nice',
      away_team: 'Lens',
      score: '2-1',
    },
    {
      date_utc: '2025-04-18',
      home_team: 'Lens',
      away_team: 'Nice',
      score: '0-0',
    },
    {
      date_utc: '2024-12-02',
      home_team: 'Nice',
      away_team: 'Lens',
      score: '3-1',
    },
  ],
};

describe('H2HSection', () => {
  it('renders the section heading', () => {
    render(<H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />);
    expect(
      screen.getByRole('heading', { name: /face à face/i }),
    ).toBeInTheDocument();
  });

  it('renders the aggregated bar with aria-label (plural wins)', () => {
    render(<H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />);
    expect(
      screen.getByLabelText(
        'Historique : Nice 7 victoires, 2 nuls, Lens 1 victoire',
      ),
    ).toBeInTheDocument();
  });

  it('uses singular « victoire » when a team has exactly 1 win', () => {
    render(<H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />);
    // away_wins = 1 → singular
    expect(
      screen.getByLabelText(/Lens 1 victoire$/),
    ).toBeInTheDocument();
  });

  it('uses singular « nul » when draws = 1', () => {
    const h2hSingle: H2HSummary = { ...h2h, draws: 1 };
    render(<H2HSection h2h={h2hSingle} homeName="Nice" awayName="Lens" />);
    expect(
      screen.getByLabelText(/1 nul,/),
    ).toBeInTheDocument();
  });

  it('lists last 3 matches', () => {
    render(<H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />);
    expect(screen.getAllByTestId('h2h-row')).toHaveLength(3);
  });

  it('renders each match score and teams', () => {
    render(<H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />);
    expect(screen.getByText(/Nice 2-1 Lens/)).toBeInTheDocument();
    expect(screen.getByText(/Lens 0-0 Nice/)).toBeInTheDocument();
    expect(screen.getByText(/Nice 3-1 Lens/)).toBeInTheDocument();
  });

  it('renders labels for wins/draws under the bar', () => {
    render(<H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />);
    expect(screen.getByText(/Nice 7V/)).toBeInTheDocument();
    expect(screen.getByText(/2N/)).toBeInTheDocument();
    expect(screen.getByText(/Lens 1V/)).toBeInTheDocument();
  });

  it('handles zero totals without crashing', () => {
    const empty: H2HSummary = {
      home_wins: 0,
      draws: 0,
      away_wins: 0,
      last_matches: [],
    };
    render(<H2HSection h2h={empty} homeName="Nice" awayName="Lens" />);
    expect(
      screen.getByLabelText(
        'Historique : Nice 0 victoire, 0 nul, Lens 0 victoire',
      ),
    ).toBeInTheDocument();
    expect(screen.queryAllByTestId('h2h-row')).toHaveLength(0);
  });

  it('accepts a custom data-testid on the root', () => {
    render(
      <H2HSection
        h2h={h2h}
        homeName="Nice"
        awayName="Lens"
        data-testid="h2h"
      />,
    );
    expect(screen.getByTestId('h2h')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <H2HSection h2h={h2h} homeName="Nice" awayName="Lens" />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
