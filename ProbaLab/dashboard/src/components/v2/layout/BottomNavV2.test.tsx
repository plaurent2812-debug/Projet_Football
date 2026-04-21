import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'jest-axe';
import { BottomNavV2 } from './BottomNavV2';

describe('BottomNavV2', () => {
  it('renders 3 nav items', () => {
    render(
      <MemoryRouter>
        <BottomNavV2 />
      </MemoryRouter>
    );
    expect(screen.getByRole('link', { name: /accueil/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /matchs/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /compte/i })).toBeInTheDocument();
  });

  it('is labeled as navigation landmark', () => {
    render(
      <MemoryRouter>
        <BottomNavV2 />
      </MemoryRouter>
    );
    expect(screen.getByRole('navigation', { name: /navigation mobile/i })).toBeInTheDocument();
  });

  it('is hidden on desktop (>= md) via responsive classes', () => {
    render(
      <MemoryRouter>
        <BottomNavV2 />
      </MemoryRouter>
    );
    const nav = screen.getByRole('navigation', { name: /navigation mobile/i });
    expect(nav.className).toMatch(/flex/);
    expect(nav.className).toMatch(/md:hidden/);
  });

  it('marks Accueil as current page on /', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <BottomNavV2 />
      </MemoryRouter>
    );
    const accueil = screen.getByRole('link', { name: /accueil/i });
    expect(accueil).toHaveAttribute('aria-current', 'page');
  });

  it('marks Matchs as current page on /matchs/42', () => {
    render(
      <MemoryRouter initialEntries={['/matchs/42']}>
        <BottomNavV2 />
      </MemoryRouter>
    );
    const matchs = screen.getByRole('link', { name: /matchs/i });
    expect(matchs).toHaveAttribute('aria-current', 'page');
    const accueil = screen.getByRole('link', { name: /accueil/i });
    expect(accueil).not.toHaveAttribute('aria-current');
  });

  it('marks Compte as current page on /compte', () => {
    render(
      <MemoryRouter initialEntries={['/compte']}>
        <BottomNavV2 />
      </MemoryRouter>
    );
    const compte = screen.getByRole('link', { name: /compte/i });
    expect(compte).toHaveAttribute('aria-current', 'page');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <BottomNavV2 />
      </MemoryRouter>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
