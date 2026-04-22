import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPut } from '@/lib/v2/apiClient';
import type { BankrollSettings } from '@/lib/v2/schemas';

export const BANKROLL_SETTINGS_KEY = [
  'v2',
  'user',
  'bankroll',
  'settings',
] as const;

export function useBankrollSettings() {
  return useQuery({
    queryKey: BANKROLL_SETTINGS_KEY,
    queryFn: () => apiGet<BankrollSettings>('/api/user/bankroll/settings'),
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateBankrollSettings() {
  const qc = useQueryClient();
  return useMutation<BankrollSettings, Error, BankrollSettings>({
    mutationFn: (input) =>
      apiPut<BankrollSettings, BankrollSettings>('/api/user/bankroll/settings', input),
    onSuccess: (data) => {
      qc.setQueryData(BANKROLL_SETTINGS_KEY, data);
      qc.invalidateQueries({ queryKey: ['v2', 'user', 'bankroll'] });
    },
  });
}
