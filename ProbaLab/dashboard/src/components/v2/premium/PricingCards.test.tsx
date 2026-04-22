import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'jest-axe';
import { PricingCards } from './PricingCards';

function wrap(ui: React.ReactElement) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

describe('PricingCards', () => {
  it('renders both Free and Premium cards with the right prices', () => {
    render(wrap(<PricingCards />));
    expect(screen.getByRole('heading', { level: 3, name: /free/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: /^premium$/i })).toBeInTheDocument();
    expect(screen.getByText(/0\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/14[,.]99\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/pour toujours/i)).toBeInTheDocument();
  });

  it('highlights Premium with the RECOMMANDÉ amber badge', () => {
    render(wrap(<PricingCards />));
    expect(screen.getByText(/recommandé/i)).toBeInTheDocument();
  });

  it('renders the Free CTA going to /register', () => {
    render(wrap(<PricingCards />));
    const freeCta = screen.getByRole('link', { name: /créer compte gratuit/i });
    expect(freeCta).toHaveAttribute('href', '/register');
  });

  it('renders the Premium CTA going to /register with trial intent', () => {
    render(wrap(<PricingCards />));
    const trialCta = screen.getByRole('link', { name: /démarrer la trial/i });
    expect(trialCta).toHaveAttribute('href', expect.stringContaining('/register'));
  });

  it('lists distinct feature sets for Free and Premium', () => {
    render(wrap(<PricingCards />));
    // Free has at least one of these.
    expect(screen.getByText(/3 prédictions/i)).toBeInTheDocument();
    // Premium has bankroll + notifications + combos.
    expect(screen.getByText(/bankroll/i)).toBeInTheDocument();
    expect(screen.getByText(/notifications/i)).toBeInTheDocument();
  });

  it('accepts a custom data-testid prop', () => {
    render(wrap(<PricingCards data-testid="pricing-x" />));
    expect(screen.getByTestId('pricing-x')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<PricingCards />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
