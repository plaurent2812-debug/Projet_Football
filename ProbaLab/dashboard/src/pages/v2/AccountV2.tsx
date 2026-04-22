import { NavLink, Navigate, Outlet } from 'react-router-dom';
import { useV2User } from '@/hooks/v2/useV2User';

interface AccountTab {
  readonly to: string;
  readonly label: string;
}

const TABS: readonly AccountTab[] = [
  { to: 'profil', label: 'Profil' },
  { to: 'abonnement', label: 'Abonnement' },
  { to: 'bankroll', label: 'Bankroll' },
  { to: 'notifications', label: 'Notifications' },
];

export interface AccountV2Props {
  'data-testid'?: string;
}

export function AccountV2({
  'data-testid': dataTestId = 'account-v2',
}: AccountV2Props = {}) {
  const { isVisitor } = useV2User();

  if (isVisitor) {
    return <Navigate to="/login" replace />;
  }

  return (
    <main
      data-testid={dataTestId}
      aria-label="Mon compte"
      className="mx-auto max-w-6xl px-4 py-8"
    >
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
        Mon compte
      </h1>
      <nav
        aria-label="Onglets du compte"
        className="mt-6 border-b border-slate-200 dark:border-slate-800"
      >
        <ul className="flex gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <li key={tab.to} className="shrink-0">
              <NavLink
                to={tab.to}
                className={({ isActive }) =>
                  [
                    'inline-block rounded-t-lg px-4 py-2 text-sm font-medium transition whitespace-nowrap',
                    isActive
                      ? 'border-b-2 border-emerald-500 text-emerald-600'
                      : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white',
                  ].join(' ')
                }
              >
                {tab.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="mt-8">
        <Outlet />
      </div>
    </main>
  );
}

export default AccountV2;
