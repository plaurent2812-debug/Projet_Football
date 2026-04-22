import { Grid3x3 } from 'lucide-react';
import type { UserRole } from '../../../types/v2/common';
import type { MarketProb } from '../../../types/v2/match-detail';
import { LockOverlay } from '../system/LockOverlay';

export interface AllMarketsGridProps {
  markets: MarketProb[];
  userRole: UserRole;
  'data-testid'?: string;
}

const FREE_UNLOCKED_PREFIX = '1x2.';
const UPGRADE_MESSAGE = 'Débloque tous les marchés avec Premium';
const SIGNUP_MESSAGE = 'Crée un compte pour voir les marchés';

function MarketCell({ market }: { market: MarketProb }) {
  const pct = Math.round(market.probability * 100);
  const odds = market.best_book_odds ?? market.fair_odds;
  const cls = market.is_value
    ? 'border-amber-400 bg-amber-50'
    : 'border-slate-200 bg-white';
  return (
    <li
      data-testid="market-cell"
      data-value={market.is_value ? 'true' : 'false'}
      data-market-key={market.market_key}
      aria-label={`${market.label}, probabilité ${pct}%`}
      className={`flex items-center justify-between rounded-lg border p-3 text-sm ${cls}`}
    >
      <span className="truncate font-medium text-slate-800">
        {market.label}
      </span>
      <div className="ml-3 flex shrink-0 items-center gap-3 tabular-nums">
        <span className="text-slate-600">{pct}%</span>
        <span className="font-semibold text-slate-900">{odds.toFixed(2)}</span>
      </div>
    </li>
  );
}

export function AllMarketsGrid({
  markets,
  userRole,
  'data-testid': dataTestId = 'all-markets-grid',
}: AllMarketsGridProps) {
  const heading = (
    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
      <Grid3x3 className="h-4 w-4 text-slate-500" aria-hidden="true" />
      Tous les marchés
    </h3>
  );

  if (markets.length === 0) {
    return (
      <section
        data-testid={dataTestId}
        className="rounded-xl border border-slate-200 bg-white p-4"
      >
        {heading}
        <p className="text-xs text-slate-500">Aucun marché disponible.</p>
      </section>
    );
  }

  if (userRole === 'visitor') {
    return (
      <section
        data-testid={dataTestId}
        className="rounded-xl border border-slate-200 bg-white p-4"
      >
        {heading}
        <LockOverlay message={SIGNUP_MESSAGE}>
          <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {markets.map((m) => (
              <MarketCell key={m.market_key} market={m} />
            ))}
          </ul>
        </LockOverlay>
      </section>
    );
  }

  if (userRole === 'free') {
    const unlocked = markets.filter((m) =>
      m.market_key.startsWith(FREE_UNLOCKED_PREFIX),
    );
    const locked = markets.filter(
      (m) => !m.market_key.startsWith(FREE_UNLOCKED_PREFIX),
    );
    return (
      <section
        data-testid={dataTestId}
        className="rounded-xl border border-slate-200 bg-white p-4"
      >
        {heading}
        {unlocked.length > 0 && (
          <ul className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            {unlocked.map((m) => (
              <MarketCell key={m.market_key} market={m} />
            ))}
          </ul>
        )}
        {locked.length > 0 && (
          <LockOverlay message={UPGRADE_MESSAGE}>
            <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {locked.map((m) => (
                <MarketCell key={m.market_key} market={m} />
              ))}
            </ul>
          </LockOverlay>
        )}
      </section>
    );
  }

  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      {heading}
      <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
        {markets.map((m) => (
          <MarketCell key={m.market_key} market={m} />
        ))}
      </ul>
    </section>
  );
}

export default AllMarketsGrid;
