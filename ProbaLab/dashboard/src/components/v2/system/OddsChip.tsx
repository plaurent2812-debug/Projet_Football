export interface OddsChipProps {
  value: number;
  highlight?: boolean;
  'data-testid'?: string;
}

export function OddsChip({
  value,
  highlight = false,
  'data-testid': dataTestId = 'odds-chip',
}: OddsChipProps) {
  const formatted = value.toFixed(2);
  return (
    <span
      data-testid={dataTestId}
      aria-label={`Cote ${formatted}`}
      data-highlight={highlight}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        borderRadius: 'var(--radius-sm)',
        background: highlight ? 'var(--primary-soft)' : 'var(--surface-2)',
        color: highlight ? 'var(--primary)' : 'var(--text)',
        border: `1px solid ${highlight ? 'var(--primary)' : 'var(--border)'}`,
        fontFamily: 'var(--font-mono)',
        fontSize: 14,
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      @{formatted}
    </span>
  );
}

export default OddsChip;
