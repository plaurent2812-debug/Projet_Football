import { lazy, Suspense } from 'react';
import { TrendingDown, TrendingUp } from 'lucide-react';
import type { ROIByMarketItem } from '@/hooks/v2/useROIByMarket';

/** Lazy boundary — Recharts BarChart ships in its own chunk. */
const ROIByMarketChartImpl = lazy(() => import('./ROIByMarketChartImpl'));

interface Props {
  data: ROIByMarketItem[];
  'data-testid'?: string;
}

function formatSignedPct(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

/**
 * ROI-per-market card.
 *
 * Renders:
 *   - an accessible row-list (one `<li>` per market with label, sample
 *     count and signed percentage — screen-reader friendly even before
 *     the chart chunk arrives) ;
 *   - a lazy Recharts horizontal BarChart (visual layer).
 *
 * Keeping the text rows in the wrapper means the page is usable even
 * when Recharts fails to load or JS is disabled on that chunk.
 */
export function ROIByMarketChart({
  data,
  'data-testid': dataTestId = 'roi-by-market',
}: Props) {
  if (data.length === 0) {
    return (
      <div
        data-testid={dataTestId}
        style={{
          padding: 'var(--space-4)',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--text-muted)',
          fontSize: 14,
          textAlign: 'center',
        }}
      >
        Aucune donnée disponible pour cette période.
      </div>
    );
  }

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
      <h3
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: 'var(--text)',
          margin: 0,
        }}
      >
        ROI par marché
      </h3>

      <Suspense
        fallback={
          <div
            data-testid="roi-by-market-fallback"
            style={{
              height: 200,
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface)',
              border: '1px dashed var(--border)',
            }}
          />
        }
      >
        <ROIByMarketChartImpl data={data} />
      </Suspense>

      <ul
        aria-label="Rendement par marché"
        style={{
          listStyle: 'none',
          margin: 0,
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-2)',
        }}
      >
        {data.map((row) => {
          const positive = row.roi_pct >= 0;
          const tone = positive ? 'positive' : 'negative';
          const Icon = positive ? TrendingUp : TrendingDown;
          return (
            <li
              key={row.market}
              data-testid={`roi-row-${row.market}`}
              data-tone={tone}
              style={{
                display: 'grid',
                gridTemplateColumns: '6rem 1fr auto',
                alignItems: 'center',
                gap: 'var(--space-3)',
                fontSize: 13,
                color: 'var(--text)',
              }}
            >
              <span style={{ fontWeight: 600 }}>{row.market}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                {row.n} paris · {row.wins}W · {row.losses}L
                {row.voids > 0 ? ` · ${row.voids}V` : ''}
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  color: positive ? 'var(--primary)' : 'var(--danger)',
                  fontVariantNumeric: 'tabular-nums',
                  fontWeight: 600,
                }}
              >
                <Icon size={14} aria-hidden="true" />
                {formatSignedPct(row.roi_pct)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default ROIByMarketChart;
