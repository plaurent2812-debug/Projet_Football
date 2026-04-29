import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Clock3, Star, Zap } from 'lucide-react';
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

function isFiniteProbability(value: number | null | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function formatPct(value: number | null | undefined): string {
  return isFiniteProbability(value) ? `${Math.round(value * 100)}%` : '—';
}

function hasAnyProbability(match: MatchRowData): boolean {
  return (
    isFiniteProbability(match.prob1x2.home) ||
    isFiniteProbability(match.prob1x2.draw) ||
    isFiniteProbability(match.prob1x2.away)
  );
}

function hasScore(match: MatchRowData): boolean {
  return match.score?.home != null && match.score.away != null;
}

function mainScenario(match: MatchRowData): string {
  const entries = [
    { label: match.home.short, value: match.prob1x2.home },
    { label: 'Nul', value: match.prob1x2.draw },
    { label: match.away.short, value: match.prob1x2.away },
  ]
    .filter((entry): entry is { label: string; value: number } =>
      isFiniteProbability(entry.value),
    )
    .sort((a, b) => b.value - a.value);
  const [first, second] = entries;

  if (!first) {
    return 'Analyse bientôt disponible.';
  }
  if (!second) {
    return `${first.label} à suivre (${Math.round(first.value * 100)}%).`;
  }
  return `${first.label} en tête (${Math.round(first.value * 100)}%), ${second.label.toLowerCase()} à surveiller.`;
}

function DesktopRow({ match }: { match: MatchRowData }) {
  const { home, away, prob1x2, signals, topValueBet } = match;
  const probabilitiesAvailable = hasAnyProbability(match);
  return (
    <div
      data-testid="match-row"
      className="grid gap-4 p-4 text-sm lg:grid-cols-[minmax(230px,0.9fr)_minmax(260px,1fr)_minmax(230px,0.8fr)_auto] lg:items-center"
      style={{ borderTop: '1px solid var(--border)', background: 'rgba(255,255,255,0.018)' }}
    >
      <div>
        <time
          className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold tabular-nums"
          style={{
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          <Clock3 aria-hidden="true" size={13} />
          {fmtTime(match.kickoffUtc)}
        </time>
        <div className="mt-3 flex items-center gap-2 font-black tracking-[-0.04em]" style={{ color: 'var(--text)' }}>
          <span className="truncate text-xl">{home.short}</span>
          <span className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: 'var(--text-faint)' }}>vs</span>
          <span className="truncate text-xl">{away.short}</span>
        </div>
        {hasScore(match) && (
          <div className="mt-2 flex items-center gap-2">
            <span
              className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-[0.12em]"
              style={{ background: 'rgba(16,185,129,0.12)', color: 'var(--primary)' }}
            >
              {match.status ?? 'Score'}
            </span>
            <span className="flex items-center gap-1 text-lg font-black tabular-nums" style={{ color: 'var(--text)' }}>
              <span>{match.score?.home}</span>
              <span style={{ color: 'var(--text-faint)' }}>-</span>
              <span>{match.score?.away}</span>
            </span>
          </div>
        )}
        <div className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
          {home.name} - {away.name}
        </div>
      </div>

      <div>
        <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.14em]" style={{ color: 'var(--text-muted)' }}>
          Probabilités
        </div>
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
          {probabilitiesAvailable ? (
            <>
              <span>{formatPct(prob1x2.home)}</span>
              {isFiniteProbability(prob1x2.draw) && <span>{formatPct(prob1x2.draw)}</span>}
              <span>{formatPct(prob1x2.away)}</span>
            </>
          ) : (
            <span>Analyse bientôt disponible</span>
          )}
        </div>
      </div>

      <div className="rounded-2xl p-3" style={{ border: '1px solid var(--border)', background: 'rgba(255,255,255,0.035)' }}>
        <div className="text-[11px] font-bold uppercase tracking-[0.14em]" style={{ color: 'var(--text-muted)' }}>
          Lecture rapide
        </div>
        <p className="mt-1 text-sm leading-5" style={{ color: 'var(--text)' }}>
          {mainScenario(match)}
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {signals.includes('safe') && (
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold"
              style={{ background: 'rgba(16,185,129,0.12)', color: 'var(--primary)' }}
            >
              <Star aria-hidden="true" size={11} />
              Prono recommandé
            </span>
          )}
          {topValueBet && (
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold"
              style={{ background: 'rgba(251,191,36,0.12)', color: 'var(--value, #fbbf24)' }}
            >
              <Zap aria-hidden="true" size={11} />
              Signal +{topValueBet.edgePct.toFixed(1)}%
            </span>
          )}
        </div>
        {topValueBet && (
          <div className="mt-3 flex items-baseline gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
            <span>Cote</span>
            <strong className="text-base tabular-nums" style={{ color: 'var(--text)' }}>{topValueBet.bestOdd.toFixed(2)}</strong>
            <span>{topValueBet.bestBook}</span>
          </div>
        )}
      </div>

      <div className="flex justify-end lg:justify-center">
        <Link
          to={`/matchs/${match.fixtureId}`}
          aria-label={`Ouvrir l'analyse, voir le détail ${home.short} vs ${away.short}`}
          className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-bold focus-visible:outline focus-visible:outline-2"
          style={{ background: 'var(--primary)', color: '#061014' }}
        >
          Ouvrir l'analyse
          <ArrowRight aria-hidden="true" size={14} />
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
