import { Link } from 'react-router-dom';

export interface TrialBannerProps {
  daysLeft: number;
  endDate?: string;
  'data-testid'?: string;
}

export function TrialBanner({
  daysLeft,
  endDate,
  'data-testid': dataTestId = 'trial-banner',
}: TrialBannerProps) {
  return (
    <div
      data-testid={dataTestId}
      role="region"
      aria-label="Trial premium banner"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 'var(--space-2)',
        padding: 'var(--space-2) var(--space-4)',
        background: 'linear-gradient(90deg, var(--primary-soft), var(--surface))',
        color: 'var(--text)',
        borderBottom: '1px solid var(--primary)',
        fontSize: 14,
      }}
    >
      <span>
        Trial premium · J-{daysLeft} · Tout est débloqué
        {endDate ? ` jusqu'au ${endDate}` : ''}
      </span>
      <Link
        to="/premium"
        aria-label="Activer l'abonnement"
        style={{ color: 'var(--primary)', fontWeight: 600, textDecoration: 'underline' }}
      >
        Activer l'abonnement
      </Link>
    </div>
  );
}

export default TrialBanner;
