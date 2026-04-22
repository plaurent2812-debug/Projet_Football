import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'jest-axe';
import { PremiumHero } from './PremiumHero';

function wrap(ui: React.ReactElement) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

describe('PremiumHero', () => {
  it('renders the emerald label, main headline and CLV subtitle', () => {
    render(wrap(<PremiumHero />));
    expect(screen.getByText(/PROBALAB PREMIUM/i)).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 1, name: /parier avec une vraie probabilité/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/CLV/i)).toBeInTheDocument();
  });

  it('exposes a primary CTA linking to /register', () => {
    render(wrap(<PremiumHero />));
    const primary = screen.getByRole('link', { name: /essai gratuit/i });
    expect(primary).toHaveAttribute('href', '/register');
  });

  it('renders a secondary CTA that smooth-scrolls to #track-record', async () => {
    const scrollIntoView = vi.fn();
    // Stub scrollIntoView on any new element.
    Element.prototype.scrollIntoView = scrollIntoView;

    // Inject a target anchor in the DOM so querySelector resolves.
    const target = document.createElement('section');
    target.id = 'track-record';
    document.body.appendChild(target);

    const user = userEvent.setup();
    render(wrap(<PremiumHero />));
    const secondary = screen.getByRole('button', { name: /voir le track record live/i });
    await user.click(secondary);
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });

    document.body.removeChild(target);
  });

  it('accepts a custom data-testid prop', () => {
    render(wrap(<PremiumHero data-testid="hero-x" />));
    expect(screen.getByTestId('hero-x')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<PremiumHero />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
