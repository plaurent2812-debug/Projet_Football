import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface Props {
  curve: Array<{ date: string; balance: number }>;
  height?: number;
  'data-testid'?: string;
}

const euro = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 0,
});

/**
 * Bankroll evolution area chart (Recharts).
 *
 * Default export so `React.lazy` picks it up without a named-adapter.
 * Pure presentation — no fetching, no local state: the parent slices
 * the curve to the active period and re-renders.
 */
export function BankrollChartImpl({
  curve,
  height = 280,
  'data-testid': dataTestId = 'bankroll-chart-impl',
}: Props) {
  return (
    <div data-testid={dataTestId} style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={curve}
          margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="v2-bankroll-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
          <XAxis
            dataKey="date"
            stroke="var(--text-muted)"
            fontSize={12}
            tickFormatter={(v: string) => v.slice(5, 10)}
            minTickGap={24}
          />
          <YAxis
            stroke="var(--text-muted)"
            fontSize={12}
            tickFormatter={(v: number) => euro.format(v)}
            width={72}
          />
          <Tooltip
            formatter={(value: number) => [euro.format(value), 'Solde']}
            labelFormatter={(label: string) =>
              new Date(label).toLocaleDateString('fr-FR', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
              })
            }
          />
          <Area
            type="monotone"
            dataKey="balance"
            stroke="var(--primary)"
            strokeWidth={2}
            fill="url(#v2-bankroll-grad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default BankrollChartImpl;
