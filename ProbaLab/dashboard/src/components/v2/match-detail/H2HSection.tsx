import type { H2HSummary } from '../../../types/v2/match-detail';

export interface H2HSectionProps {
  h2h: H2HSummary;
  homeName: string;
  awayName: string;
  'data-testid'?: string;
}

function pluralize(n: number, singular: string, plural: string): string {
  return n > 1 ? plural : singular;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'Europe/Paris',
  }).format(d);
}

export function H2HSection({
  h2h,
  homeName,
  awayName,
  'data-testid': dataTestId = 'h2h-section',
}: H2HSectionProps) {
  const { home_wins, draws, away_wins, last_matches } = h2h;
  const total = home_wins + draws + away_wins;
  const homePct = total > 0 ? (home_wins / total) * 100 : 0;
  const drawPct = total > 0 ? (draws / total) * 100 : 0;
  const awayPct = total > 0 ? Math.max(0, 100 - homePct - drawPct) : 0;

  const ariaLabel = `Historique : ${homeName} ${home_wins} ${pluralize(
    home_wins,
    'victoire',
    'victoires',
  )}, ${draws} ${pluralize(draws, 'nul', 'nuls')}, ${awayName} ${away_wins} ${pluralize(
    away_wins,
    'victoire',
    'victoires',
  )}`;

  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      <h3 className="mb-3 text-sm font-semibold text-slate-900">Face à face</h3>
      <div
        role="img"
        aria-label={ariaLabel}
        className="flex h-3 overflow-hidden rounded-full bg-slate-100"
      >
        {homePct > 0 && (
          <div className="bg-emerald-500" style={{ width: `${homePct}%` }} />
        )}
        {drawPct > 0 && (
          <div className="bg-slate-400" style={{ width: `${drawPct}%` }} />
        )}
        {awayPct > 0 && (
          <div className="bg-sky-500" style={{ width: `${awayPct}%` }} />
        )}
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-600">
        <span className="font-medium">
          {homeName} {home_wins}V
        </span>
        <span>{draws}N</span>
        <span className="font-medium">
          {awayName} {away_wins}V
        </span>
      </div>
      {last_matches.length > 0 && (
        <ul className="mt-4 space-y-2 border-t border-slate-100 pt-3">
          {last_matches.map((m, i) => (
            <li
              key={`${m.date_utc}-${i}`}
              data-testid="h2h-row"
              className="flex items-center justify-between text-xs text-slate-700"
            >
              <span className="tabular-nums text-slate-500">
                {formatDate(m.date_utc)}
              </span>
              <span className="font-medium">
                {m.home_team} {m.score} {m.away_team}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default H2HSection;
