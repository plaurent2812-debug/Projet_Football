import type {
  ConditionType,
  RuleCondition,
} from '@/lib/v2/schemas/rules';

/**
 * Leagues supported by the rules builder. Labels match the ones displayed
 * throughout the dashboard so filters roundtrip cleanly to the backend
 * `league_in` predicate.
 */
export const LEAGUE_OPTIONS: readonly {
  value: string;
  label: string;
}[] = [
  { value: 'L1', label: 'L1' },
  { value: 'L2', label: 'L2' },
  { value: 'PL', label: 'PL' },
  { value: 'LaLiga', label: 'LaLiga' },
  { value: 'SerieA', label: 'SerieA' },
  { value: 'Bundesliga', label: 'Bundesliga' },
  { value: 'UCL', label: 'UCL' },
  { value: 'UEL', label: 'UEL' },
];

interface Props {
  index: number;
  condition: RuleCondition;
  onChange: (next: RuleCondition) => void;
}

/**
 * Renders the value editor for a single rule condition. The shape of
 * the control depends on the `type` of the condition — see schema in
 * `rules.ts`. The wrapper takes care of always emitting a fully valid
 * discriminated union, so the parent can feed the result straight into
 * react-hook-form.
 */
export function ConditionValueField({ index, condition, onChange }: Props) {
  const id = `rule-cond-val-${index}`;
  const label = `Valeur condition ${index + 1}`;
  const type: ConditionType = condition.type;

  if (type === 'edge_min') {
    return (
      <div className="flex items-center gap-2">
        <label htmlFor={id} className="sr-only">
          {label}
        </label>
        <input
          id={id}
          data-testid="rule-edge-input"
          type="number"
          min={0}
          max={100}
          step={0.1}
          value={Number.isFinite(condition.value) ? condition.value : 0}
          onChange={(e) =>
            onChange({ type: 'edge_min', value: Number(e.target.value) })
          }
          className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
        />
        <span
          className="text-xs text-slate-500 dark:text-slate-400"
          aria-hidden="true"
        >
          %
        </span>
      </div>
    );
  }

  if (type === 'league_in') {
    const selected = condition.type === 'league_in' ? condition.value : [];
    return (
      <div>
        <span className="sr-only" id={`${id}-label`}>
          {label}
        </span>
        <div
          role="group"
          aria-labelledby={`${id}-label`}
          className="flex flex-wrap gap-2"
        >
          {LEAGUE_OPTIONS.map((opt) => {
            const cbId = `${id}-${opt.value}`;
            const isChecked = selected.includes(opt.value);
            return (
              <label
                key={opt.value}
                htmlFor={cbId}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
              >
                <input
                  id={cbId}
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => {
                    const next = isChecked
                      ? selected.filter((v) => v !== opt.value)
                      : [...selected, opt.value];
                    onChange({
                      type: 'league_in',
                      value: next.length > 0 ? next : [opt.value],
                    });
                  }}
                  className="h-3.5 w-3.5 rounded border-slate-300 text-emerald-500 focus:ring-emerald-500"
                />
                {opt.label}
              </label>
            );
          })}
        </div>
      </div>
    );
  }

  if (type === 'sport') {
    const selected = condition.type === 'sport' ? condition.value : 'football';
    return (
      <div
        role="radiogroup"
        aria-label={label}
        className="flex items-center gap-3 text-sm text-slate-700 dark:text-slate-200"
      >
        {(['football', 'nhl'] as const).map((s) => {
          const rid = `${id}-${s}`;
          return (
            <label
              key={s}
              htmlFor={rid}
              className="inline-flex items-center gap-1.5"
            >
              <input
                id={rid}
                type="radio"
                name={id}
                checked={selected === s}
                onChange={() => onChange({ type: 'sport', value: s })}
                className="h-3.5 w-3.5 border-slate-300 text-emerald-500 focus:ring-emerald-500"
              />
              {s === 'football' ? 'Football' : 'NHL'}
            </label>
          );
        })}
      </div>
    );
  }

  if (type === 'confidence') {
    const selected = condition.type === 'confidence' ? condition.value : 'HIGH';
    return (
      <div>
        <label htmlFor={id} className="sr-only">
          {label}
        </label>
        <select
          id={id}
          value={selected}
          onChange={(e) =>
            onChange({
              type: 'confidence',
              value: e.target.value as 'LOW' | 'MED' | 'HIGH',
            })
          }
          className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
        >
          <option value="HIGH">Élevée</option>
          <option value="MED">Moyenne</option>
          <option value="LOW">Faible</option>
        </select>
      </div>
    );
  }

  if (type === 'kickoff_within') {
    return (
      <div className="flex items-center gap-2">
        <label htmlFor={id} className="sr-only">
          {label}
        </label>
        <input
          id={id}
          type="number"
          min={1}
          max={168}
          step={1}
          value={Number.isFinite(condition.value) ? condition.value : 1}
          onChange={(e) =>
            onChange({
              type: 'kickoff_within',
              value: Math.round(Number(e.target.value)),
            })
          }
          className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
        />
        <span
          className="text-xs text-slate-500 dark:text-slate-400"
          aria-hidden="true"
        >
          heures
        </span>
      </div>
    );
  }

  // bankroll_drawdown
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <input
        id={id}
        type="number"
        min={0}
        max={100}
        step={0.5}
        value={Number.isFinite(condition.value) ? condition.value : 0}
        onChange={(e) =>
          onChange({
            type: 'bankroll_drawdown',
            value: Number(e.target.value),
          })
        }
        className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
      />
      <span
        className="text-xs text-slate-500 dark:text-slate-400"
        aria-hidden="true"
      >
        %
      </span>
    </div>
  );
}
