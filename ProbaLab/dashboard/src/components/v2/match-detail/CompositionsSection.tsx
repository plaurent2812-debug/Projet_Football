import { Users } from 'lucide-react';
import type {
  CompositionsPayload,
  CompositionsStatus,
  Lineup,
} from '../../../types/v2/match-detail';

export interface CompositionsSectionProps {
  compositions: CompositionsPayload;
  homeName: string;
  awayName: string;
  'data-testid'?: string;
}

const STATUS_LABEL: Record<CompositionsStatus, string> = {
  confirmed: 'Confirmée',
  probable: 'Probable',
  unavailable: 'Indisponible',
};

const STATUS_BG: Record<CompositionsStatus, string> = {
  confirmed: 'bg-emerald-100 text-emerald-800',
  probable: 'bg-amber-100 text-amber-800',
  unavailable: 'bg-slate-100 text-slate-600',
};

function TeamLineup({ name, lineup }: { name: string; lineup: Lineup }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-800">{name}</span>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium tabular-nums text-slate-600">
          {lineup.formation}
        </span>
      </div>
      <ul className="space-y-1 text-xs text-slate-700">
        {lineup.starters.map((p) => (
          <li
            key={p.number}
            className="flex items-center gap-2"
            data-testid="lineup-player"
          >
            <span className="inline-block w-6 text-right tabular-nums text-slate-500">
              {p.number}
            </span>
            <span className="font-medium">{p.name}</span>
            <span className="text-slate-400">{p.position}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CompositionsSection({
  compositions,
  homeName,
  awayName,
  'data-testid': dataTestId = 'compositions-section',
}: CompositionsSectionProps) {
  const { status, home, away } = compositions;
  const unavailable = status === 'unavailable' || (!home && !away);

  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Users className="h-4 w-4 text-slate-500" aria-hidden="true" />
          Compositions
        </h3>
        <span
          data-testid="compositions-status"
          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${STATUS_BG[status]}`}
        >
          {STATUS_LABEL[status]}
        </span>
      </div>
      {unavailable ? (
        <p className="text-xs text-slate-500">
          Compositions non communiquées.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {home && <TeamLineup name={homeName} lineup={home} />}
          {away && <TeamLineup name={awayName} lineup={away} />}
        </div>
      )}
    </section>
  );
}

export default CompositionsSection;
