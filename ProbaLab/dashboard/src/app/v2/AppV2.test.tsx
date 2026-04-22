import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement, ReactNode } from 'react';
import { AppV2Content } from './AppV2';
import * as v2User from '@/hooks/v2/useV2User';

function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('AppV2', () => {
  it('renders HomeV2 at /', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'visitor', isVisitor: true });
    renderWithProviders(
      <MemoryRouter initialEntries={['/']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
      /vraie probabilité/i,
    );
  });

  it('renders MatchesV2 at /matchs', async () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/matchs']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(await screen.findByTestId('matches-v2-page')).toBeInTheDocument();
  });

  it('renders MatchDetailV2 at /matchs/:fixtureId', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'premium', isVisitor: false });
    renderWithProviders(
      <MemoryRouter initialEntries={['/matchs/fx-1']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(await screen.findByTestId('match-detail-v2')).toHaveAttribute(
      'data-fixture-id',
      'fx-1',
    );
  });

  it('renders PremiumV2 at /premium', () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/premium']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByTestId('premium-v2-page')).toBeInTheDocument();
  });

  it('renders AccountV2 with ProfileTab at /compte (index redirect)', () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({
      role: 'premium',
      isVisitor: false,
    });
    renderWithProviders(
      <MemoryRouter initialEntries={['/compte']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(
      screen.getByRole('heading', { level: 1, name: /mon compte/i }),
    ).toBeInTheDocument();
  });

  it('renders the NotificationsTab at /compte/notifications (not the stub)', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({
      role: 'premium',
      isVisitor: false,
    });
    renderWithProviders(
      <MemoryRouter initialEntries={['/compte/notifications']}>
        <AppV2Content />
      </MemoryRouter>,
    );
    // The full page exposes its own h1 — the stub only rendered a
    // dashed WIP block with no heading.
    expect(
      await screen.findByRole('heading', { level: 1, name: /^notifications$/i }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('tab-notifications-stub')).not.toBeInTheDocument();
  });

  it('renders legacy Login at /login', async () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AppV2Content />
      </MemoryRouter>
    );
    // Legacy Login.tsx exposes a Connexion/Inscription tab group.
    expect(
      await screen.findByRole('tab', { name: /connexion/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /inscription/i })).toBeInTheDocument();
  });

  it('redirects /register to /login (no V2 register page in Lot 6)', async () => {
    render(
      <MemoryRouter initialEntries={['/register']}>
        <AppV2Content />
      </MemoryRouter>
    );
    // After the <Navigate replace />, the legacy Login page renders.
    expect(
      await screen.findByRole('tab', { name: /connexion/i }),
    ).toBeInTheDocument();
  });
});

// ── Legacy pages wired into AppV2 (Lot 6 — cutover prep) ─────────
// These assert that routes kept from V1 (admin, perf, legal, auth
// utilities, old /profile alias) don't fall through to a 404 when
// VITE_FRONTEND_V2=true. The legacy pages call `useAuth()`, so we
// mock `@/lib/auth` to avoid pulling in the real Supabase client
// (which would hang on `getSession()` without env vars).
vi.mock('@/lib/auth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/auth')>('@/lib/auth');
  return {
    ...actual,
    useAuth: () => ({
      user: null,
      profile: null,
      role: 'free',
      loading: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      resetPassword: vi.fn(),
      hasAccess: (_requiredRole: string) => false,
      isPremium: false,
      isAdmin: false,
    }),
    Protected: ({
      fallback = null,
    }: {
      children?: ReactNode;
      requiredRole?: string;
      fallback?: ReactNode;
    }) => fallback,
  };
});

describe('AppV2 — legacy pages wired for cutover', () => {
  function renderAt(path: string) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <AppV2Content />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it('renders legacy CGU page at /cgu', async () => {
    renderAt('/cgu');
    expect(
      await screen.findByRole('heading', {
        level: 1,
        name: /conditions générales d'utilisation/i,
      }),
    ).toBeInTheDocument();
  });

  it('renders legacy Confidentialité page at /confidentialite', async () => {
    renderAt('/confidentialite');
    expect(
      await screen.findByRole('heading', {
        level: 1,
        name: /politique de confidentialité/i,
      }),
    ).toBeInTheDocument();
  });

  it('renders legacy UpdatePassword page at /update-password', async () => {
    renderAt('/update-password');
    // The page exposes an <h1>Nouveau mot de passe</h1>.
    expect(
      await screen.findByRole('heading', {
        level: 1,
        name: /nouveau mot de passe/i,
      }),
    ).toBeInTheDocument();
  });

  it('renders legacy Admin route at /admin (guard fallback ok)', () => {
    renderAt('/admin');
    // Admin.tsx self-guards: when no admin session, the fallback
    // "🚫 Accès non autorisé" renders. The critical assertion for
    // cutover is that AppV2 does NOT fall back to a 404 / blank.
    // Either the fallback OR the admin dashboard shell is acceptable.
    // We just assert the LayoutShell wrapper is present and HomeV2 isn't.
    expect(screen.getByTestId('layout-shell')).toBeInTheDocument();
    expect(screen.queryByText(/vraie probabilité/i)).not.toBeInTheDocument();
  });

  it('renders legacy Performance route at /performance with guard', () => {
    renderAt('/performance');
    // Wrapped in <Protected requiredRole="admin"> — without an admin
    // session, the guard fallback renders. This just confirms the
    // route is wired (not a 404) and HomeV2 isn't bleeding through.
    expect(screen.getByTestId('layout-shell')).toBeInTheDocument();
    expect(screen.queryByText(/vraie probabilité/i)).not.toBeInTheDocument();
  });

  it('redirects /profile to /compte/profil (legacy alias)', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({
      role: 'premium',
      isVisitor: false,
    });
    renderAt('/profile');
    // After the <Navigate replace />, AccountV2 renders with ProfileTab.
    expect(
      await screen.findByRole('heading', { level: 1, name: /mon compte/i }),
    ).toBeInTheDocument();
  });
});

// ── Legacy route redirects (Lot 6 — Task 2/3) ─────────────────────
describe('AppV2 — legacy route redirects', () => {
  function renderAt(path: string) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <AppV2Content />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it('redirects /paris-du-soir to /matchs?signal=value (MatchesV2 renders)', async () => {
    renderAt('/paris-du-soir');
    expect(await screen.findByTestId('matches-v2-page')).toBeInTheDocument();
  });

  it('redirects /paris-du-soir/football to MatchesV2', async () => {
    renderAt('/paris-du-soir/football');
    expect(await screen.findByTestId('matches-v2-page')).toBeInTheDocument();
  });

  it('redirects /football to MatchesV2', async () => {
    renderAt('/football');
    expect(await screen.findByTestId('matches-v2-page')).toBeInTheDocument();
  });

  it('redirects /football/match/fx-1 to /matchs/fx-1 (MatchDetailV2)', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'premium', isVisitor: false });
    renderAt('/football/match/fx-1');
    expect(await screen.findByTestId('match-detail-v2')).toHaveAttribute(
      'data-fixture-id',
      'fx-1',
    );
  });

  it('redirects /nhl to MatchesV2', async () => {
    renderAt('/nhl');
    expect(await screen.findByTestId('matches-v2-page')).toBeInTheDocument();
  });

  it('redirects /nhl/match/fx-1 to /matchs/fx-1 (MatchDetailV2)', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'premium', isVisitor: false });
    renderAt('/nhl/match/fx-1');
    expect(await screen.findByTestId('match-detail-v2')).toHaveAttribute(
      'data-fixture-id',
      'fx-1',
    );
  });

  it('redirects /watchlist to AccountV2 bankroll tab', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'premium', isVisitor: false });
    renderAt('/watchlist');
    expect(
      await screen.findByRole('heading', { level: 1, name: /mon compte/i }),
    ).toBeInTheDocument();
  });

  it('redirects /hero-showcase to / (HomeV2)', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'visitor', isVisitor: true });
    renderAt('/hero-showcase');
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
      /vraie probabilité/i,
    );
  });
});
