import type { Sport } from '@/types/v2/matches';

export type SportChipsValue = 'all' | Sport;

interface Counts {
  all: number;
  football: number;
  nhl: number;
}

interface Props {
  value: SportChipsValue;
  onChange: (v: SportChipsValue) => void;
  counts?: Counts;
  'data-testid'?: string;
}

const OPTIONS: { key: SportChipsValue; label: string }[] = [
  { key: 'all', label: 'Tous' },
  { key: 'football', label: 'Football' },
  { key: 'nhl', label: 'NHL' },
];

export function SportChips({
  value,
  onChange,
  counts,
  'data-testid': dataTestId = 'sport-chips',
}: Props) {
  return (
    <div
      data-testid={dataTestId}
      role="group"
      aria-label="Filtre par sport"
      className="flex flex-wrap gap-2"
    >
      {OPTIONS.map((opt) => {
        const selected = value === opt.key;
        const count = counts ? counts[opt.key] : undefined;
        return (
          <button
            key={opt.key}
            type="button"
            onClick={() => onChange(opt.key)}
            aria-pressed={selected}
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2"
            style={{
              border: '1px solid var(--border)',
              background: selected ? 'var(--primary)' : 'var(--surface)',
              color: selected ? '#ffffff' : 'var(--text)',
            }}
          >
            <span>{opt.label}</span>
            {count !== undefined && (
              <span
                className="tabular-nums"
                style={{
                  fontVariantNumeric: 'tabular-nums',
                  opacity: 0.8,
                }}
              >
                ({count})
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default SportChips;
