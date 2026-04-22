import type { MatchHeader } from '../../../types/v2/match-detail';
import { FormBadge } from './FormBadge';

export interface MatchHeroCompactProps {
  header: MatchHeader;
  'data-testid'?: string;
}

function formatKickoffCompact(iso: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Paris',
  }).format(d);
}

export function MatchHeroCompact({
  header,
  'data-testid': dataTestId = 'match-hero-compact',
}: MatchHeroCompactProps) {
  const { home, away, kickoff_utc, league_name } = header;
  return (
    <header
      data-testid={dataTestId}
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-wide text-slate-500">
          {league_name}
        </span>
        <span className="text-xs font-medium text-slate-600">
          {formatKickoffCompact(kickoff_utc)}
        </span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <img
            src={home.logo_url}
            alt={`${home.name} logo`}
            width={40}
            height={40}
            className="h-10 w-10 shrink-0 object-contain"
          />
          <div className="flex flex-col gap-1">
            <div className="text-sm font-semibold text-slate-900">
              {home.name}
            </div>
            <FormBadge form={home.form} size="sm" />
          </div>
        </div>
        <div className="text-sm font-bold text-slate-500" aria-hidden="true">
          VS
        </div>
        <div className="flex items-center gap-2">
          <div className="flex flex-col items-end gap-1 text-right">
            <div className="text-sm font-semibold text-slate-900">
              {away.name}
            </div>
            <FormBadge form={away.form} size="sm" />
          </div>
          <img
            src={away.logo_url}
            alt={`${away.name} logo`}
            width={40}
            height={40}
            className="h-10 w-10 shrink-0 object-contain"
          />
        </div>
      </div>
    </header>
  );
}

export default MatchHeroCompact;
