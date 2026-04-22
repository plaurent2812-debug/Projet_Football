import { Zap } from 'lucide-react';
import type { UserRole } from '../../../types/v2/common';
import type { ValueBet } from '../../../types/v2/match-detail';
import { LockOverlay } from '../system/LockOverlay';
import { OddsChip } from '../system/OddsChip';
import { ValueBadge } from '../system/ValueBadge';

export interface ValueBetsListProps {
  valueBets: ValueBet[];
  userRole: UserRole;
  matchTitle?: string;
  'data-testid'?: string;
}

const UPGRADE_MESSAGE = 'Débloque tous les value bets avec Premium';
const SIGNUP_MESSAGE = 'Crée un compte pour voir les value bets';

function ValueBetRow({ bet }: { bet: ValueBet }) {
  return (
    <li
      data-testid="value-bet-row"
      aria-label={`${bet.label}, edge ${(bet.edge * 100).toFixed(1)}%, cote ${bet.best_odds.toFixed(2)}`}
      className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"
    >
      <span className="min-w-0 flex-1 truncate font-medium text-slate-900">
        {bet.label}
      </span>
      <ValueBadge edge={bet.edge} />
      <OddsChip value={bet.best_odds} highlight />
    </li>
  );
}

export function ValueBetsList({
  valueBets,
  userRole,
  matchTitle,
  'data-testid': dataTestId = 'value-bets-list',
}: ValueBetsListProps) {
  const heading = (
    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
      <Zap className="h-4 w-4 text-amber-500" aria-hidden="true" />
      Value bets
    </h3>
  );

  const ariaLabel = matchTitle
    ? `Value bets — ${matchTitle}`
    : 'Value bets du match';

  if (valueBets.length === 0) {
    return (
      <section
        data-testid={dataTestId}
        aria-label={ariaLabel}
        className="rounded-xl border border-slate-200 bg-white p-4"
      >
        {heading}
        <p className="text-xs text-slate-500">Aucun value bet détecté.</p>
      </section>
    );
  }

  if (userRole === 'visitor') {
    return (
      <section
        data-testid={dataTestId}
        aria-label={ariaLabel}
        className="rounded-xl border border-slate-200 bg-white p-4"
      >
        {heading}
        <LockOverlay message={SIGNUP_MESSAGE}>
          <ul className="flex flex-col gap-2">
            {valueBets.map((b) => (
              <ValueBetRow key={b.market_key} bet={b} />
            ))}
          </ul>
        </LockOverlay>
      </section>
    );
  }

  if (userRole === 'free' && valueBets.length > 1) {
    const [first, ...rest] = valueBets;
    return (
      <section
        data-testid={dataTestId}
        aria-label={ariaLabel}
        className="rounded-xl border border-slate-200 bg-white p-4"
      >
        {heading}
        <ul className="mb-2 flex flex-col gap-2">
          <ValueBetRow bet={first} />
        </ul>
        <LockOverlay message={UPGRADE_MESSAGE}>
          <ul className="flex flex-col gap-2">
            {rest.map((b) => (
              <ValueBetRow key={b.market_key} bet={b} />
            ))}
          </ul>
        </LockOverlay>
      </section>
    );
  }

  return (
    <section
      data-testid={dataTestId}
      aria-label={ariaLabel}
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      {heading}
      <ul className="flex flex-col gap-2">
        {valueBets.map((b) => (
          <ValueBetRow key={b.market_key} bet={b} />
        ))}
      </ul>
    </section>
  );
}

export default ValueBetsList;
