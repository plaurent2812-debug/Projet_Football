export interface ValueBadgeProps {
  edge: number;
  'data-testid'?: string;
}

export function ValueBadge({ edge, 'data-testid': dataTestId = 'value-badge' }: ValueBadgeProps) {
  const pct = (edge * 100).toFixed(1);
  const label = `Value bet +${pct}%`;
  return (
    <span
      data-testid={dataTestId}
      aria-label={label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--space-1)',
        padding: '2px 8px',
        borderRadius: 'var(--radius-sm)',
        background: 'var(--value)',
        color: '#111827',
        fontSize: 12,
        fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        letterSpacing: 0.3,
      }}
    >
      <span aria-hidden="true" style={{ fontWeight: 700, fontSize: 10 }}>
        VALUE
      </span>
      +{pct}%
    </span>
  );
}

export default ValueBadge;
