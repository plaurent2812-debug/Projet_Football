import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'jest-axe';
import { TrialBanner } from './TrialBanner';

describe('TrialBanner', () => {
  it('renders daysLeft and end date', () => {
    render(
      <MemoryRouter>
        <TrialBanner daysLeft={12} endDate="2026-05-21" />
      </MemoryRouter>,
    );
    expect(screen.getByText(/j-12/i)).toBeInTheDocument();
    expect(screen.getByText(/2026-05-21/)).toBeInTheDocument();
  });

  it('renders without end date', () => {
    render(
      <MemoryRouter>
        <TrialBanner daysLeft={5} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/j-5/i)).toBeInTheDocument();
  });

  it('includes a link to activate subscription', () => {
    render(
      <MemoryRouter>
        <TrialBanner daysLeft={3} />
      </MemoryRouter>,
    );
    const link = screen.getByRole('link', { name: /activer l'abonnement/i });
    expect(link).toHaveAttribute('href', '/premium');
  });

  it('is a region landmark labeled Trial', () => {
    render(
      <MemoryRouter>
        <TrialBanner daysLeft={12} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('region', { name: /trial/i })).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <TrialBanner daysLeft={12} endDate="2026-05-21" />
      </MemoryRouter>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
