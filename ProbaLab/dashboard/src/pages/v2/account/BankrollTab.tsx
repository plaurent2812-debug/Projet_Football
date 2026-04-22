import { useMemo } from 'react';
import { AlertCircle } from 'lucide-react';
import { BankrollHeader } from '@/components/v2/account/bankroll/BankrollHeader';
import { KPIStrip5 } from '@/components/v2/account/bankroll/KPIStrip5';
import { BankrollChart } from '@/components/v2/account/bankroll/BankrollChart';
import type { BankrollCurvePoint } from '@/components/v2/account/bankroll/BankrollChart';
import { ROIByMarketChart } from '@/components/v2/account/bankroll/ROIByMarketChart';
import { BetsTable } from '@/components/v2/account/bankroll/BetsTable';
import { useBankroll } from '@/hooks/v2/useBankroll';
import { useBankrollBets } from '@/hooks/v2/useBankrollBets';
import type { BetRow } from '@/hooks/v2/useBankrollBets';
import { useROIByMarket } from '@/hooks/v2/useROIByMarket';

/**
 * Build a daily bankroll curve by replaying settled bets chronologically.
 *
 * PENDING bets are ignored. A WIN contributes `stake * (odds - 1)`,
 * a LOSS contributes `-stake`, a VOID contributes 0. The curve starts
 * at `initialBalance` anchored on the earliest bet date (or now when
 * there are no bets).
 */
function buildCurve(
  initialBalance: number,
  bets: BetRow[],
): BankrollCurvePoint[] {
  if (bets.length === 0) {
    return [{ date: new Date().toISOString(), balance: initialBalance }];
  }
  const sorted = [...bets].sort(
    (a, b) =>
      new Date(a.placed_at).getTime() - new Date(b.placed_at).getTime(),
  );
  let balance = initialBalance;
  const curve: BankrollCurvePoint[] = [
    { date: sorted[0].placed_at, balance },
  ];
  for (const bet of sorted) {
    if (bet.result === 'WIN') {
      balance += bet.stake * (bet.odds - 1);
    } else if (bet.result === 'LOSS') {
      balance -= bet.stake;
    }
    const date = bet.resolved_at ?? bet.placed_at;
    curve.push({ date, balance });
  }
  return curve;
}

/**
 * "Bankroll" tab — composition page for the bankroll workflow.
 *
 * Layout (top → bottom):
 *   1. `<BankrollHeader />` — title + "Paramètres" + "+ Ajouter un pari"
 *   2. `<KPIStrip5 />`     — five hero KPIs driven by the summary
 *   3. Grid 2 cols (desktop) / 1 col (mobile) :
 *        - `<BankrollChart />` (left)
 *        - `<ROIByMarketChart />` (right)
 *   4. `<BetsTable />`     — paginated filterable bets list
 *
 * Owns the loading skeleton, the error state and the empty state. The
 * mutations bubble up through the dedicated hooks inside `BetsTable`.
 */
export function BankrollTab() {
  const bankrollQuery = useBankroll();
  const betsQuery = useBankrollBets();
  const roiQuery = useROIByMarket();

  const bets = betsQuery.data ?? [];
  const roiRows = roiQuery.data ?? [];

  const curve = useMemo(
    () => buildCurve(bankrollQuery.data?.initial_balance ?? 0, bets),
    [bankrollQuery.data?.initial_balance, bets],
  );

  if (bankrollQuery.isLoading) {
    return (
      <div data-testid="bankroll-tab" className="space-y-6">
        <BankrollHeader />
        <div
          data-testid="bankroll-skeleton"
          aria-busy="true"
          aria-label="Chargement du bankroll"
          className="space-y-4"
        >
          <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />
          <div className="h-64 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />
          <div className="h-40 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />
        </div>
      </div>
    );
  }

  if (bankrollQuery.isError || !bankrollQuery.data) {
    return (
      <div data-testid="bankroll-tab" className="space-y-6">
        <BankrollHeader />
        <div
          data-testid="bankroll-error"
          role="alert"
          className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300"
        >
          <AlertCircle className="mt-0.5 h-4 w-4" aria-hidden="true" />
          <div>
            <strong>Impossible de charger ton bankroll.</strong>
            <p className="mt-1 text-rose-600 dark:text-rose-400">
              Réessaie plus tard ou rafraîchis la page.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const bankroll = bankrollQuery.data;
  const isEmpty = bets.length === 0;

  return (
    <div data-testid="bankroll-tab" className="space-y-6">
      <BankrollHeader />

      <KPIStrip5 bankroll={bankroll} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <BankrollChart curve={curve} />
        <ROIByMarketChart data={roiRows} />
      </div>

      {isEmpty ? (
        <div
          data-testid="bankroll-empty"
          className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"
        >
          <p className="font-medium text-slate-700 dark:text-slate-200">
            Aucun pari enregistré pour le moment.
          </p>
          <p className="mt-1">
            Clique sur « + Ajouter un pari » pour commencer à suivre ta
            bankroll.
          </p>
        </div>
      ) : (
        <BetsTable bets={bets} />
      )}
    </div>
  );
}

export default BankrollTab;
