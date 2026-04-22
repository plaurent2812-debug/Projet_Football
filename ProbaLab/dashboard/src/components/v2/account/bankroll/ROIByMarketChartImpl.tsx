import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ROIByMarketItem } from '@/hooks/v2/useROIByMarket';

interface Props {
  data: ROIByMarketItem[];
  height?: number;
  'data-testid'?: string;
}

/**
 * Horizontal diverging bar chart — one bar per market, positive
 * extending right (primary colour), negative extending left (danger).
 * Default export so `React.lazy` picks it up directly.
 */
export function ROIByMarketChartImpl({
  data,
  height,
  'data-testid': dataTestId = 'roi-by-market-impl',
}: Props) {
  // Height grows with the number of markets so small datasets don't
  // end up with an absurdly thick bar.
  const resolvedHeight = height ?? Math.max(160, 40 * data.length);

  return (
    <div data-testid={dataTestId} style={{ width: '100%', height: resolvedHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 12, left: 12, bottom: 4 }}
        >
          <XAxis
            type="number"
            stroke="var(--text-muted)"
            fontSize={12}
            tickFormatter={(v: number) => `${v}%`}
            domain={['auto', 'auto']}
          />
          <YAxis
            type="category"
            dataKey="market"
            stroke="var(--text-muted)"
            fontSize={12}
            width={72}
          />
          <ReferenceLine x={0} stroke="var(--border)" />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(1)}%`, 'ROI']}
            cursor={{ fill: 'rgba(148,163,184,0.12)' }}
          />
          <Bar dataKey="roi_pct" radius={[4, 4, 4, 4]}>
            {data.map((row) => (
              <Cell
                key={row.market}
                fill={row.roi_pct >= 0 ? 'var(--primary)' : 'var(--danger)'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default ROIByMarketChartImpl;
