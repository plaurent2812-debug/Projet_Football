import { Link } from 'react-router-dom';
import type { UserRole } from '../../../types/v2/common';

export interface HeaderV2Props {
  userRole: UserRole;
  trialDaysLeft?: number;
}

function roleBadge(role: UserRole, trialDaysLeft?: number): string {
  if (role === 'trial' && typeof trialDaysLeft === 'number') {
    return `Trial J-${trialDaysLeft}`;
  }
  if (role === 'premium') return 'Premium';
  if (role === 'free') return 'Free';
  if (role === 'admin') return 'Admin';
  return '';
}

export function HeaderV2({ userRole, trialDaysLeft }: HeaderV2Props) {
  const badge = roleBadge(userRole, trialDaysLeft);
  return (
    <header
      aria-label="Navigation principale"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 40,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--space-3) var(--space-4)',
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <Link to="/" aria-label="ProbaLab" style={{ color: 'var(--primary)', fontWeight: 700 }}>
        ProbaLab
      </Link>
      <nav aria-label="Navigation" style={{ display: 'flex', gap: 'var(--space-4)' }}>
        <Link to="/" aria-label="Accueil">Accueil</Link>
        <Link to="/matchs" aria-label="Matchs">Matchs</Link>
        <Link to="/compte" aria-label="Compte">Compte</Link>
      </nav>
      {badge && (
        <span
          aria-label={`Statut : ${badge}`}
          style={{
            fontSize: 12,
            padding: '2px 8px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--surface-2)',
            color: 'var(--text-muted)',
          }}
        >
          {badge}
        </span>
      )}
    </header>
  );
}

export default HeaderV2;
