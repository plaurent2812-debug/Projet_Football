import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Star, Zap } from 'lucide-react';
import { ProbBar } from '@/components/v2/system/ProbBar';
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

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Paris',
  });
}

function DesktopRow({ match }: { match: MatchRowData }) {
  const { home, away, prob1x2, signals, topValueBet } = match;
  return (
    <div
      data-testid="match-row-desktop"
      className="grid grid-cols-[60px_1fr_200px_110px_140px_60px] items-center gap-3 px-4 py-2.5 text-sm"
      style={{ borderTop: '1px solid var(--border)' }}
    >
      <time
        className="tabular-nums text-xs"
        style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
      >
        {fmtTime(match.kickoffUtc)}
      </time>
      <div className="flex items-center gap-2 font-medium">
        <span className="truncate">{home.short}</span>
        <span style={{ color: 'var(--text-faint)' }}>vs</span>
        <span className="truncate">{away.short}</span>
      </div>
      <div>
        <ProbBar
          home={prob1x2.home}
          draw={prob1x2.draw}
          away={prob1x2.away}
          homeLabel={home.short}
          awayLabel={away.short}
        />
        <div
          className="mt-1 flex justify-between text-[11px] tabular-nums"
          style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
        >
          <span>{Math.round(prob1x2.home * 100)}%</span>
          <span>{Math.round(prob1x2.draw * 100)}%</span>
          <span>{Math.round(prob1x2.away * 100)}%</span>
        </div>
      </div>
      <div className="flex flex-wrap gap-1">
        {signals.includes('safe') && (
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
            style={{ background: 'rgba(16,185,129,0.12)', color: 'var(--primary)' }}
          >
            <Star aria-hidden="true" size={10} />
            SAFE
          </span>
        )}
        {topValueBet && (
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
            style={{ background: 'rgba(245,158,11,0.12)', color: 'var(--warning, #b45309)' }}
          >
            <Zap aria-hidden="true" size={10} />+{topValueBet.edgePct.toFixed(1)}%
          </span>
        )}
      </div>
      <div className="flex flex-col items-end text-xs tabular-nums" style={{ fontVariantNumeric: 'tabular-nums' }}>
        {topValueBet ? (
          <>
            <span className="font-semibold">{topValueBet.bestOdd.toFixed(2)}</span>
            <span style={{ color: 'var(--text-muted)' }}>{topValueBet.bestBook}</span>
          </>
        ) : (
          <span style={{ color: 'var(--text-faint)' }}>—</span>
        )}
      </div>
      <div className="flex justify-end">
        <Link
          to={`/matchs/${match.fixtureId}`}
          aria-label={`Voir le détail ${home.short} vs ${away.short}`}
          className="inline-flex h-7 w-7 items-center justify-center rounded-full focus-visible:outline focus-visible:outline-2"
          style={{ border: '1px solid var(--border)', color: 'var(--text)' }}
        >
          <ChevronRight aria-hidden="true" size={14} />
        </Link>
      </div>
    </div>
  );
}

export function MatchesTableDesktop({
  matches,
  'data-testid': dataTestId = 'matches-table-desktop',
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
          <div role="list">
            {items.map((m) => (
              <div role="listitem" key={m.fixtureId}>
                <DesktopRow match={m} />
              </div>
            ))}
          </div>
        </LeagueGroup>
      ))}
    </div>
  );
}

export default MatchesTableDesktop;
