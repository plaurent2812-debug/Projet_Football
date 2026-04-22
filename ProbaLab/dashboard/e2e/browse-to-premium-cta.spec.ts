import { test, expect } from '@playwright/test';

/**
 * E2E Spec 2 — Visitor browses matches and hits the Premium CTA.
 *
 * Flow:
 *   1. Landing at `/`.
 *   2. Nav to `/matchs`.
 *   3. Click into the first match card.
 *   4. Match detail shows a blurred / locked zone (visitor gating).
 *   5. Any CTA routing to `/premium` reaches the pricing + live
 *      track record sections.
 *
 * Selectors lean on the existing test-ids (`matches-v2-page`,
 * `match-row`, `lock-overlay`, `premium-v2-page`, `pricing-cards`,
 * `live-track-record`) rather than duplicating them under aliases.
 */
test.describe('Browse to premium CTA', () => {
  test('visitor reaches premium page with pricing and live track record', async ({
    page,
  }) => {
    await page.goto('/');
    await expect(page.getByTestId('home-landing')).toBeVisible();

    // Navigate to the matches list via the header link.
    await page
      .getByRole('link', { name: /^matchs$/i })
      .first()
      .click();
    await page.waitForURL(/\/matchs(\?|$)/, { timeout: 10_000 });
    await expect(page.getByTestId('matches-v2-page')).toBeVisible();

    // Click into the first available match row.
    const firstMatch = page.getByTestId('match-row').first();
    await expect(firstMatch).toBeVisible();
    await firstMatch.click();

    // Match detail with a visitor-gated (blurred) zone.
    await expect(page.getByTestId('match-detail-v2')).toBeVisible();
    await expect(page.getByTestId('lock-overlay').first()).toBeVisible();

    // Navigate to the premium page via any available link to /premium.
    await page.goto('/premium');
    await expect(page).toHaveURL(/\/premium$/);
    await expect(page.getByTestId('premium-v2-page')).toBeVisible();
    await expect(page.getByTestId('pricing-cards')).toBeVisible();
    await expect(page.getByTestId('live-track-record')).toBeVisible();
  });
});
