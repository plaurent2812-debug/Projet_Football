import { lazy, type ReactElement } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
// ── Legacy pages wired into AppV2 (Lot 6 — cutover prep) ────────────
// These pages are NOT rebuilt in the V2 design refresh but must stay
// reachable once VITE_FRONTEND_V2=true. They import @/lib/auth which
// is already provided by AppV2, so no extra provider plumbing needed.
import { Protected } from '../../lib/auth';
import { V2_REDIRECTS, buildRedirectTarget, type RedirectEntry } from './redirects';

const HomeV2 = lazy(() => import('../../pages/v2/HomeV2'));
const MatchesV2 = lazy(() => import('../../pages/v2/MatchesV2'));
const MatchDetailV2 = lazy(() => import('../../pages/v2/MatchDetailV2'));
const PremiumV2 = lazy(() => import('../../pages/v2/PremiumV2'));
const AccountV2 = lazy(() => import('../../pages/v2/AccountV2'));
const ProfileTab = lazy(() => import('../../pages/v2/account/ProfileTab'));
const SubscriptionTab = lazy(() => import('../../pages/v2/account/SubscriptionTab'));
const BankrollTab = lazy(() => import('../../pages/v2/account/BankrollTab'));
const NotificationsTab = lazy(() => import('../../pages/v2/account/NotificationsTab'));
const AdminPage = lazy(() => import('../../pages/Admin'));
const PerformancePage = lazy(() => import('../../pages/Performance'));
const LoginLegacy = lazy(() => import('../../pages/Login'));
const UpdatePasswordPage = lazy(() => import('../../pages/UpdatePassword'));
const CGUPage = lazy(() => import('../../pages/CGU'));
const ConfidentialitePage = lazy(() => import('../../pages/Confidentialite'));

export interface V2Route {
  path: string;
  element: ReactElement;
  isPublic: boolean;
  children?: readonly V2RouteChild[];
}

export interface V2RouteChild {
  path?: string;
  index?: boolean;
  element: ReactElement;
}

/**
 * Wrapper that converts a legacy URL into a V2 `<Navigate replace>` at render.
 *
 * Reads the current location (via `useLocation`) so that query-string
 * preservation and `:id` substitution stay stateless and test-friendly.
 */
function LegacyRedirect({ entry }: { entry: RedirectEntry }) {
  const location = useLocation();
  const target = buildRedirectTarget(
    entry.from,
    location.pathname,
    location.search,
    entry.preserveQuery,
    entry.to,
  );
  return <Navigate to={target} replace />;
}

export const v2Routes: readonly V2Route[] = [
  { path: '/', element: <HomeV2 />, isPublic: true },
  { path: '/matchs', element: <MatchesV2 />, isPublic: true },
  { path: '/matchs/:fixtureId', element: <MatchDetailV2 />, isPublic: true },
  { path: '/premium', element: <PremiumV2 />, isPublic: true },
  {
    path: '/compte',
    element: <AccountV2 />,
    isPublic: false,
    children: [
      { index: true, element: <Navigate to="profil" replace /> },
      { path: 'profil', element: <ProfileTab /> },
      { path: 'abonnement', element: <SubscriptionTab /> },
      { path: 'bankroll', element: <BankrollTab /> },
      { path: 'notifications', element: <NotificationsTab /> },
    ],
  },
  // ── Legacy routes kept for cutover (Lot 6) ────────────────────────
  // Auth pages — legacy Login is the functional implementation; no V2
  // refresh is scheduled inside this Lot. `/register` is intentionally
  // NOT wired here: the legacy Login.tsx exposes both Login + Register
  // tabs on the same route, so redirecting /register -> /login is the
  // cleanest way to keep the visitor experience consistent.
  { path: '/login', element: <LoginLegacy />, isPublic: true },
  { path: '/register', element: <Navigate to="/login" replace />, isPublic: true },
  { path: '/update-password', element: <UpdatePasswordPage />, isPublic: true },
  // Legal pages — fully public.
  { path: '/cgu', element: <CGUPage />, isPublic: true },
  { path: '/confidentialite', element: <ConfidentialitePage />, isPublic: true },
  // Admin surfaces — Admin.tsx self-guards via `<Protected requiredRole="admin">`.
  // Performance.tsx has no internal guard, so wrap it here to mirror
  // AppLegacy's `<AdminGuard>` behavior.
  { path: '/admin', element: <AdminPage />, isPublic: false },
  {
    path: '/performance',
    element: (
      <Protected
        requiredRole="admin"
        fallback={
          <div className="min-h-screen flex items-center justify-center text-muted-foreground">
            🚫 Accès réservé aux administrateurs
          </div>
        }
      >
        <PerformancePage />
      </Protected>
    ),
    isPublic: false,
  },
  // Old /profile legacy URL — redirect to the V2 account hub so old
  // bookmarks and emails keep working.
  { path: '/profile', element: <Navigate to="/compte/profil" replace />, isPublic: false },
  // Legacy redirects (Lot 6 Bloc A) — keep last so real routes take precedence.
  ...V2_REDIRECTS.map<V2Route>((entry) => ({
    path: entry.from,
    element: <LegacyRedirect entry={entry} />,
    isPublic: true,
  })),
] as const;
