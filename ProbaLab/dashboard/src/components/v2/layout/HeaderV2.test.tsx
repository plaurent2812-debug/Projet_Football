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
