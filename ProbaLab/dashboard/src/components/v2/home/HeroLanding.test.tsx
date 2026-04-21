import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { HeroLanding } from './HeroLanding';

expect.extend(toHaveNoViolations);

function wrap(ui: React.ReactElement) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

describe('HeroLanding', () => {
  it('renders the PROBALAB label and headline', () => {
    render(wrap(<HeroLanding />));
    expect(screen.getByText(/PROBALAB/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      /vraie probabilité/i,
    );
  });

  it('renders primary CTA to /register and secondary to /premium', () => {
    render(wrap(<HeroLanding />));
    const primary = screen.getByRole('link', { name: /Essai gratuit 30 jours/i });
    expect(primary).toHaveAttribute('href', '/register');
    const secondary = screen.getByRole('link', { name: /Découvrir Premium/i });
    expect(secondary).toHaveAttribute('href', '/premium');
  });

  it('mentions no credit card required', () => {
    render(wrap(<HeroLanding />));
    expect(screen.getByText(/Aucune carte/i)).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<HeroLanding />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
