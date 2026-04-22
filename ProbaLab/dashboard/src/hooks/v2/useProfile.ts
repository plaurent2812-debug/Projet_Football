import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch, apiPost, apiDelete } from '@/lib/v2/apiClient';

/**
 * User profile — mirrored from `GET /api/user/profile`.
 *
 * `role` is the backend auth tier ; `trialEnd` is only set while the user
 * sits in the 7-day trial window.
 */
export interface ProfileData {
  email: string;
  pseudo: string;
  avatarUrl?: string;
  role: 'free' | 'trial' | 'premium' | 'admin';
  trialEnd?: string;
}

/**
 * Mutation payload for `PATCH /api/user/profile`.
 *
 * Derived from `profileUpdateSchema` in `lib/v2/schemas/profile.ts` —
 * the form validates against that schema before calling the mutation.
 */
export interface UpdateProfileInput {
  pseudo?: string;
  avatarUrl?: string;
  email?: string;
}

const PROFILE_KEY = ['v2', 'user', 'profile'] as const;

export function useProfile() {
  return useQuery({
    queryKey: PROFILE_KEY,
    queryFn: () => apiGet<ProfileData>('/api/user/profile'),
    staleTime: 60 * 1000,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation<ProfileData, Error, UpdateProfileInput>({
    mutationFn: (input) => apiPatch<UpdateProfileInput, ProfileData>('/api/user/profile', input),
    onSuccess: (data) => {
      qc.setQueryData(PROFILE_KEY, data);
    },
  });
}

export interface ChangePasswordInput {
  current: string;
  next: string;
}

export function useChangePassword() {
  return useMutation<void, Error, ChangePasswordInput>({
    mutationFn: (payload) =>
      apiPost<ChangePasswordInput, void>('/api/user/profile/password', payload),
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => apiDelete('/api/user/profile'),
    onSuccess: () => {
      qc.removeQueries({ queryKey: PROFILE_KEY });
    },
  });
}
