import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ProfileTab } from './ProfileTab';

vi.mock('@/hooks/v2/useProfile', () => ({
  useProfile: () => ({
    data: { email: 'demo@probalab.net', pseudo: 'demo', role: 'premium' },
    isLoading: false,
  }),
  useUpdateProfile: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useChangePassword: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteAccount: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

describe('ProfileTab', () => {
  it('renders the profile form sections', () => {
    render(wrap(<ProfileTab />));
    expect(
      screen.getByRole('heading', { level: 2, name: /informations/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /changer le mot de passe/i }),
    ).toBeInTheDocument();
  });

  it('exposes a data-testid on the root for e2e selection', () => {
    render(wrap(<ProfileTab />));
    expect(screen.getByTestId('profile-tab')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<ProfileTab />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
