import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MatchesTableDesktop } from './MatchesTableDesktop';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

function renderTable(matches = mockMatches) {
  return render(
    <MemoryRouter>
      <MatchesTableDesktop matches={matches} />
    </MemoryRouter>,
  );
}

describe('MatchesTableDesktop', () => {
  it('renders one row per match grouped by league', () => {
    renderTable();
    // 3 fixtures, 3 distinct leagues, so 3 LeagueGroups each with one row
    expect(screen.getAllByTestId('match-row')).toHaveLength(3);
  });

  it('shows kickoff time, team shorts and odd for each row', () => {
    renderTable();
    expect(screen.getByText('PSG')).toBeInTheDocument();
    expect(screen.getByText('LEN')).toBeInTheDocument();
    expect(screen.getByText(/1\.92/)).toBeInTheDocument();
  });

  it('uses analysis-first chips instead of betting jargon', () => {
    renderTable();
    expect(screen.getByText(/Prono recommandé/i)).toBeInTheDocument();
    expect(screen.getByText(/Signal \+7\.2%/i)).toBeInTheDocument();
    expect(screen.queryByText(/SAFE/i)).not.toBeInTheDocument();
  });

  it('renders each match as a decision card with clear sections', () => {
    renderTable();
    const firstRow = screen.getAllByTestId('match-row')[0];

    expect(within(firstRow).getByText(/probabilités/i)).toBeInTheDocument();
    expect(within(firstRow).getByText(/lecture rapide/i)).toBeInTheDocument();
    expect(within(firstRow).getByRole('link', { name: /ouvrir l'analyse/i })).toBeInTheDocument();
  });

  it('renders a detail link per row', () => {
    renderTable();
    const rows = screen.getAllByTestId('match-row');
    rows.forEach((row) => {
      expect(within(row).getAllByRole('link').length).toBeGreaterThan(0);
    });
  });

  it('shows empty message when no matches', () => {
    renderTable([]);
    expect(screen.getByText(/Aucun match/i)).toBeInTheDocument();
  });

  it('accepts data-testid prop', () => {
    render(
      <MemoryRouter>
        <MatchesTableDesktop matches={mockMatches} data-testid="matches-table" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('matches-table')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderTable();
    expect(await axe(container)).toHaveNoViolations();
  });
});
