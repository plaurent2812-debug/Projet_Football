import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ValueBetsTeaser } from './ValueBetsTeaser';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

function wrap(ui: React.ReactElement) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

describe('ValueBetsTeaser', () => {
  it('renders up to 2 value bets with edge and Kelly', () => {
    render(wrap(<ValueBetsTeaser matches={mockMatches} />));
    const edgeMatches = screen.getAllByText(/Kelly/);
    expect(edgeMatches.length).toBeGreaterThanOrEqual(1);
    expect(edgeMatches.length).toBeLessThanOrEqual(2);
  });

  it('blurs the second item for free users', () => {
    render(wrap(<ValueBetsTeaser matches={mockMatches} gating="free" />));
    expect(screen.getByTestId('value-bet-locked')).toBeInTheDocument();
  });

  it('renders nothing when no value bets available', () => {
    const withoutVb = mockMatches.map((m) => ({ ...m, topValueBet: undefined }));
    const { container } = render(wrap(<ValueBetsTeaser matches={withoutVb} />));
    expect(container.firstChild).toBeNull();
  });

  it('links each item to the match detail page', () => {
    render(wrap(<ValueBetsTeaser matches={mockMatches} />));
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveAttribute('href', expect.stringMatching(/^\/matchs\/fx-/));
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<ValueBetsTeaser matches={mockMatches} />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
