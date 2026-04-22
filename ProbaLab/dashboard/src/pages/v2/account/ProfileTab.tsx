import { ProfileForm } from '@/components/v2/account/profile/ProfileForm';

/**
 * "Profil" tab page — thin wrapper around {@link ProfileForm}.
 *
 * Kept separate from the form so the route element stays a page-level
 * component and the form remains reusable (tests, Storybook).
 */
export function ProfileTab() {
  return (
    <div data-testid="profile-tab">
      <ProfileForm />
    </div>
  );
}

export default ProfileTab;
