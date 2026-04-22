import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';
import type { SafePick } from '@/types/v2/matches';

interface Props {
  data: SafePick | null;
  'data-testid'?: string;
}

export function SafeOfTheDayCard({ data, 'data-testid': dataTestId = 'safe-of-the-day-card' }: Props) {
  if (!data) {
    return (
      <section
        data-testid={dataTestId}
        className="rounded-xl border border-border bg-surface p-6 text-center"
        style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
      >
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Pas de pronostic Safe aujourd'hui — privilégiez l'analyse des matchs du soir.
        </p>
      </section>
    );
  }
  const pct = Math.round(data.probability * 100);
  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl p-6 shadow-sm"
      style={{
        borderLeft: '3px solid var(--primary)',
        background:
          'linear-gradient(135deg, rgba(16,185,129,0.12) 0%, var(--surface) 70%)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <span
          className="inline-flex items-center gap-1 text-xs font-medium tracking-wide"
          style={{ color: 'var(--primary)' }}
        >
          <Star aria-hidden="true" size={14} />
          SAFE · PRONOSTIC DU JOUR
        </span>
        <span
          className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
          style={{
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
          }}
        >
          FREE
        </span>
      </div>
      <h3 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>
        {data.betLabel}
      </h3>
      <div className="mt-3 flex items-baseline gap-4">
        <span
          className="font-bold tabular-nums"
          style={{ fontSize: 32, color: 'var(--primary)', fontVariantNumeric: 'tabular-nums' }}
        >
          {data.odd.toFixed(2)}
        </span>
        <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Probabilité {pct}%
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Probabilité ${data.betLabel} ${pct}%`}
        className="mt-2 h-1 w-full rounded-full overflow-hidden"
        style={{ background: 'var(--surface-2)' }}
      >
        <div
          className="h-full"
          style={{ width: `${pct}%`, background: 'var(--primary)' }}
        />
      </div>
      <p className="mt-4 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        {data.justification}
      </p>
      <Link
        to={`/matchs/${data.fixtureId}`}
        className="mt-4 inline-block text-sm font-medium focus-visible:outline focus-visible:outline-2"
        style={{ color: 'var(--primary)' }}
      >
        Voir le match →
      </Link>
    </section>
  );
}

export default SafeOfTheDayCard;
