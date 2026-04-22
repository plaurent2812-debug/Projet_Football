import { Link } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { LockOverlay } from '@/components/v2/system/LockOverlay';
import type { MatchRowData } from '@/types/v2/matches';

export type ValueBetsGating = 'free' | 'trial' | 'premium';

interface Props {
  matches: MatchRowData[];
  gating?: ValueBetsGating;
  'data-testid'?: string;
}

export function ValueBetsTeaser({
  matches,
  gating = 'premium',
  'data-testid': dataTestId = 'value-bets-teaser',
}: Props) {
  const items = matches.filter((m) => m.topValueBet).slice(0, 2);
  if (items.length === 0) return null;

  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl p-4"
      style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
    >
      <h3
        className="mb-3 flex items-center gap-2 text-sm font-semibold"
        style={{ color: 'var(--text)' }}
      >
        <Zap size={14} aria-hidden="true" style={{ color: 'var(--value, #f59e0b)' }} />
        Value bets du jour
      </h3>
      <ul className="space-y-2">
        {items.map((m, idx) => {
          const vb = m.topValueBet!;
          const locked = gating === 'free' && idx > 0;
          const content = (
            <Link
              to={`/matchs/${m.fixtureId}`}
              className="flex items-center justify-between gap-2 text-sm focus-visible:outline focus-visible:outline-2"
              style={{ color: 'var(--text)' }}
            >
              <span className="truncate">
                {m.home.short} vs {m.away.short} · {vb.market}
              </span>
              <span
                className="shrink-0 tabular-nums text-xs font-semibold"
                style={{ color: 'var(--value, #f59e0b)', fontVariantNumeric: 'tabular-nums' }}
              >
                +{vb.edgePct.toFixed(1)}% · Kelly {vb.kellyPct.toFixed(1)}%
              </span>
            </Link>
          );
          if (locked) {
            return (
              <li key={m.fixtureId} data-testid="value-bet-locked">
                <LockOverlay message="Premium requis">{content}</LockOverlay>
              </li>
            );
          }
          return <li key={m.fixtureId}>{content}</li>;
        })}
      </ul>
      <p className="mt-3 text-[11px]" style={{ color: 'var(--text-muted)' }}>
        {items[0]!.topValueBet!.bestBook} offre la meilleure cote.
      </p>
    </section>
  );
}

export default ValueBetsTeaser;
