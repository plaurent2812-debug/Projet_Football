import { Link } from 'react-router-dom';

interface Props {
  'data-testid'?: string;
}

export function PremiumCTA({ 'data-testid': dataTestId = 'premium-cta' }: Props) {
  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl p-5"
      style={{
        border: '1px solid rgba(245, 158, 11, 0.4)',
        background: 'rgba(245, 158, 11, 0.06)',
      }}
    >
      <h3 className="text-sm font-semibold" style={{ color: 'var(--value, #f59e0b)' }}>
        PREMIUM · 14,99€/mois
      </h3>
      <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
        Value bets illimités, analyses IA, bankroll, alertes custom.
      </p>
      <Link
        to="/premium"
        className="mt-3 inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2"
        style={{
          background: 'var(--value, #f59e0b)',
          color: '#0a0e1a',
        }}
      >
        Activer l'abonnement
      </Link>
    </section>
  );
}

export default PremiumCTA;
