import type { ReactElement } from 'react';
import HomeV2 from '../../pages/v2/HomeV2';
import MatchesV2 from '../../pages/v2/MatchesV2';
import MatchDetailV2 from '../../pages/v2/MatchDetailV2';
import PremiumV2 from '../../pages/v2/PremiumV2';
import AccountV2 from '../../pages/v2/AccountV2';
import LoginV2 from '../../pages/v2/LoginV2';
import RegisterV2 from '../../pages/v2/RegisterV2';

export interface V2Route {
  path: string;
  element: ReactElement;
  isPublic: boolean;
}

export const v2Routes: readonly V2Route[] = [
  { path: '/', element: <HomeV2 />, isPublic: true },
  { path: '/matchs', element: <MatchesV2 />, isPublic: true },
  { path: '/matchs/:fixtureId', element: <MatchDetailV2 />, isPublic: true },
  { path: '/premium', element: <PremiumV2 />, isPublic: true },
  { path: '/compte', element: <AccountV2 />, isPublic: false },
  { path: '/login', element: <LoginV2 />, isPublic: true },
  { path: '/register', element: <RegisterV2 />, isPublic: true },
] as const;
