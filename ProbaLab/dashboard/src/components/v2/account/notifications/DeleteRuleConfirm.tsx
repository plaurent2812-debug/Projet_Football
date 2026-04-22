import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { Modal } from '@/components/v2/system/Modal';
import { useDeleteRule } from '@/hooks/v2/useNotificationRules';
import type { NotificationRule } from '@/lib/v2/schemas/rules';

export interface DeleteRuleConfirmProps {
  rule: NotificationRule | null;
  onOpenChange: (open: boolean) => void;
  'data-testid'?: string;
}

/**
 * Confirmation modal for deleting a rule.
 *
 * The parent decides whether the modal is visible by passing either the
 * candidate `rule` or `null`. On confirm the `useDeleteRule(id)`
 * mutation is called, the rules query cache is invalidated and the
 * parent is notified via `onOpenChange(false)`.
 */
export function DeleteRuleConfirm({
  rule,
  onOpenChange,
  'data-testid': dataTestId = 'delete-rule-confirm',
}: DeleteRuleConfirmProps) {
  const [apiError, setApiError] = useState<string | null>(null);
  const deleteMut = useDeleteRule(rule?.id ?? '');

  const onConfirm = async () => {
    if (!rule?.id) return;
    setApiError(null);
    try {
      await deleteMut.mutateAsync();
      onOpenChange(false);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erreur lors de la suppression';
      setApiError(message);
    }
  };

  return (
    <Modal
      open={rule !== null}
      onOpenChange={onOpenChange}
      title="Supprimer la règle"
      description="Cette action est irréversible."
      data-testid={dataTestId}
      footer={
        <>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Annuler
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={deleteMut.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            {deleteMut.isPending ? 'Suppression…' : 'Supprimer'}
          </button>
        </>
      }
    >
      <p className="text-sm text-slate-700 dark:text-slate-200">
        Supprimer la règle «&nbsp;
        <strong className="font-semibold">{rule?.name ?? ''}</strong>
        &nbsp;» ?
      </p>

      {apiError && (
        <div
          role="alert"
          className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300"
        >
          {apiError}
        </div>
      )}
    </Modal>
  );
}

export default DeleteRuleConfirm;
