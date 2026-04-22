import { Link, useLocation } from 'react-router-dom';
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

function isActive(pathname: string, target: 'home' | 'matchs' | 'compte'): boolean {
  if (target === 'home') return pathname === '/';
  if (target === 'matchs') return pathname === '/matchs' || pathname.startsWith('/matchs/');
  if (target === 'compte') return pathname === '/compte' || pathname.startsWith('/compte/');
  return false;
}

export function HeaderV2({ userRole, trialDaysLeft }: HeaderV2Props) {
  const badge = roleBadge(userRole, trialDaysLeft);
  const { pathname } = useLocation();
  const homeActive = isActive(pathname, 'home');
  const matchsActive = isActive(pathname, 'matchs');
  const compteActive = isActive(pathname, 'compte');

  const activeStyle = { color: 'var(--primary)', fontWeight: 600 };
  const inactiveStyle = { color: 'var(--text)' };

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
      <nav
        aria-label="Navigation"
        className="hidden md:flex"
        style={{ gap: 'var(--space-4)' }}
      >
        <Link
          to="/"
          aria-label="Accueil"
          aria-current={homeActive ? 'page' : undefined}
          style={homeActive ? activeStyle : inactiveStyle}
        >
          Accueil
        </Link>
        <Link
          to="/matchs"
          aria-label="Matchs"
          aria-current={matchsActive ? 'page' : undefined}
          style={matchsActive ? activeStyle : inactiveStyle}
        >
          Matchs
        </Link>
        <Link
          to="/compte"
          aria-label="Compte"
          aria-current={compteActive ? 'page' : undefined}
          style={compteActive ? activeStyle : inactiveStyle}
        >
          Compte
        </Link>
      </nav>
      {badge && (
        <span
          aria-label={`Statut : ${badge}`}
          className="hidden md:inline-block"
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
