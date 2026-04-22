import { useEffect, useRef, useState } from 'react';
import { Check, MoreHorizontal, Trash2, X } from 'lucide-react';
import type { BetResult, BetRow } from '@/hooks/v2/useBankrollBets';
import { useDeleteBet, useUpdateBet } from '@/hooks/v2/useBankrollBets';

export interface BetsTableProps {
  bets: BetRow[];
  /**
   * Optional outcome change handler. When omitted, the table falls back
   * to firing `useUpdateBet(id)` via an inline row-local mutation so the
   * component stays drop-in usable without lifting state up.
   */
  onUpdateResult?: (id: string, result: BetResult) => void;
  /** Optional delete handler. When omitted, `useDeleteBet(id)` is used. */
  onDelete?: (id: string) => void;
  'data-testid'?: string;
}

type Filter = 'all' | 'pending' | 'won' | 'lost';

const FILTERS: Array<{ value: Filter; label: string }> = [
  { value: 'all', label: 'Tous' },
  { value: 'pending', label: 'En cours' },
  { value: 'won', label: 'Gagnés' },
  { value: 'lost', label: 'Perdus' },
];

const RESULT_LABEL: Record<BetResult, string> = {
  WIN: 'Gagné',
  LOSS: 'Perdu',
  PENDING: 'En cours',
  VOID: 'Annulé',
};

const RESULT_TONE: Record<BetResult, string> = {
  WIN: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  LOSS: 'bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300',
  PENDING: 'bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  VOID: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
};

const euro = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'EUR',
});
const dateFmt = new Intl.DateTimeFormat('fr-FR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

function matchesFilter(row: BetRow, filter: Filter): boolean {
  if (filter === 'all') return true;
  if (filter === 'pending') return row.result === 'PENDING';
  if (filter === 'won') return row.result === 'WIN';
  if (filter === 'lost') return row.result === 'LOSS';
  return true;
}

/**
 * Bets table — centrepiece of the Bankroll tab.
 *
 * Renders a responsive table (cards stack on mobile, full grid on
 * desktop) with filter chips on top and an inline action menu per row.
 * Mutations are delegated to `onUpdateResult` / `onDelete` when the
 * parent owns the state, and fall back to the shared bankroll hooks
 * so the component is usable as a drop-in in simpler contexts.
 */
export function BetsTable({
  bets,
  onUpdateResult,
  onDelete,
  'data-testid': dataTestId = 'bets-table',
}: BetsTableProps) {
  const [filter, setFilter] = useState<Filter>('all');
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  const rows = bets.filter((b) => matchesFilter(b, filter));

  return (
    <div
      data-testid={dataTestId}
      className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      {/* Filter chips */}
      <div
        role="group"
        aria-label="Filtrer les paris"
        className="flex flex-wrap gap-2"
      >
        {FILTERS.map((f) => {
          const active = f.value === filter;
          return (
            <button
              key={f.value}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(f.value)}
              className={
                'rounded-full border px-3 py-1 text-xs font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ' +
                (active
                  ? 'border-emerald-500 bg-emerald-500 text-white'
                  : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800')
              }
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {rows.length === 0 ? (
        <div
          data-testid="bets-empty"
          className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400"
        >
          Aucun pari à afficher pour ce filtre.
        </div>
      ) : (
        /*
         * Single rendering tree for both viewports : a `role="table"` grid
         * that collapses to card-like rows on mobile. Avoids duplicating
         * the row tree (which would break test-ids in JSDOM where media
         * queries are not evaluated).
         */
        <div
          role="table"
          aria-label="Historique des paris"
          className="w-full text-sm"
        >
          <div
            role="row"
            className="hidden grid-cols-[minmax(5rem,auto)_1fr_auto_auto_auto_auto] gap-3 border-b border-slate-200 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500 md:grid dark:border-slate-800 dark:text-slate-400"
          >
            <span role="columnheader">Date</span>
            <span role="columnheader">Pari</span>
            <span role="columnheader" className="text-right">
              Cote
            </span>
            <span role="columnheader" className="text-right">
              Mise
            </span>
            <span role="columnheader">Résultat</span>
            <span role="columnheader" className="sr-only">
              Actions
            </span>
          </div>
          <div className="flex flex-col divide-y divide-slate-100 dark:divide-slate-800">
            {rows.map((row) => (
              <div
                key={row.id}
                role="row"
                data-testid={`bet-row-${row.id}`}
                data-status={row.result}
                className="grid grid-cols-2 gap-x-3 gap-y-2 py-3 text-slate-700 dark:text-slate-200 md:grid-cols-[minmax(5rem,auto)_1fr_auto_auto_auto_auto] md:items-center md:gap-y-0"
              >
                <span
                  role="cell"
                  className="order-1 whitespace-nowrap text-xs text-slate-600 md:order-none md:text-sm dark:text-slate-300"
                >
                  {dateFmt.format(new Date(row.placed_at))}
                </span>
                <span role="cell" className="order-3 col-span-2 md:order-none md:col-span-1">
                  <span className="block font-medium text-slate-900 dark:text-white">
                    {row.match_title}
                  </span>
                  <span className="block text-xs text-slate-500 dark:text-slate-400">
                    {row.market} · {row.selection}
                  </span>
                </span>
                <span
                  role="cell"
                  className="order-4 text-right tabular-nums text-xs text-slate-600 md:order-none md:text-sm"
                >
                  <span className="md:hidden">Cote </span>
                  {row.odds.toFixed(2)}
                </span>
                <span
                  role="cell"
                  className="order-5 text-right tabular-nums text-xs text-slate-600 md:order-none md:text-sm"
                >
                  <span className="md:hidden">Mise </span>
                  {euro.format(row.stake)}
                </span>
                <span role="cell" className="order-2 justify-self-end md:order-none md:justify-self-start">
                  <ResultChip result={row.result} />
                </span>
                <span role="cell" className="order-6 justify-self-end md:order-none">
                  <RowActions
                    betId={row.id}
                    isOpen={openMenu === row.id}
                    onOpenChange={(v) => setOpenMenu(v ? row.id : null)}
                    onUpdateResult={onUpdateResult}
                    onDelete={onDelete}
                  />
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ResultChip({ result }: { result: BetResult }) {
  return (
    <span
      className={
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ' +
        RESULT_TONE[result]
      }
    >
      {RESULT_LABEL[result]}
    </span>
  );
}

interface RowActionsProps {
  betId: string;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdateResult?: (id: string, result: BetResult) => void;
  onDelete?: (id: string) => void;
}

function RowActions({
  betId,
  isOpen,
  onOpenChange,
  onUpdateResult,
  onDelete,
}: RowActionsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fallbackUpdate = useUpdateBet(betId);
  const fallbackDelete = useDeleteBet(betId);

  // Close on outside click / Escape.
  useEffect(() => {
    if (!isOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        onOpenChange(false);
      }
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onOpenChange(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKey);
    };
  }, [isOpen, onOpenChange]);

  const runUpdate = (result: BetResult) => {
    if (onUpdateResult) {
      onUpdateResult(betId, result);
    } else {
      fallbackUpdate.mutate({
        result,
        resolved_at: new Date().toISOString(),
      });
    }
    onOpenChange(false);
  };

  const runDelete = () => {
    if (onDelete) {
      onDelete(betId);
    } else {
      fallbackDelete.mutate();
    }
    onOpenChange(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        data-testid={`bet-actions-${betId}`}
        aria-label="Actions"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => onOpenChange(!isOpen)}
        className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 dark:hover:bg-slate-800 dark:hover:text-slate-200"
      >
        <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
      </button>
      {isOpen && (
        <div
          role="menu"
          aria-label={`Actions du pari ${betId}`}
          className="absolute right-0 z-10 mt-1 w-48 rounded-md border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => runUpdate('WIN')}
            className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <Check className="h-4 w-4 text-emerald-500" aria-hidden="true" />
            Marquer gagné
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => runUpdate('LOSS')}
            className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <X className="h-4 w-4 text-rose-500" aria-hidden="true" />
            Marquer perdu
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={runDelete}
            className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Supprimer
          </button>
        </div>
      )}
    </div>
  );
}

export default BetsTable;
