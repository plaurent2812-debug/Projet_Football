import { BookOpen } from 'lucide-react';
import type { BookOdd } from '../../../types/v2/match-detail';
import { OddsChip } from '../system/OddsChip';

export interface BookOddsListProps {
  bookOdds: BookOdd[];
  /**
   * Index (dans `bookOdds`) à mettre en évidence comme "meilleur prix".
   * Si non fourni, on cherche d'abord le premier item avec `is_best=true`,
   * puis on retombe sur le plus haut `odds`.
   */
  bestIndex?: number;
  'data-testid'?: string;
}

function resolveBestIndex(
  bookOdds: BookOdd[],
  override: number | undefined,
): number {
  if (override != null && override >= 0 && override < bookOdds.length) {
    return override;
  }
  const flagged = bookOdds.findIndex((b) => b.is_best);
  if (flagged !== -1) return flagged;
  let maxIdx = 0;
  let maxOdds = -Infinity;
  for (let i = 0; i < bookOdds.length; i++) {
    if (bookOdds[i].odds > maxOdds) {
      maxOdds = bookOdds[i].odds;
      maxIdx = i;
    }
  }
  return maxIdx;
}

export function BookOddsList({
  bookOdds,
  bestIndex,
  'data-testid': dataTestId = 'book-odds-list',
}: BookOddsListProps) {
  const heading = (
    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
      <BookOpen className="h-4 w-4 text-slate-500" aria-hidden="true" />
      Cotes bookmakers
    </h3>
  );

  if (bookOdds.length === 0) {
    return (
      <section
        data-testid={dataTestId}
        className="rounded-xl border border-slate-200 bg-white p-4"
      >
        {heading}
        <p className="text-xs text-slate-500">
          Aucune cote disponible pour le moment.
        </p>
      </section>
    );
  }

  const bestIdx = resolveBestIndex(bookOdds, bestIndex);

  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl border border-slate-200 bg-white p-4"
    >
      {heading}
      <ul
        aria-label="Comparateur de cotes par bookmaker"
        className="flex flex-col gap-2"
      >
        {bookOdds.map((b, i) => {
          const isBest = i === bestIdx;
          const rowTestId = isBest ? 'book-odds-item-best' : 'book-odds-item';
          return (
            <li
              key={b.bookmaker}
              data-testid={rowTestId}
              data-best={isBest}
              aria-label={`${b.bookmaker}, cote ${b.odds.toFixed(2)}`}
              className={`flex items-center gap-3 rounded-lg border p-3 text-sm ${
                isBest
                  ? 'border-emerald-500 bg-emerald-50'
                  : 'border-slate-200 bg-white'
              }`}
            >
              <span
                className={`flex-1 ${isBest ? 'font-semibold text-slate-900' : 'text-slate-700'}`}
              >
                {b.bookmaker}
              </span>
              <OddsChip value={b.odds} highlight={isBest} />
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export { resolveBestIndex };
export default BookOddsList;
