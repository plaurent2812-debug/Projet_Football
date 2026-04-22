export type RuleChipVariant = 'label' | 'condition' | 'action';

export interface RuleChipProps {
  variant: RuleChipVariant;
  text: string;
  'data-testid'?: string;
}

function variantStyle(variant: RuleChipVariant): {
  background: string;
  color: string;
  border: string;
} {
  if (variant === 'label') {
    return {
      background: 'var(--surface-2)',
      color: 'var(--text-faint)',
      border: '1px solid var(--border)',
    };
  }
  if (variant === 'condition') {
    return {
      background: 'var(--surface)',
      color: 'var(--text)',
      border: '1px solid var(--info)',
    };
  }
  return {
    background: 'var(--primary-soft)',
    color: 'var(--primary)',
    border: '1px solid var(--primary)',
  };
}

export function RuleChip({
  variant,
  text,
  'data-testid': dataTestId = 'rule-chip',
}: RuleChipProps) {
  const s = variantStyle(variant);
  return (
    <span
      data-testid={dataTestId}
      data-variant={variant}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 10px',
        borderRadius: 'var(--radius-lg)',
        fontSize: 12,
        fontWeight: variant === 'label' ? 700 : 500,
        letterSpacing: variant === 'label' ? 0.5 : 0,
        textTransform: variant === 'label' ? 'uppercase' : 'none',
        background: s.background,
        color: s.color,
        border: s.border,
      }}
    >
      {text}
    </span>
  );
}

export default RuleChip;
