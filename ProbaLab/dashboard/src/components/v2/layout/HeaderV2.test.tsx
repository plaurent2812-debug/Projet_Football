import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'jest-axe';
import { HeaderV2 } from './HeaderV2';

describe('HeaderV2', () => {
  it('renders logo and nav links on desktop', () => {
    render(
      <MemoryRouter>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    expect(screen.getByRole('link', { name: /probalab/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /accueil/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /matchs/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /compte/i })).toBeInTheDocument();
  });

  it('shows Free badge when userRole is free', () => {
    render(
      <MemoryRouter>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    expect(screen.getByText('Free')).toBeInTheDocument();
  });

  it('shows Trial J-X badge when userRole is trial', () => {
    render(
      <MemoryRouter>
        <HeaderV2 userRole="trial" trialDaysLeft={12} />
      </MemoryRouter>
    );
    expect(screen.getByText(/trial j-12/i)).toBeInTheDocument();
  });

  it('shows Premium badge when userRole is premium', () => {
    render(
      <MemoryRouter>
        <HeaderV2 userRole="premium" />
      </MemoryRouter>
    );
    expect(screen.getByText('Premium')).toBeInTheDocument();
  });

  it('hides horizontal nav on mobile (< md) via responsive classes', () => {
    render(
      <MemoryRouter>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    const nav = screen.getByRole('navigation', { name: /navigation$/i });
    expect(nav.className).toMatch(/hidden/);
    expect(nav.className).toMatch(/md:flex/);
  });

  it('hides role badge on mobile (< md) via responsive classes', () => {
    render(
      <MemoryRouter>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    const badge = screen.getByLabelText(/statut : free/i);
    expect(badge.className).toMatch(/hidden/);
    expect(badge.className).toMatch(/md:/);
  });

  it('marks Accueil as current page when on /', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    const accueilLinks = screen.getAllByRole('link', { name: /accueil/i });
    // The nav link (not the logo) should be aria-current
    const current = accueilLinks.find((l) => l.getAttribute('aria-current') === 'page');
    expect(current).toBeDefined();
    const matchs = screen.getByRole('link', { name: /^matchs$/i });
    expect(matchs).not.toHaveAttribute('aria-current');
  });

  it('marks Matchs as current page when on /matchs', () => {
    render(
      <MemoryRouter initialEntries={['/matchs']}>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    const matchs = screen.getByRole('link', { name: /^matchs$/i });
    expect(matchs).toHaveAttribute('aria-current', 'page');
  });

  it('marks Matchs as current page on nested /matchs/123', () => {
    render(
      <MemoryRouter initialEntries={['/matchs/123']}>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    const matchs = screen.getByRole('link', { name: /^matchs$/i });
    expect(matchs).toHaveAttribute('aria-current', 'page');
  });

  it('marks Compte as current page when on /compte', () => {
    render(
      <MemoryRouter initialEntries={['/compte']}>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    const compte = screen.getByRole('link', { name: /^compte$/i });
    expect(compte).toHaveAttribute('aria-current', 'page');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <HeaderV2 userRole="free" />
      </MemoryRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
