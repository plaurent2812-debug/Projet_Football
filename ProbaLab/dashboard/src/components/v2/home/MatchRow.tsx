import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';
import { ProbBar } from '@/components/v2/system/ProbBar';
import { ValueBadge } from '@/components/v2/system/ValueBadge';
import type { MatchRowData } from '@/types/v2/matches';

interface Props {
  match: MatchRowData;
  onClick?: () => void;
  variant?: 'mobile' | 'desktop';
  'data-testid'?: string;
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

export function MatchRow({
  match,
  onClick,
  variant = 'mobile',
  'data-testid': dataTestId = 'match-row',
}: Props) {
  const { prob1x2, home, away, signals, topValueBet } = match;
  const hasProbabilities =
    isFiniteProbability(prob1x2.home) ||
    isFiniteProbability(prob1x2.draw) ||
    isFiniteProbability(prob1x2.away);
  const hasScore = match.score?.home != null && match.score.away != null;

  return (
    <Link
      to={`/matchs/${match.fixtureId}`}
      onClick={onClick}
      data-testid={dataTestId}
      data-variant={variant}
      className="flex items-center gap-3 rounded-lg px-3 py-3 transition-colors focus-visible:outline focus-visible:outline-2 md:gap-4 md:px-4"
      style={{ color: 'var(--text)', textDecoration: 'none' }}
    >
      <time
        className="w-12 shrink-0 text-xs tabular-nums"
        style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
      >
        {fmtTime(match.kickoffUtc)}
      </time>
      <div className="min-w-0 flex-1">
        <div
          className="flex items-center justify-between gap-2 text-sm font-medium"
          style={{ color: 'var(--text)' }}
        >
          <span className="truncate">{home.short}</span>
          <span style={{ color: 'var(--text-faint)' }}>vs</span>
          <span className="truncate text-right">{away.short}</span>
        </div>
        {hasScore && (
          <div className="mt-1 flex items-center justify-center gap-2 text-xs font-bold tabular-nums">
            <span style={{ color: 'var(--primary)' }}>{match.status ?? 'Score'}</span>
            <span>{match.score?.home} - {match.score?.away}</span>
          </div>
        )}
        <div className="mt-2">
          <ProbBar
            home={prob1x2.home}
            draw={prob1x2.draw}
            away={prob1x2.away}
            homeLabel={home.short}
            awayLabel={away.short}
          />
        </div>
        <div
          className="mt-1 flex justify-between text-[11px] tabular-nums"
          style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
        >
          {hasProbabilities ? (
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
      <div className="flex shrink-0 flex-col items-end gap-1">
        {signals.includes('safe') && (
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
            style={{
              background: 'rgba(16,185,129,0.12)',
              color: 'var(--primary)',
            }}
          >
            <Star aria-hidden="true" size={10} />
            Prono recommandé
          </span>
        )}
        {topValueBet && <ValueBadge edge={topValueBet.edgePct / 100} />}
      </div>
    </Link>
  );
}

export default MatchRow;
