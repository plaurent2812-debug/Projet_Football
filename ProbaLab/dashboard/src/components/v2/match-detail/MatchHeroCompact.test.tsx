import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MatchHeroCompact } from './MatchHeroCompact';
import type { MatchHeader } from '../../../types/v2/match-detail';

const header: MatchHeader = {
  fixture_id: 42,
  kickoff_utc: '2026-04-22T18:45:00Z',
  stadium: 'Allianz Riviera',
  league_name: 'Ligue 1',
  home: {
    id: 1,
    name: 'Nice',
    logo_url: '/n.png',
    rank: 4,
    form: ['W', 'W', 'D', 'W', 'W'],
  },
  away: {
    id: 2,
    name: 'Lens',
    logo_url: '/l.png',
    rank: 7,
    form: ['L', 'D', 'W', 'L', 'D'],
  },
};

describe('MatchHeroCompact', () => {
  it('renders compact logos at 40px', () => {
    render(<MatchHeroCompact header={header} />);
    const homeImg = screen.getByAltText('Nice logo');
    const awayImg = screen.getByAltText('Lens logo');
    expect(homeImg).toHaveAttribute('width', '40');
    expect(homeImg).toHaveAttribute('height', '40');
    expect(awayImg).toHaveAttribute('width', '40');
    expect(awayImg).toHaveAttribute('height', '40');
  });

  it('shows both team names', () => {
    render(<MatchHeroCompact header={header} />);
    expect(screen.getByText('Nice')).toBeInTheDocument();
    expect(screen.getByText('Lens')).toBeInTheDocument();
  });

  it('renders the league name', () => {
    render(<MatchHeroCompact header={header} />);
    expect(screen.getByText('Ligue 1')).toBeInTheDocument();
  });

  it('renders formatted kickoff inline', () => {
    render(<MatchHeroCompact header={header} />);
    // Europe/Paris -> 20:45
    expect(screen.getByText(/20:45/)).toBeInTheDocument();
  });

  it('renders both form badges', () => {
    render(<MatchHeroCompact header={header} />);
    expect(screen.getByLabelText('Forme récente : V V N V V')).toBeInTheDocument();
    expect(screen.getByLabelText('Forme récente : D N V D N')).toBeInTheDocument();
  });

  it('accepts a custom data-testid on the root', () => {
    render(<MatchHeroCompact header={header} data-testid="hero-compact" />);
    expect(screen.getByTestId('hero-compact')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<MatchHeroCompact header={header} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
