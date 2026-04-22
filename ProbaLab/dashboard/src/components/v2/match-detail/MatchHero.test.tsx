import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MatchHero } from './MatchHero';
import type { MatchHeader } from '../../../types/v2/match-detail';

const baseHeader: MatchHeader = {
  fixture_id: 42,
  kickoff_utc: '2026-04-22T18:45:00Z',
  stadium: 'Allianz Riviera',
  referee: 'Clément Turpin',
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

describe('MatchHero', () => {
  it('renders both team names', () => {
    render(<MatchHero header={baseHeader} />);
    expect(screen.getByText('Nice')).toBeInTheDocument();
    expect(screen.getByText('Lens')).toBeInTheDocument();
  });

  it('renders team ranks when provided', () => {
    render(<MatchHero header={baseHeader} />);
    expect(screen.getByText(/#4/)).toBeInTheDocument();
    expect(screen.getByText(/#7/)).toBeInTheDocument();
  });

  it('renders logos at 64px', () => {
    render(<MatchHero header={baseHeader} />);
    const homeImg = screen.getByAltText('Nice logo');
    const awayImg = screen.getByAltText('Lens logo');
    expect(homeImg).toHaveAttribute('width', '64');
    expect(homeImg).toHaveAttribute('height', '64');
    expect(awayImg).toHaveAttribute('width', '64');
    expect(awayImg).toHaveAttribute('height', '64');
  });

  it('renders league name', () => {
    render(<MatchHero header={baseHeader} />);
    expect(screen.getByText('Ligue 1')).toBeInTheDocument();
  });

  it('renders stadium and referee when present', () => {
    render(<MatchHero header={baseHeader} />);
    expect(screen.getByText(/Allianz Riviera/)).toBeInTheDocument();
    expect(screen.getByText(/Clément Turpin/)).toBeInTheDocument();
  });

  it('does not render referee when absent', () => {
    const header = { ...baseHeader, referee: undefined };
    render(<MatchHero header={header} />);
    expect(screen.queryByText(/Turpin/)).not.toBeInTheDocument();
  });

  it('does not render stadium when absent', () => {
    const header = { ...baseHeader, stadium: undefined };
    render(<MatchHero header={header} />);
    expect(screen.queryByText(/Allianz/)).not.toBeInTheDocument();
  });

  it('omits rank when undefined', () => {
    const header: MatchHeader = {
      ...baseHeader,
      home: { ...baseHeader.home, rank: undefined },
    };
    render(<MatchHero header={header} />);
    expect(screen.queryByText(/#4/)).not.toBeInTheDocument();
    // away rank still rendered
    expect(screen.getByText(/#7/)).toBeInTheDocument();
  });

  it('renders the form badges for both teams', () => {
    render(<MatchHero header={baseHeader} />);
    expect(screen.getByLabelText('Forme récente : V V N V V')).toBeInTheDocument();
    expect(screen.getByLabelText('Forme récente : D N V D N')).toBeInTheDocument();
  });

  it('renders formatted kickoff', () => {
    render(<MatchHero header={baseHeader} />);
    // 2026-04-22T18:45:00Z → Europe/Paris → 22 avril 2026 20:45
    expect(screen.getByText(/22 avril 2026/i)).toBeInTheDocument();
    expect(screen.getByText(/20:45/)).toBeInTheDocument();
  });

  it('accepts a custom data-testid on the root', () => {
    render(<MatchHero header={baseHeader} data-testid="hero" />);
    expect(screen.getByTestId('hero')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<MatchHero header={baseHeader} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
