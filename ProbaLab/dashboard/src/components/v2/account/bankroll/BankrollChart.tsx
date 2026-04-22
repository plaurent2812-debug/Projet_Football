import { lazy, Suspense, useMemo, useState } from 'react';

/** Lazy boundary — keeps Recharts out of the initial bundle. */
const BankrollChartImpl = lazy(() => import('./BankrollChartImpl'));

export interface BankrollCurvePoint {
  date: string;
  balance: number;
}

type Range = '7' | '30' | '90' | 'all';

const RANGES: Array<{ value: Range; label: string }> = [
  { value: '7', label: '7j' },
  { value: '30', label: '30j' },
  { value: '90', label: '90j' },
  { value: 'all', label: 'Tout' },
];

interface Props {
  /** Chronological bankroll curve — each point is a daily balance snapshot. */
  curve: BankrollCurvePoint[];
  'data-testid'?: string;
}

/**
 * Bankroll evolution card — local `range` state drives a pure client-side
 * slice over `curve`; the Recharts AreaChart lives in `BankrollChartImpl`
 * and is lazy-loaded so the account tab shell keeps a small bundle.
 */
export function BankrollChart({
  curve,
  'data-testid': dataTestId = 'bankroll-chart',
}: Props) {
  const [range, setRange] = useState<Range>('30');

  const sliced = useMemo(() => {
    if (range === 'all') return curve;
    const days = Number(range);
    const cutoff = Date.now() - days * 86400_000;
    return curve.filter((p) => new Date(p.date).getTime() >= cutoff);
  }, [curve, range]);

  return (
    <div
      data-testid={dataTestId}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
        padding: 'var(--space-4)',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-2)',
          flexWrap: 'wrap',
        }}
      >
        <h3
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: 'var(--text)',
            margin: 0,
          }}
        >
          Évolution bankroll
        </h3>
        <div
          role="group"
          aria-label="Période"
          className="inline-flex gap-1"
        >
          {RANGES.map((r) => {
            const active = r.value === range;
            return (
              <button
                key={r.value}
                type="button"
                aria-pressed={active}
                onClick={() => setRange(r.value)}
                className="rounded-md px-3 py-1 text-xs font-semibold focus-visible:outline focus-visible:outline-2"
                style={{
                  background: active ? 'var(--primary)' : 'transparent',
                  color: active ? '#0a0e1a' : 'var(--text-muted)',
                  border: active
                    ? '1px solid var(--primary)'
                    : '1px solid var(--border)',
                }}
              >
                {r.label}
              </button>
            );
          })}
        </div>
      </div>
      <Suspense
        fallback={
          <div
            data-testid="bankroll-chart-fallback"
            style={{
              height: 280,
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface)',
              border: '1px dashed var(--border)',
            }}
          />
        }
      >
        <BankrollChartImpl curve={sliced} />
      </Suspense>
    </div>
  );
}

export default BankrollChart;
