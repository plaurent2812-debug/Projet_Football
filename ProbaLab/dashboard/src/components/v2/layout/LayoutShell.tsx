import type { ReactNode } from 'react';
import type { UserRole } from '../../../types/v2/common';
import { HeaderV2 } from './HeaderV2';
import { BottomNavV2 } from './BottomNavV2';
import { TrialBannerContainer } from './TrialBannerContainer';

export interface LayoutShellProps {
  children: ReactNode;
  userRole?: UserRole;
  trialDaysLeft?: number;
  trialEndDate?: string;
}

export function LayoutShell({
  children,
  userRole = 'visitor',
  trialDaysLeft,
  trialEndDate,
}: LayoutShellProps) {
  return (
    <div
      data-testid="layout-shell"
      style={{
        minHeight: '100vh',
        background: 'var(--bg)',
        color: 'var(--text)',
        paddingBottom: 72,
      }}
    >
      <TrialBannerContainer
        userRole={userRole}
        trialDaysLeft={trialDaysLeft}
        trialEndDate={trialEndDate}
      />
      <HeaderV2 userRole={userRole} trialDaysLeft={trialDaysLeft} />
      <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: 'var(--space-4)' }}>
        {children}
      </div>
      <BottomNavV2 />
    </div>
  );
}

export default LayoutShell;
