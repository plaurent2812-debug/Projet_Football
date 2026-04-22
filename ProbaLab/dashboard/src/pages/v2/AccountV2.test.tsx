import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import { AccountV2 } from './AccountV2';
import * as v2User from '@/hooks/v2/useV2User';

function Harness({
  initial = '/compte/profil',
}: {
  initial?: string;
}): ReactElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/compte" element={<AccountV2 />}>
            <Route
              path="profil"
              element={<div data-testid="tab-profile">PROFIL</div>}
            />
            <Route
              path="abonnement"
              element={<div data-testid="tab-sub">ABO</div>}
            />
            <Route
              path="bankroll"
              element={<div data-testid="tab-bk">BK</div>}
            />
            <Route
              path="notifications"
              element={<div data-testid="tab-notif">NOTIF</div>}
            />
          </Route>
          <Route path="/login" element={<div data-testid="login-stub">LOGIN</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function mockUser(
  role: 'visitor' | 'free' | 'trial' | 'premium' | 'admin',
): void {
  vi.spyOn(v2User, 'useV2User').mockReturnValue({
    role,
    isVisitor: role === 'visitor',
  });
}

describe('AccountV2', () => {
  it('renders 4 tab links for a connected user', () => {
    mockUser('premium');
    render(<Harness />);
    expect(screen.getByRole('link', { name: /profil/i })).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /abonnement/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /bankroll/i })).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /notifications/i }),
    ).toBeInTheDocument();
  });

  it('renders outlet content for current route', () => {
    mockUser('premium');
    render(<Harness initial="/compte/bankroll" />);
    expect(screen.getByTestId('tab-bk')).toBeInTheDocument();
  });

  it('navigates between tabs', async () => {
    mockUser('premium');
    const user = userEvent.setup();
    render(<Harness initial="/compte/profil" />);
    expect(screen.getByTestId('tab-profile')).toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: /notifications/i }));
    expect(screen.getByTestId('tab-notif')).toBeInTheDocument();
  });

  it('flags the active tab with aria-current', () => {
    mockUser('premium');
    render(<Harness initial="/compte/abonnement" />);
    const active = screen.getByRole('link', { name: /abonnement/i });
    expect(active).toHaveAttribute('aria-current', 'page');
    const inactive = screen.getByRole('link', { name: /profil/i });
    expect(inactive).not.toHaveAttribute('aria-current', 'page');
  });

  it('redirects visitor to /login', () => {
    mockUser('visitor');
    render(<Harness initial="/compte/profil" />);
    expect(screen.getByTestId('login-stub')).toBeInTheDocument();
    expect(screen.queryByTestId('tab-profile')).not.toBeInTheDocument();
  });

  it('renders the "Mon compte" heading', () => {
    mockUser('premium');
    render(<Harness />);
    expect(
      screen.getByRole('heading', { level: 1, name: /mon compte/i }),
    ).toBeInTheDocument();
  });

  it('wraps tabs in a nav element', () => {
    mockUser('premium');
    render(<Harness />);
    const nav = screen.getByRole('navigation', { name: /onglets du compte/i });
    expect(nav).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    mockUser('premium');
    const { container } = render(<Harness />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
