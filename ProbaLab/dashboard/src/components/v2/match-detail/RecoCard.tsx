import { TrendingUp } from 'lucide-react';
import type { Recommendation } from '../../../types/v2/match-detail';

export interface RecoCardProps {
  recommendation: Recommendation | null;
  'data-testid'?: string;
}

export function RecoCard({
  recommendation,
  'data-testid': dataTestId = 'reco-card',
}: RecoCardProps) {
  if (!recommendation) return null;

  const confidencePct = Math.round(recommendation.confidence * 100);
  const kellyPct = (recommendation.kelly_fraction * 100).toFixed(1);
  const edgePct = Math.round(recommendation.edge * 100);

  const ariaLabel = `Recommandation : ${recommendation.market_label} à cote ${recommendation.odds.toFixed(2)} chez ${recommendation.book_name}, confiance ${confidencePct}%, Kelly ${kellyPct}%, edge +${edgePct}%`;

  return (
    <section
      data-testid={dataTestId}
      aria-label={ariaLabel}
      className="rounded-2xl border border-emerald-200 border-l-4 border-l-emerald-500 bg-gradient-to-br from-emerald-50 to-white p-5 shadow-sm"
    >
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
        <TrendingUp className="h-3 w-3" aria-hidden="true" />
        Recommandation
      </div>
      <div className="mt-1 text-base font-semibold text-slate-900">
        {recommendation.market_label}
      </div>
      <div
        data-testid="reco-odds"
        className="mt-2 text-[34px] font-bold leading-none tabular-nums text-emerald-700"
      >
        {recommendation.odds.toFixed(2)}
      </div>
      <div className="mt-1 text-xs text-slate-500">
        chez {recommendation.book_name}
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
        <div>
          <dt className="text-slate-500">Confiance</dt>
          <dd className="mt-0.5 font-semibold tabular-nums text-slate-900">
            {confidencePct}%
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Kelly</dt>
          <dd className="mt-0.5 font-semibold tabular-nums text-slate-900">
            {kellyPct}%
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Edge</dt>
          <dd className="mt-0.5 font-semibold tabular-nums text-emerald-700">
            +{edgePct}%
          </dd>
        </div>
      </dl>
    </section>
  );
}

export default RecoCard;
