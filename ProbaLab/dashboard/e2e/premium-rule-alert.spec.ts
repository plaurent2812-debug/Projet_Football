import { test, expect } from './fixtures/auth';

/**
 * E2E Spec 3 — Premium user creates a notification rule.
 *
 * Flow:
 *   1. Auto-login via the `premiumPage` fixture (localStorage flag).
 *   2. Navigate to `/compte/notifications`.
 *   3. Open the RuleBuilder, fill the form (name, edge threshold,
 *      telegram + push channels), save.
 *   4. The new rule appears in the list after query invalidation.
 *
 * The MSW handlers used by the preview server echo the created rule back
 * on the list endpoint, so this spec runs fully against mocks. Persistence
 * across hard reloads belongs to backend contract tests, not this browser mock.
 */
test.describe('Premium — notification rule builder', () => {
  test('creates an edge-based rule with Telegram + Push channels', async ({
    premiumPage: page,
  }) => {
    await page.goto('/compte/notifications');
    await expect(page.getByTestId('notifications-tab')).toBeVisible();

    const ruleName = `E2E Edge Rule ${Date.now()}`;

    await page.getByTestId('new-rule-button').click();
    await expect(page.getByTestId('rule-form')).toBeVisible();

    await page.getByTestId('rule-name-input').fill(ruleName);

    // The default condition is `edge_min`; just overwrite the value.
    const edgeInput = page.getByTestId('rule-edge-input');
    await edgeInput.fill('8');

    await page.getByTestId('rule-channel-telegram').check();
    await page.getByTestId('rule-channel-push').check();

    await page.getByTestId('rule-save').click();

    // The rule modal closes and the new rule appears in the list.
    const item = page
      .getByTestId('rule-list-item')
      .filter({ hasText: ruleName });
    await expect(item).toBeVisible();

    // The default enabled toggle is on.
    await expect(item.getByRole('switch')).toBeChecked();

    // Hard reload persistence is owned by the real API; this mocked E2E only
    // verifies the create -> invalidate -> refetch path in the browser.
  });
});
