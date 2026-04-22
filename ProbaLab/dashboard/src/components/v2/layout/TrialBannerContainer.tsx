import type { UserRole } from '../../../types/v2/common';
import { TrialBanner } from '../system/TrialBanner';

export interface TrialBannerContainerProps {
  userRole: UserRole;
  trialDaysLeft?: number;
  trialEndDate?: string;
}

export function TrialBannerContainer({ userRole, trialDaysLeft, trialEndDate }: TrialBannerContainerProps) {
  if (userRole !== 'trial' || typeof trialDaysLeft !== 'number') {
    return null;
  }
  return <TrialBanner daysLeft={trialDaysLeft} endDate={trialEndDate} />;
}

export default TrialBannerContainer;
