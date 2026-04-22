import { AlertCircle, Plus } from 'lucide-react';
import { useNotificationRules } from '@/hooks/v2/useNotificationRules';
import type { NotificationRule } from '@/lib/v2/schemas/rules';
import { RuleRow } from './RuleRow';

export interface RulesListProps {
  onCreate: () => void;
  onEdit: (rule: NotificationRule) => void;
  onDeleteRequest: (rule: NotificationRule) => void;
  'data-testid'?: string;
}

/**
 * Section wrapping the list of the user's notification rules.
 *
 * Header : title + "+ Nouvelle règle" button. Body : one `<RuleRow />`
 * per rule, or a soft empty state when none are configured yet.
 * The loading skeleton and the error banner are owned here so each row
 * stays focused on rendering one rule.
 *
 * All mutations are handled by the rows + the parent's modal lifecycle.
 */
export function RulesList({
  onCreate,
  onEdit,
  onDeleteRequest,
  'data-testid': dataTestId = 'rules-list',
}: RulesListProps) {
  const { data, isLoading, isError, error } = useNotificationRules();

  return (
    <section
      data-testid={dataTestId}
      aria-label="Règles de notification"
      className="space-y-3"
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          Règles actives
        </h2>
        <button
          type="button"
          data-testid="new-rule-button"
          onClick={onCreate}
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Nouvelle règle
        </button>
      </header>

      {isLoading && (
        <div
          data-testid="rules-list-skeleton"
          aria-busy="true"
          aria-label="Chargement des règles"
          className="space-y-3"
        >
          <div className="h-20 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900" />
          <div className="h-20 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900" />
        </div>
      )}

      {isError && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300"
        >
          <AlertCircle className="mt-0.5 h-4 w-4" aria-hidden="true" />
          <div>
            <strong>Erreur de chargement des règles.</strong>
            <p className="mt-1 text-rose-600 dark:text-rose-400">
              {error instanceof Error ? error.message : 'Erreur inconnue'}
            </p>
          </div>
        </div>
      )}

      {!isLoading && !isError && data && data.length === 0 && (
        <div
          data-testid="rules-list-empty"
          className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"
        >
          <p className="font-medium text-slate-700 dark:text-slate-200">
            Aucune règle configurée.
          </p>
          <p className="mt-1">
            Crée une règle pour recevoir des alertes ciblées (edge minimum,
            ligues, drawdown…).
          </p>
        </div>
      )}

      {!isLoading && !isError && data && data.length > 0 && (
        <div className="space-y-2">
          {data.map((rule) => (
            <RuleRow
              key={rule.id ?? rule.name}
              rule={rule}
              onEdit={onEdit}
              onDeleteRequest={onDeleteRequest}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export default RulesList;
