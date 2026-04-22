import { test as base, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * E2E auth fixtures for ProbaLab V2.
 *
 * Strategy — Option A (MSW / localStorage stub) chosen for the V1
 * cutover. Playwright specs run against `npm run dev`, where MSW is
 * already wired for the V2 hooks. The auth state is injected client-
 * side via a `__e2e_role__` localStorage key that the dev build reads
 * inside `useV2User` to override the Supabase session role.
 *
 * Rationale:
 *   - no Supabase creds required in CI (keeps the suite hermetic),
 *   - a single flag flips the entire gating tree (visitor / free /
 *     trial / premium / admin),
 *   - the shim lives strictly in dev bundles, so prod behaviour is
 *     untouched.
 *
 * Option B (real Supabase login via the login page) stays available
 * for smoke runs against staging — see `loginViaSupabase` helper below.
 */

export type E2ERole = 'visitor' | 'free' | 'trial' | 'premium' | 'admin';

/**
 * Sets the E2E role flag in `localStorage` for the next navigation.
 *
 * Playwright navigates the page first (so an origin is loaded), then
 * writes the flag, then reloads so the app boots with the desired role.
 */
export async function loginAs(page: Page, role: E2ERole): Promise<void> {
  // Ensure we have an origin so localStorage.setItem doesn't throw.
  const url = page.url();
  if (url === 'about:blank' || url === '') {
    await page.goto('/');
  }
  await page.evaluate((r) => {
    window.localStorage.setItem('__e2e_role__', r);
  }, role);
  await page.reload();
}

export async function loginAsPremium(page: Page): Promise<void> {
  await loginAs(page, 'premium');
}

export async function loginAsFree(page: Page): Promise<void> {
  await loginAs(page, 'free');
}

export async function loginAsTrial(page: Page): Promise<void> {
  await loginAs(page, 'trial');
}

/**
 * Option B — real Supabase login (kept for staging smoke runs).
 *
 * Uses the regular login page + Supabase session cookies. Requires:
 *   - E2E_PREMIUM_EMAIL
 *   - E2E_PREMIUM_PASSWORD
 * Not used by the default specs; exported so the fixture file is the
 * single source of truth for auth helpers.
 */
export async function loginViaSupabase(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/mot de passe/i).fill(password);
  await page.getByRole('button', { name: /se connecter|connexion/i }).click();
  await page.waitForURL((u) => !u.pathname.startsWith('/login'), {
    timeout: 15_000,
  });
}

type AuthFixtures = {
  premiumPage: Page;
};

/**
 * Extended `test` helper exposing a `premiumPage` fixture which
 * auto-logs the user in with the premium role.
 */
export const test = base.extend<AuthFixtures>({
  premiumPage: async ({ page }, use) => {
    await loginAsPremium(page);
    await use(page);
  },
});

export { expect };
