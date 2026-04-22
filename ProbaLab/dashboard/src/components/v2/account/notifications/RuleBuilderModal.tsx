import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Modal } from '@/components/v2/system/Modal';
import {
  notificationRuleSchema,
  type ConditionType,
  type NotificationRule,
  type RuleChannel,
  type RuleCondition,
} from '@/lib/v2/schemas/rules';
import {
  useCreateRule,
  useUpdateRule,
  type CreateRuleInput,
} from '@/hooks/v2/useNotificationRules';
import { LEAGUE_OPTIONS } from './conditionFields';
import {
  ChannelsPicker,
  ConditionsSection,
  EnabledSwitch,
  LogicToggle,
} from './RuleBuilderFields';

export interface RuleBuilderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialRule?: NotificationRule;
  onSaved?: (rule: NotificationRule) => void;
  'data-testid'?: string;
}

/** Build a fresh condition with a sensible default value for a given type. */
function blankCondition(type: ConditionType): RuleCondition {
  if (type === 'edge_min') return { type, value: 5 };
  if (type === 'league_in') return { type, value: [LEAGUE_OPTIONS[0].value] };
  if (type === 'sport') return { type, value: 'football' };
  if (type === 'confidence') return { type, value: 'HIGH' };
  if (type === 'kickoff_within') return { type, value: 2 };
  return { type, value: 10 };
}

function emptyRule(): CreateRuleInput {
  return {
    name: '',
    conditions: [blankCondition('edge_min')],
    logic: 'AND',
    channels: [],
    action: { notify: true, pauseSuggestion: false },
    enabled: true,
  };
}

/**
 * Composable rule builder. Lets the user define up to three conditions
 * combined via AND/OR and choose the notification channels. Uses
 * react-hook-form with a zod resolver so the validation errors come
 * straight from `notificationRuleSchema` and stay in sync with the API
 * contract.
 *
 * The modal is created (no `initialRule`) or edited (with `initialRule`).
 * On success, the parent receives `onOpenChange(false)` and the rules
 * query cache is invalidated by the underlying mutation hook.
 */
export function RuleBuilderModal({
  open,
  onOpenChange,
  initialRule,
  onSaved,
  'data-testid': dataTestId = 'rule-builder-modal',
}: RuleBuilderModalProps) {
  const createMut = useCreateRule();
  const updateMut = useUpdateRule(initialRule?.id ?? '');
  const isEdit = Boolean(initialRule?.id);
  const [apiError, setApiError] = useState<string | null>(null);

  const defaultValues = useMemo<CreateRuleInput>(
    () => (initialRule ? { ...initialRule } : emptyRule()),
    [initialRule],
  );

  const form = useForm<CreateRuleInput>({
    resolver: zodResolver(notificationRuleSchema),
    defaultValues,
    mode: 'onSubmit',
  });

  // Reset when the modal is (re)opened with a different initial rule.
  useEffect(() => {
    if (!open) return;
    form.reset(defaultValues);
    setApiError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialRule?.id]);

  const conditions = form.watch('conditions');
  const channels = form.watch('channels');
  const logic = form.watch('logic');
  const pauseSuggestion = form.watch('action.pauseSuggestion');
  const enabled = form.watch('enabled');

  const addCondition = () => {
    if (conditions.length >= 3) return;
    form.setValue(
      'conditions',
      [...conditions, blankCondition('edge_min')],
      { shouldValidate: false },
    );
  };

  const removeCondition = (index: number) => {
    if (conditions.length <= 1) return;
    form.setValue(
      'conditions',
      conditions.filter((_, i) => i !== index),
      { shouldValidate: false },
    );
  };

  const updateConditionType = (index: number, type: ConditionType) => {
    form.setValue(`conditions.${index}`, blankCondition(type), {
      shouldValidate: false,
    });
  };

  const toggleChannel = (c: RuleChannel) => {
    const current = channels ?? [];
    const next = current.includes(c)
      ? current.filter((x) => x !== c)
      : [...current, c];
    form.setValue('channels', next, { shouldValidate: false });
  };

  const onSubmit = form.handleSubmit(async (values) => {
    setApiError(null);
    try {
      if (isEdit && initialRule?.id) {
        const saved = await updateMut.mutateAsync({
          ...values,
          id: initialRule.id,
        });
        onSaved?.(saved);
      } else {
        const saved = await createMut.mutateAsync(values);
        onSaved?.(saved);
      }
      onOpenChange(false);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Erreur lors de l'enregistrement";
      setApiError(message);
    }
  });

  const title = isEdit ? 'Modifier la règle' : 'Nouvelle règle';
  const description = isEdit
    ? "Ajuste quand et comment ProbaLab t'envoie cette alerte."
    : "Définis quand et comment ProbaLab t'envoie une alerte.";
  const nameError = form.formState.errors.name?.message;
  const channelsError = form.formState.errors.channels?.message as
    | string
    | undefined;
  const isPending = createMut.isPending || updateMut.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
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
            type="submit"
            data-testid="rule-save"
            form="rule-builder-form"
            disabled={isPending}
            className="inline-flex items-center rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isPending ? 'Enregistrement…' : 'Enregistrer la règle'}
          </button>
        </>
      }
    >
      <form
        id="rule-builder-form"
        data-testid="rule-form"
        onSubmit={onSubmit}
        className="space-y-5"
        noValidate
      >
        <div>
          <label
            htmlFor="rule-name"
            className="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            Nom de la règle
          </label>
          <input
            id="rule-name"
            data-testid="rule-name-input"
            type="text"
            {...form.register('name')}
            aria-invalid={nameError ? 'true' : 'false'}
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          />
          {nameError && (
            <p className="mt-1 text-xs text-rose-600" role="alert">
              {nameError}
            </p>
          )}
        </div>

        <ConditionsSection
          control={form.control}
          conditions={conditions}
          onTypeChange={updateConditionType}
          onRemove={removeCondition}
          onAdd={addCondition}
        />

        {conditions.length > 1 && (
          <LogicToggle
            logic={logic}
            onChange={(next) =>
              form.setValue('logic', next, { shouldValidate: false })
            }
          />
        )}

        <ChannelsPicker
          channels={channels ?? []}
          onToggle={toggleChannel}
          error={channelsError}
        />

        <label
          htmlFor="rule-pause-suggestion"
          className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200"
        >
          <input
            id="rule-pause-suggestion"
            type="checkbox"
            checked={pauseSuggestion}
            onChange={(e) =>
              form.setValue('action.pauseSuggestion', e.target.checked, {
                shouldValidate: false,
              })
            }
            className="h-4 w-4 rounded border-slate-300 text-emerald-500 focus:ring-emerald-500"
          />
          Suggérer pause paris à l&apos;utilisateur
        </label>

        <EnabledSwitch
          enabled={enabled}
          onChange={(next) =>
            form.setValue('enabled', next, { shouldValidate: false })
          }
        />

        {apiError && (
          <div
            role="alert"
            className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300"
          >
            {apiError}
          </div>
        )}
      </form>
    </Modal>
  );
}

export default RuleBuilderModal;
