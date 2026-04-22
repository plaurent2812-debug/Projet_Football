import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TrackRecordPoint } from '@/hooks/v2/useTrackRecordLive';

interface Props {
  data: TrackRecordPoint[];
  height?: number;
  'data-testid'?: string;
}

/**
 * Cumulative-ROI area chart rendered via Recharts.
 *
 * Exported as a default export so `React.lazy` can import it
 * without a named-default adapter. Intentionally renders a pure
 * Recharts tree — no fetching or state — so the consumer can swap
 * `data` (30j / 90j / 1 an) without remounting the chart.
 */
export function ROIChart({
  data,
  height = 280,
  'data-testid': dataTestId = 'roi-chart',
}: Props) {
  return (
    <div data-testid={dataTestId} style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="v2-roi-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.4} />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
          <XAxis
            dataKey="date"
            stroke="var(--text-muted)"
            fontSize={12}
            tickFormatter={(v: string) => v.slice(5)}
            minTickGap={24}
          />
          <YAxis
            stroke="var(--text-muted)"
            fontSize={12}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(2)}%`, 'ROI cumulé']}
            labelFormatter={(label: string) => label}
          />
          <Area
            type="monotone"
            dataKey="roi"
            stroke="var(--primary)"
            strokeWidth={2}
            fill="url(#v2-roi-grad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default ROIChart;
