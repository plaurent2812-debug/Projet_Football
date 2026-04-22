import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { LeagueGroup } from './LeagueGroup';
import { leagueL1 } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

describe('LeagueGroup', () => {
  it('renders league name and count', () => {
    render(
      <LeagueGroup league={leagueL1} count={3}>
        <div>row</div>
      </LeagueGroup>,
    );
    expect(screen.getByText(/Ligue 1/i)).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders children inside', () => {
    render(
      <LeagueGroup league={leagueL1} count={1}>
        <div data-testid="child">child-content</div>
      </LeagueGroup>,
    );
    expect(screen.getByTestId('child')).toHaveTextContent('child-content');
  });

  it('applies league color to header', () => {
    render(
      <LeagueGroup league={leagueL1} count={1}>
        <div />
      </LeagueGroup>,
    );
    const header = screen.getByRole('heading', { name: /Ligue 1/i });
    expect(header).toHaveStyle({ backgroundColor: 'rgb(37, 99, 235)' });
  });

  it('accepts data-testid prop', () => {
    render(
      <LeagueGroup league={leagueL1} count={1} data-testid="league-group">
        <div />
      </LeagueGroup>,
    );
    expect(screen.getByTestId('league-group')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      <LeagueGroup league={leagueL1} count={1}>
        <div />
      </LeagueGroup>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
