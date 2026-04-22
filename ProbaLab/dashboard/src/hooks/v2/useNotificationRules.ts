import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from '@/lib/v2/apiClient';
import type { NotificationRule } from '@/lib/v2/schemas/rules';

export const NOTIF_RULES_KEY = [
  'v2',
  'user',
  'notifications',
  'rules',
] as const;

/**
 * Input for creating a rule : strict `NotificationRule` minus the
 * server-assigned `id`. `action` and `enabled` are required here (no
 * defaults) so the form layer always transmits the user's intent.
 */
export type CreateRuleInput = Omit<NotificationRule, 'id'>;

export function useNotificationRules() {
  return useQuery({
    queryKey: NOTIF_RULES_KEY,
    queryFn: () => apiGet<NotificationRule[]>('/api/user/notifications/rules'),
    staleTime: 30 * 1000,
  });
}

function invalidateRules(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: NOTIF_RULES_KEY });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation<NotificationRule, Error, CreateRuleInput>({
    mutationFn: (input) =>
      apiPost<CreateRuleInput, NotificationRule>(
        '/api/user/notifications/rules',
        input,
      ),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useUpdateRule(id: string) {
  const qc = useQueryClient();
  return useMutation<NotificationRule, Error, NotificationRule>({
    mutationFn: (rule) =>
      apiPut<NotificationRule, NotificationRule>(
        `/api/user/notifications/rules/${id}`,
        rule,
      ),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useDeleteRule(id: string) {
  const qc = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => apiDelete(`/api/user/notifications/rules/${id}`),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useToggleRule(id: string) {
  const qc = useQueryClient();
  return useMutation<NotificationRule, Error, boolean>({
    mutationFn: (enabled) =>
      apiPatch<{ enabled: boolean }, NotificationRule>(
        `/api/user/notifications/rules/${id}`,
        { enabled },
      ),
    onSuccess: () => invalidateRules(qc),
  });
}
