import { Controller } from 'react-hook-form';
import type { Control } from 'react-hook-form';
import { X } from 'lucide-react';
import type {
  ConditionType,
  RuleChannel,
  RuleCondition,
} from '@/lib/v2/schemas/rules';
import type { CreateRuleInput } from '@/hooks/v2/useNotificationRules';
import { ConditionValueField } from './conditionFields';

const CONDITION_TYPE_OPTIONS: readonly {
  value: ConditionType;
  label: string;
}[] = [
  { value: 'edge_min', label: 'Edge minimum' },
  { value: 'league_in', label: 'Ligues' },
  { value: 'sport', label: 'Sport' },
  { value: 'confidence', label: 'Confiance' },
  { value: 'kickoff_within', label: "Coup d'envoi dans (heures)" },
  { value: 'bankroll_drawdown', label: 'Drawdown bankroll' },
];

export interface ConditionsSectionProps {
  control: Control<CreateRuleInput>;
  conditions: readonly RuleCondition[];
  onTypeChange: (index: number, type: ConditionType) => void;
  onRemove: (index: number) => void;
  onAdd: () => void;
}

export function ConditionsSection({
  control,
  conditions,
  onTypeChange,
  onRemove,
  onAdd,
}: ConditionsSectionProps) {
  return (
    <fieldset className="border-none p-0">
      <legend className="text-sm font-semibold text-slate-700 dark:text-slate-200">
        Quand…
      </legend>
      <div className="mt-2 space-y-3">
        {conditions.map((c, i) => (
          <div
            key={i}
            data-testid="rule-condition-row"
            className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:items-start dark:border-slate-800 dark:bg-slate-900/40"
          >
            <div className="flex-1 space-y-2">
              <label
                htmlFor={`rule-cond-type-${i}`}
                className="block text-xs font-medium text-slate-500 dark:text-slate-400"
              >
                {`Type condition ${i + 1}`}
              </label>
              <select
                id={`rule-cond-type-${i}`}
                value={c.type}
                onChange={(e) =>
                  onTypeChange(i, e.target.value as ConditionType)
                }
                className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
              >
                {CONDITION_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              <Controller
                control={control}
                name={`conditions.${i}`}
                render={({ field }) => (
                  <ConditionValueField
                    index={i}
                    condition={field.value}
                    onChange={field.onChange}
                  />
                )}
              />
            </div>
            {conditions.length > 1 && (
              <button
                type="button"
                aria-label={`Supprimer condition ${i + 1}`}
                onClick={() => onRemove(i)}
                className="mt-6 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-400 hover:bg-rose-50 hover:text-rose-600 focus-visible:outline focus-visible:outline-2 dark:hover:bg-rose-950"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={onAdd}
        disabled={conditions.length >= 3}
        className="mt-3 inline-flex items-center gap-1 rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:border-emerald-500 hover:text-emerald-600 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-400"
      >
        + Ajouter une condition
      </button>
    </fieldset>
  );
}

export interface LogicToggleProps {
  logic: 'AND' | 'OR';
  onChange: (next: 'AND' | 'OR') => void;
}

export function LogicToggle({ logic, onChange }: LogicToggleProps) {
  return (
    <fieldset className="border-none p-0">
      <legend className="text-sm font-semibold text-slate-700 dark:text-slate-200">
        Relier avec…
      </legend>
      <div
        className="mt-2 inline-flex overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700"
        role="group"
        aria-label="Relier les conditions"
      >
        {(['AND', 'OR'] as const).map((l) => {
          const isActive = logic === l;
          return (
            <button
              key={l}
              type="button"
              aria-pressed={isActive}
              onClick={() => onChange(l)}
              className={
                isActive
                  ? 'bg-emerald-500 px-4 py-1.5 text-xs font-medium text-white'
                  : 'bg-white px-4 py-1.5 text-xs font-medium text-slate-600 dark:bg-slate-900 dark:text-slate-300'
              }
            >
              {l}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export interface ChannelsPickerProps {
  channels: readonly RuleChannel[];
  onToggle: (c: RuleChannel) => void;
  error?: string;
}

const CHANNEL_OPTIONS: readonly { value: RuleChannel; label: string }[] = [
  { value: 'telegram', label: 'Telegram' },
  { value: 'email', label: 'Email' },
  { value: 'push', label: 'Push' },
];

export function ChannelsPicker({
  channels,
  onToggle,
  error,
}: ChannelsPickerProps) {
  return (
    <fieldset className="border-none p-0">
      <legend className="text-sm font-semibold text-slate-700 dark:text-slate-200">
        Notifier sur…
      </legend>
      <div className="mt-2 flex flex-wrap gap-3">
        {CHANNEL_OPTIONS.map((opt) => {
          const id = `rule-channel-${opt.value}`;
          const isChecked = channels.includes(opt.value);
          return (
            <label
              key={opt.value}
              htmlFor={id}
              className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200"
            >
              <input
                id={id}
                data-testid={`rule-channel-${opt.value}`}
                type="checkbox"
                checked={isChecked}
                onChange={() => onToggle(opt.value)}
                className="h-4 w-4 rounded border-slate-300 text-emerald-500 focus:ring-emerald-500"
              />
              {opt.label}
            </label>
          );
        })}
      </div>
      {error && (
        <p className="mt-1 text-xs text-rose-600" role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}

export interface EnabledSwitchProps {
  enabled: boolean;
  onChange: (next: boolean) => void;
}

export function EnabledSwitch({ enabled, onChange }: EnabledSwitchProps) {
  return (
    <div className="flex items-center justify-between gap-3">
      <label
        htmlFor="rule-enabled"
        className="text-sm text-slate-700 dark:text-slate-200"
      >
        Activer la règle
      </label>
      <button
        id="rule-enabled"
        type="button"
        role="switch"
        aria-checked={enabled}
        aria-label="Activer la règle"
        onClick={() => onChange(!enabled)}
        className={
          enabled
            ? 'relative inline-flex h-5 w-9 items-center rounded-full bg-emerald-500 transition'
            : 'relative inline-flex h-5 w-9 items-center rounded-full bg-slate-300 transition dark:bg-slate-700'
        }
      >
        <span
          className={
            enabled
              ? 'block h-4 w-4 translate-x-4 rounded-full bg-white transition-transform'
              : 'block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform'
          }
        />
      </button>
    </div>
  );
}
