import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { CompositionsSection } from './CompositionsSection';
import type { CompositionsPayload } from '../../../types/v2/match-detail';

const comps: CompositionsPayload = {
  status: 'probable',
  home: {
    formation: '4-3-3',
    starters: [
      { number: 1, name: 'Bulka', position: 'GK' },
      { number: 9, name: 'Moffi', position: 'ST' },
    ],
  },
  away: {
    formation: '4-2-3-1',
    starters: [{ number: 30, name: 'Samba', position: 'GK' }],
  },
};

describe('CompositionsSection', () => {
  it('renders section heading', () => {
    render(
      <CompositionsSection
        compositions={comps}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(
      screen.getByRole('heading', { name: /compositions/i }),
    ).toBeInTheDocument();
  });

  it('renders formations for each team', () => {
    render(
      <CompositionsSection
        compositions={comps}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(screen.getByText('4-3-3')).toBeInTheDocument();
    expect(screen.getByText('4-2-3-1')).toBeInTheDocument();
  });

  it('renders players for home and away', () => {
    render(
      <CompositionsSection
        compositions={comps}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(screen.getByText('Bulka')).toBeInTheDocument();
    expect(screen.getByText('Moffi')).toBeInTheDocument();
    expect(screen.getByText('Samba')).toBeInTheDocument();
  });

  it('shows status badge for probable', () => {
    render(
      <CompositionsSection
        compositions={comps}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(screen.getByText(/probable/i)).toBeInTheDocument();
  });

  it('shows status badge for confirmed', () => {
    render(
      <CompositionsSection
        compositions={{ ...comps, status: 'confirmed' }}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(screen.getByText(/confirm/i)).toBeInTheDocument();
  });

  it('renders fallback when status is unavailable', () => {
    render(
      <CompositionsSection
        compositions={{ status: 'unavailable', home: null, away: null }}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(
      screen.getByText(/compositions non communiquées/i),
    ).toBeInTheDocument();
  });

  it('renders fallback when both lineups are null', () => {
    render(
      <CompositionsSection
        compositions={{ status: 'probable', home: null, away: null }}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(
      screen.getByText(/compositions non communiquées/i),
    ).toBeInTheDocument();
  });

  it('renders team names as section titles', () => {
    render(
      <CompositionsSection
        compositions={comps}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(screen.getByText('Nice')).toBeInTheDocument();
    expect(screen.getByText('Lens')).toBeInTheDocument();
  });

  it('accepts a custom data-testid on the root', () => {
    render(
      <CompositionsSection
        compositions={comps}
        homeName="Nice"
        awayName="Lens"
        data-testid="compos-root"
      />,
    );
    expect(screen.getByTestId('compos-root')).toBeInTheDocument();
  });

  it('has no accessibility violations (probable with lineups)', async () => {
    const { container } = render(
      <CompositionsSection
        compositions={comps}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations (unavailable)', async () => {
    const { container } = render(
      <CompositionsSection
        compositions={{ status: 'unavailable', home: null, away: null }}
        homeName="Nice"
        awayName="Lens"
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
