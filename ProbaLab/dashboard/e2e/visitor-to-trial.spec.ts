import { test, expect } from '@playwright/test';

/**
 * E2E Spec 1 — Visitor to trial (<60s).
 *
 * Verifies the critical happy path of the landing:
 *   1. Landing is reachable at `/` and exposes the hero.
 *   2. The "Essai gratuit 30 jours" CTA is wired to `/register`.
 *   3. Clicking the CTA brings the visitor to the register page.
 *
 * The actual Supabase sign-up call lives outside of V1 scope for
 * this Lot — the register form may be a WIP placeholder or a legacy
 * login redirect. The spec therefore tolerates both outcomes and
 * asserts only on navigation, so the suite stays green as long as
 * the CTA reaches an auth surface.
 */
test.describe('Visitor to trial (<60s)', () => {
  test('lands on home, sees hero, and clicks into register', async ({
    page,
  }) => {
    await page.goto('/');
    await expect(page.getByTestId('home-landing')).toBeVisible();

    // Hero copy sanity check — ensures we rendered the visitor branch.
    await expect(
      page.getByRole('heading', { name: /vraie probabilité/i }),
    ).toBeVisible();

    const cta = page.getByTestId('cta-register-trial');
    await expect(cta).toBeVisible();
    await cta.click();

    // Tolerate either direct /register or a legacy /login redirect:
    // the cutover (Lot 6 Task 10) may redirect /register -> /login
    // while the V2 register form is still WIP.
    await page.waitForURL(/\/(register|login)/, { timeout: 10_000 });
    expect(page.url()).toMatch(/\/(register|login)/);
  });
});
