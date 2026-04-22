import { Zap } from 'lucide-react';

interface Props {
  value: boolean;
  onChange: (v: boolean) => void;
  'data-testid'?: string;
}

export function ValueOnlyToggle({
  value,
  onChange,
  'data-testid': dataTestId = 'value-only-toggle',
}: Props) {
  return (
    <button
      type="button"
      data-testid={dataTestId}
      onClick={() => onChange(!value)}
      aria-pressed={value}
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2"
      style={{
        border: '1px solid var(--border)',
        background: value ? 'var(--primary)' : 'var(--surface)',
        color: value ? '#ffffff' : 'var(--text)',
      }}
    >
      <Zap aria-hidden="true" size={12} />
      <span>Value bets ≥5%</span>
    </button>
  );
}

export default ValueOnlyToggle;
