import { Shield } from 'lucide-react';

interface Props {
  'data-testid'?: string;
}

/**
 * Inline banner surfacing the monthly transparency guarantee.
 *
 * Rule: if CLV over the last 30 days becomes negative, the user
 * is credited with a free month. The icon is a lucide `Shield` —
 * no emoji.
 */
export function TransparencyGuarantee({
  'data-testid': dataTestId = 'transparency-guarantee',
}: Props) {
  return (
    <section
      data-testid={dataTestId}
      aria-labelledby="transparency-guarantee-title"
      className="rounded-2xl p-8 text-center"
      style={{
        background: 'color-mix(in oklab, var(--primary) 10%, transparent)',
        border: '1px solid color-mix(in oklab, var(--primary) 35%, transparent)',
      }}
    >
      <div className="mx-auto flex items-center justify-center gap-2">
        <Shield size={20} aria-hidden="true" style={{ color: 'var(--primary)' }} />
        <h3
          id="transparency-guarantee-title"
          className="text-lg font-semibold"
          style={{ color: 'var(--primary)' }}
        >
          Garantie transparence
        </h3>
      </div>
      <p className="mx-auto mt-3 max-w-2xl text-sm" style={{ color: 'var(--text-muted)' }}>
        Si le CLV 30 jours devient négatif, vous recevez automatiquement un{' '}
        <strong style={{ color: 'var(--text)' }}>mois offert</strong>. Nos chiffres
        sont publics, vérifiables, mis à jour toutes les 5 minutes.
      </p>
    </section>
  );
}

export default TransparencyGuarantee;
