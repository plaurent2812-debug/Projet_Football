import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MatchesList } from './MatchesList';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

describe('MatchesList', () => {
  it('groups matches by league with colored header', () => {
    render(
      <MemoryRouter>
        <MatchesList matches={mockMatches} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: /Ligue 1/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Premier League/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Serie A/ })).toBeInTheDocument();
  });

  it('renders each match as a link', () => {
    render(
      <MemoryRouter>
        <MatchesList matches={mockMatches} />
      </MemoryRouter>,
    );
    expect(screen.getAllByRole('link')).toHaveLength(mockMatches.length);
  });

  it('shows default empty state when list is empty', () => {
    render(
      <MemoryRouter>
        <MatchesList matches={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Aucun match/i)).toBeInTheDocument();
  });

  it('shows custom empty message when provided', () => {
    render(
      <MemoryRouter>
        <MatchesList matches={[]} emptyMessage="Rien à afficher" />
      </MemoryRouter>,
    );
    expect(screen.getByText('Rien à afficher')).toBeInTheDocument();
  });

  it('warns (console) but still renders when >50 matches', () => {
    const big = Array.from({ length: 55 }, (_, i) => ({
      ...mockMatches[0],
      fixtureId: `fx-big-${i}`,
    }));
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    render(
      <MemoryRouter>
        <MatchesList matches={big} />
      </MemoryRouter>,
    );
    expect(spy).toHaveBeenCalledWith(expect.stringContaining('virtualization'));
    spy.mockRestore();
  });

  it('accepts a data-testid prop on the root', () => {
    render(
      <MemoryRouter>
        <MatchesList matches={mockMatches} data-testid="my-list" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('my-list')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <MatchesList matches={mockMatches} />
      </MemoryRouter>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
