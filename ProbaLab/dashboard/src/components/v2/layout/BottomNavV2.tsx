import { Link } from 'react-router-dom';
import { Home, List, User } from 'lucide-react';

export function BottomNavV2() {
  return (
    <nav
      aria-label="Navigation mobile"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 40,
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
        padding: 'var(--space-2) 0',
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
      }}
    >
      <Link to="/" aria-label="Accueil" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, color: 'var(--text)' }}>
        <Home size={20} aria-hidden="true" />
        <span style={{ fontSize: 12 }}>Accueil</span>
      </Link>
      <Link to="/matchs" aria-label="Matchs" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, color: 'var(--text)' }}>
        <List size={20} aria-hidden="true" />
        <span style={{ fontSize: 12 }}>Matchs</span>
      </Link>
      <Link to="/compte" aria-label="Compte" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, color: 'var(--text)' }}>
        <User size={20} aria-hidden="true" />
        <span style={{ fontSize: 12 }}>Compte</span>
      </Link>
    </nav>
  );
}

export default BottomNavV2;
