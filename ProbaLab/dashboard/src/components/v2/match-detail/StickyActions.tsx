import { Bell, Check, Plus } from 'lucide-react';
import { useAddToBankroll } from '../../../hooks/v2/useAddToBankroll';
import type { FixtureId } from '../../../types/v2/common';
import type { Recommendation } from '../../../types/v2/match-detail';

export interface StickyActionsProps {
  fixtureId: FixtureId;
  recommendation: Recommendation;
  /**
   * Stake par défaut (en € ou unités bankroll) passé à la mutation
   * d'ajout au bankroll. Par défaut 10 — cohérent avec l'expérience
   * "suivre en un clic" du mock-up (le détail du stake est configurable
   * ailleurs dans le parcours Premium).
   */
  stake?: number;
  onAlertKickoff?: () => void;
  'data-testid'?: string;
}

export function StickyActions({
  fixtureId,
  recommendation,
  stake = 10,
  onAlertKickoff,
  'data-testid': dataTestId = 'sticky-actions',
}: StickyActionsProps) {
  const addToBankroll = useAddToBankroll();
  const { isPending, isSuccess, isError } = addToBankroll;
  const disableBankroll = isPending || isSuccess;

  const handleAdd = () => {
    if (disableBankroll) return;
    addToBankroll.mutate({
      fixture_id: fixtureId,
      market_key: recommendation.market_key,
      odds: recommendation.odds,
      stake,
    });
  };

  const handleAlert = () => {
    onAlertKickoff?.();
  };

  const bankrollLabel = isSuccess
    ? 'Ajouté au bankroll'
    : isPending
      ? 'Ajout en cours…'
      : 'Suivre dans mon bankroll';

  return (
    <div
      data-testid={dataTestId}
      className="flex flex-col gap-2"
    >
      <button
        type="button"
        onClick={handleAdd}
        disabled={disableBankroll}
        aria-busy={isPending}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500 disabled:opacity-60"
      >
        {isSuccess ? (
          <Check className="h-4 w-4" aria-hidden="true" />
        ) : (
          <Plus className="h-4 w-4" aria-hidden="true" />
        )}
        {bankrollLabel}
      </button>
      <button
        type="button"
        onClick={handleAlert}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 transition hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
      >
        <Bell className="h-4 w-4" aria-hidden="true" />
        Alerte kick-off
      </button>
      {isError && (
        <p
          role="alert"
          className="text-xs text-red-600"
          data-testid="sticky-actions-error"
        >
          L’ajout a échoué. Réessaie.
        </p>
      )}
    </div>
  );
}

export default StickyActions;
