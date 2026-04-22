import { useMemo } from 'react';
import { MatchRow } from '@/components/v2/home/MatchRow';
import { LeagueGroup } from './LeagueGroup';
import type { LeagueRef, MatchRowData } from '@/types/v2/matches';

interface Props {
  matches: MatchRowData[];
  'data-testid'?: string;
}

interface Group {
  league: LeagueRef;
  items: MatchRowData[];
}

export function MatchesListMobile({
  matches,
  'data-testid': dataTestId = 'matches-list-mobile',
}: Props) {
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
        Aucun match pour cette sélection.
      </p>
    );
  }

  return (
    <div data-testid={dataTestId} className="space-y-4">
      {grouped.map(({ league, items }) => (
        <LeagueGroup key={league.id} league={league} count={items.length}>
          <ul className="divide-y" style={{ borderColor: 'var(--border)' }}>
            {items.map((m) => (
              <li key={m.fixtureId} style={{ borderTop: '1px solid var(--border)' }}>
                <MatchRow match={m} />
              </li>
            ))}
          </ul>
        </LeagueGroup>
      ))}
    </div>
  );
}

export default MatchesListMobile;
