import { Link, useLocation } from 'react-router-dom';
import { Home, List, User } from 'lucide-react';

function isActive(pathname: string, target: 'home' | 'matchs' | 'compte'): boolean {
  if (target === 'home') return pathname === '/';
  if (target === 'matchs') return pathname === '/matchs' || pathname.startsWith('/matchs/');
  if (target === 'compte') return pathname === '/compte' || pathname.startsWith('/compte/');
  return false;
}

export function BottomNavV2() {
  const { pathname } = useLocation();
  const homeActive = isActive(pathname, 'home');
  const matchsActive = isActive(pathname, 'matchs');
  const compteActive = isActive(pathname, 'compte');

  const baseLinkStyle = {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: 2,
  };
  const activeColor = 'var(--primary)';
  const inactiveColor = 'var(--text)';

  return (
    <nav
      aria-label="Navigation mobile"
      className="flex md:hidden"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 40,
        justifyContent: 'space-around',
        alignItems: 'center',
        padding: 'var(--space-2) 0',
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
      }}
    >
      <Link
        to="/"
        aria-label="Accueil"
        aria-current={homeActive ? 'page' : undefined}
        style={{ ...baseLinkStyle, color: homeActive ? activeColor : inactiveColor }}
      >
        <Home size={20} aria-hidden="true" />
        <span style={{ fontSize: 12 }}>Accueil</span>
      </Link>
      <Link
        to="/matchs"
        aria-label="Matchs"
        aria-current={matchsActive ? 'page' : undefined}
        style={{ ...baseLinkStyle, color: matchsActive ? activeColor : inactiveColor }}
      >
        <List size={20} aria-hidden="true" />
        <span style={{ fontSize: 12 }}>Matchs</span>
      </Link>
      <Link
        to="/compte"
        aria-label="Compte"
        aria-current={compteActive ? 'page' : undefined}
        style={{ ...baseLinkStyle, color: compteActive ? activeColor : inactiveColor }}
      >
        <User size={20} aria-hidden="true" />
        <span style={{ fontSize: 12 }}>Compte</span>
      </Link>
    </nav>
  );
}

export default BottomNavV2;
