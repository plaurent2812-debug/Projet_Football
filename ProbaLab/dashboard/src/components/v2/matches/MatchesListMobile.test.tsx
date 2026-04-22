import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MatchesListMobile } from './MatchesListMobile';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

function renderList(matches = mockMatches) {
  return render(
    <MemoryRouter>
      <MatchesListMobile matches={matches} />
    </MemoryRouter>,
  );
}

describe('MatchesListMobile', () => {
  it('groups matches by league', () => {
    renderList();
    expect(screen.getAllByTestId('league-group').length).toBe(3);
  });

  it('renders one MatchRow per fixture', () => {
    renderList();
    // MatchRow default data-testid is 'match-row'
    expect(screen.getAllByTestId('match-row').length).toBe(3);
  });

  it('shows team shorts', () => {
    renderList();
    expect(screen.getByText('PSG')).toBeInTheDocument();
    expect(screen.getByText('ARS')).toBeInTheDocument();
    expect(screen.getByText('INT')).toBeInTheDocument();
  });

  it('shows empty message when no matches', () => {
    renderList([]);
    expect(screen.getByText(/Aucun match/i)).toBeInTheDocument();
  });

  it('accepts data-testid prop', () => {
    render(
      <MemoryRouter>
        <MatchesListMobile matches={mockMatches} data-testid="matches-list-mobile" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('matches-list-mobile')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderList();
    expect(await axe(container)).toHaveNoViolations();
  });
});
