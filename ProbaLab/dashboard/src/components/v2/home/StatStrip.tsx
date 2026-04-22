import { StatTile } from '@/components/v2/system/StatTile';
import type { PerformanceSummary } from '@/types/v2/performance';

interface Props {
  data?: PerformanceSummary;
  loading?: boolean;
  'data-testid'?: string;
}

function formatDelta(v: number, suffix = '%'): string {
  const sign = v >= 0 ? '+' : '';
  return `${sign}${v.toFixed(1)}${suffix} vs 7j`;
}

export function StatStrip({ data, loading, 'data-testid': dataTestId = 'stat-strip' }: Props) {
  if (loading || !data) {
    return (
      <div
        data-testid={dataTestId}
        className="grid grid-cols-2 md:grid-cols-4 gap-3"
      >
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            data-testid="stat-tile-skeleton"
            className="h-20 rounded-lg bg-surface-2 animate-pulse"
            style={{ background: 'var(--surface-2)' }}
          />
        ))}
      </div>
    );
  }
  const bankrollStr = `${data.bankroll.value.toLocaleString('fr-FR').replace(/\u202f/g, ' ')} €`;
  return (
    <div
      data-testid={dataTestId}
      className="grid grid-cols-2 md:grid-cols-4 gap-3"
    >
      <StatTile
        label="ROI 30J"
        value={`${data.roi30d.value.toFixed(1)}%`}
        delta={formatDelta(data.roi30d.deltaVs7d)}
        tone={data.roi30d.value >= 0 ? 'positive' : 'negative'}
      />
      <StatTile
        label="Accuracy"
        value={`${data.accuracy.value.toFixed(1)}%`}
        delta={formatDelta(data.accuracy.deltaVs7d)}
      />
      <StatTile
        label="Brier 7J"
        value={data.brier7d.value.toFixed(3)}
        delta={formatDelta(data.brier7d.deltaVs7d, '')}
        tone={data.brier7d.deltaVs7d <= 0 ? 'positive' : 'negative'}
      />
      <StatTile label="Bankroll" value={bankrollStr} />
    </div>
  );
}

export default StatStrip;
