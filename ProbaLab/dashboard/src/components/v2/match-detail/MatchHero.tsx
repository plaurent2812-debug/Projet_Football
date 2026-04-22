import { MapPin, UserCheck } from 'lucide-react';
import type {
  MatchHeader,
  MatchHeaderTeam,
} from '../../../types/v2/match-detail';
import { FormBadge } from './FormBadge';

export interface MatchHeroProps {
  header: MatchHeader;
  'data-testid'?: string;
}

function formatKickoff(iso: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'full',
    timeStyle: 'short',
    timeZone: 'Europe/Paris',
  }).format(d);
}

interface TeamBlockProps {
  team: MatchHeaderTeam;
  align: 'left' | 'right';
}

function TeamBlock({ team, align }: TeamBlockProps) {
  const flexClass =
    align === 'right'
      ? 'flex-row-reverse text-right'
      : 'flex-row text-left';
  const textAlign = align === 'right' ? 'text-right' : 'text-left';
  const formAlign = align === 'right' ? 'justify-end' : 'justify-start';

  return (
    <div className={`flex flex-1 items-center gap-4 ${flexClass}`}>
      <img
        src={team.logo_url}
        alt={`${team.name} logo`}
        width={64}
        height={64}
        className="h-16 w-16 shrink-0 object-contain"
      />
      <div className={`flex flex-col gap-1 ${textAlign}`}>
        <div className="text-lg font-semibold text-slate-900">{team.name}</div>
        {team.rank != null && (
          <div className="text-xs text-slate-500">#{team.rank}</div>
        )}
        <div className={`mt-1 flex ${formAlign}`}>
          <FormBadge form={team.form} />
        </div>
      </div>
    </div>
  );
}

export function MatchHero({
  header,
  'data-testid': dataTestId = 'match-hero',
}: MatchHeroProps) {
  const { home, away, kickoff_utc, stadium, referee, league_name } = header;
  return (
    <header
      data-testid={dataTestId}
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="text-xs uppercase tracking-wide text-slate-500">
        {league_name}
      </div>
      <div className="mt-4 flex items-center justify-between gap-6">
        <TeamBlock team={home} align="right" />
        <div className="flex min-w-[160px] flex-col items-center gap-1 text-center">
          <div className="text-sm font-medium text-slate-700">
            {formatKickoff(kickoff_utc)}
          </div>
          {stadium && (
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <MapPin className="h-3 w-3" aria-hidden="true" />
              <span>{stadium}</span>
            </div>
          )}
          {referee && (
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <UserCheck className="h-3 w-3" aria-hidden="true" />
              <span>{referee}</span>
            </div>
          )}
          <div className="mt-2 text-2xl font-bold text-slate-900">VS</div>
        </div>
        <TeamBlock team={away} align="left" />
      </div>
    </header>
  );
}

export default MatchHero;
