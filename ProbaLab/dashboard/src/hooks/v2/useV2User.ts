import { useAuth } from '@/lib/auth';
import type { UserRole } from '@/types/v2/common';

export interface V2User {
  role: UserRole;
  isVisitor: boolean;
  trialDaysLeft?: number;
}

/**
 * Thin wrapper around the legacy `useAuth` context that maps the
 * profile role onto the V2 `UserRole` union.
 * Returns `visitor` when the user is not authenticated.
 */
export function useV2User(): V2User {
  const { user, role } = useAuth();
  if (!user) return { role: 'visitor', isVisitor: true };
  const mapped: UserRole =
    role === 'premium' || role === 'admin' || role === 'trial' || role === 'free'
      ? (role as UserRole)
      : 'free';
  return { role: mapped, isVisitor: false };
}
