import type { ComparativeStat } from '../../../types/v2/match-detail';

export interface StatsComparativeProps {
  stats: ComparativeStat[];
  /**
   * Titre de la section. Absent = pas de heading rendu.
   */
  label?: string;
  'data-testid'?: string;
}

function format(value: number, unit?: string): string {
  return `${value}${unit ?? ''}`;
}

export function StatsComparative({
  stats,
  label,
  'data-testid': dataTestId = 'stats-comparative',
}: StatsComparativeProps) {
  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      {label && (
        <h3 className="mb-3 text-sm font-semibold text-slate-900">{label}</h3>
      )}
      <ul className="space-y-3">
        {stats.map((s) => {
          const total = s.home_value + s.away_value;
          const homePct = total > 0 ? (s.home_value / total) * 100 : 50;
          const homeBest = s.home_value >= s.away_value;
          return (
            <li
              key={s.label}
              data-testid="stat-row"
              aria-label={`${s.label} : domicile ${format(
                s.home_value,
                s.unit,
              )}, extérieur ${format(s.away_value, s.unit)}`}
              className="flex items-center gap-3 text-xs"
            >
              <span
                className={`w-10 text-right font-semibold tabular-nums ${
                  homeBest ? 'text-emerald-600' : 'text-slate-600'
                }`}
              >
                {format(s.home_value, s.unit)}
              </span>
              <div className="flex h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={homeBest ? 'bg-emerald-500' : 'bg-slate-400'}
                  style={{ width: `${homePct}%` }}
                />
                <div
                  className={!homeBest ? 'bg-emerald-500' : 'bg-slate-400'}
                  style={{ width: `${100 - homePct}%` }}
                />
              </div>
              <span
                className={`w-10 text-left font-semibold tabular-nums ${
                  !homeBest ? 'text-emerald-600' : 'text-slate-600'
                }`}
              >
                {format(s.away_value, s.unit)}
              </span>
              <span className="ml-2 min-w-[120px] text-slate-500">
                {s.label}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default StatsComparative;
