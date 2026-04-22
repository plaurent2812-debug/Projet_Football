import type { ReactNode } from 'react';

export type StatTone = 'neutral' | 'positive' | 'negative';

export interface StatTileProps {
  label: string;
  value: ReactNode;
  delta?: string;
  tone?: StatTone;
  'data-testid'?: string;
}

function toneColor(tone: StatTone): string {
  if (tone === 'positive') return 'var(--primary)';
  if (tone === 'negative') return 'var(--danger)';
  return 'var(--text-muted)';
}

export function StatTile({
  label,
  value,
  delta,
  tone = 'neutral',
  'data-testid': dataTestId = 'stat-tile',
}: StatTileProps) {
  return (
    <div
      role="group"
      data-testid={dataTestId}
      aria-label={`${label}: ${typeof value === 'string' ? value : ''}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-1)',
        padding: 'var(--space-3)',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
      }}
    >
      <span
        style={{
          fontSize: 12,
          color: 'var(--text-faint)',
          textTransform: 'uppercase',
          letterSpacing: 0.4,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 24,
          fontWeight: 700,
          color: 'var(--text)',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {value}
      </span>
      {delta && (
        <span
          data-tone={tone}
          style={{ fontSize: 12, color: toneColor(tone), fontVariantNumeric: 'tabular-nums' }}
        >
          {delta}
        </span>
      )}
    </div>
  );
}

export default StatTile;
