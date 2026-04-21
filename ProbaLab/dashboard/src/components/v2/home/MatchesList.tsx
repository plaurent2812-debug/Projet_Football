import { useEffect, useMemo } from 'react';
import { MatchRow } from './MatchRow';
import type { LeagueRef, MatchRowData } from '@/types/v2/matches';

interface Props {
  matches: MatchRowData[];
  emptyMessage?: string;
  'data-testid'?: string;
}

interface Group {
  league: LeagueRef;
  items: MatchRowData[];
}

export function MatchesList({
  matches,
  emptyMessage = 'Aucun match programmé.',
  'data-testid': dataTestId = 'matches-list',
}: Props) {
  useEffect(() => {
    if (matches.length > 50) {
      // Non-bloquant : signale que la liste devrait basculer vers react-window.

      console.warn(
        `[MatchesList] ${matches.length} rows rendered without virtualization — consider react-window`,
      );
    }
  }, [matches.length]);

  const grouped = useMemo<Group[]>(() => {
    const map = new Map<string, Group>();
    for (const m of matches) {
      const g = map.get(m.league.id) ?? { league: m.league, items: [] };
      g.items.push(m);
      map.set(m.league.id, g);
    }
    return Array.from(map.values());
  }, [matches]);

  if (matches.length === 0) {
    return (
      <p
        data-testid={dataTestId}
        className="rounded-lg p-6 text-center text-sm"
        style={{
          border: '1px solid var(--border)',
          background: 'var(--surface)',
          color: 'var(--text-muted)',
        }}
      >
        {emptyMessage}
      </p>
    );
  }

  return (
    <div data-testid={dataTestId} className="space-y-4">
      {grouped.map(({ league, items }) => (
        <section
          key={league.id}
          className="rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
        >
          <h3
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wide"
            style={{ backgroundColor: league.color, color: '#ffffff' }}
          >
            {league.name}
            <span className="ml-auto text-[11px]" style={{ opacity: 0.8 }}>
              {items.length}
            </span>
          </h3>
          <ul className="divide-y" style={{ borderColor: 'var(--border)' }}>
            {items.map((m) => (
              <li key={m.fixtureId} style={{ borderTop: '1px solid var(--border)' }}>
                <MatchRow match={m} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export default MatchesList;
