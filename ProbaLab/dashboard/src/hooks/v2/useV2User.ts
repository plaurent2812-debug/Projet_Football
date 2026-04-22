import { useAuth } from '@/lib/auth';
import type { UserRole } from '@/types/v2/common';

export interface V2User {
  role: UserRole;
  isVisitor: boolean;
  trialDaysLeft?: number;
}

const E2E_ROLE_STORAGE_KEY = '__e2e_role__';
const ALLOWED_E2E_ROLES: readonly UserRole[] = [
  'visitor',
  'free',
  'trial',
  'premium',
  'admin',
];

/**
 * Reads the E2E role override from `localStorage` in dev bundles only.
 *
 * The Playwright auth fixture sets `__e2e_role__` to flip the gating
 * tree without needing a real Supabase session. Prod builds never hit
 * this branch because `import.meta.env.DEV` is compiled away.
 */
function readE2eRole(): UserRole | null {
  if (!import.meta.env.DEV) return null;
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(E2E_ROLE_STORAGE_KEY);
    if (!raw) return null;
    return (ALLOWED_E2E_ROLES as readonly string[]).includes(raw)
      ? (raw as UserRole)
      : null;
  } catch {
    return null;
  }
}

/**
 * Thin wrapper around the legacy `useAuth` context that maps the
 * profile role onto the V2 `UserRole` union.
 * Returns `visitor` when the user is not authenticated.
 */
export function useV2User(): V2User {
  const e2eRole = readE2eRole();
  if (e2eRole) {
    if (e2eRole === 'visitor') return { role: 'visitor', isVisitor: true };
    return {
      role: e2eRole,
      isVisitor: false,
      trialDaysLeft: e2eRole === 'trial' ? 18 : undefined,
    };
  }
  const { user, role } = useAuth();
  if (!user) return { role: 'visitor', isVisitor: true };
  const mapped: UserRole =
    role === 'premium' || role === 'admin' || role === 'trial' || role === 'free'
      ? (role as UserRole)
      : 'free';
  return { role: mapped, isVisitor: false };
}
