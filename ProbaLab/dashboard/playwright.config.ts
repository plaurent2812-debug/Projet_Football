import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration — ProbaLab V2 E2E suite.
 *
 * Environment variables:
 *   - `E2E_FRONTEND_URL` (default: http://localhost:5173)
 *   - `E2E_BACKEND_URL`  (default: http://localhost:8000)
 *
 * Dev workflow: run `npm run dev` in a separate terminal (MSW-enabled),
 * then `npm run e2e`. In CI we spin up `vite preview` with the V2 flag.
 */
const FRONTEND_URL = process.env.E2E_FRONTEND_URL ?? 'http://localhost:5173';
const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://localhost:8000';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 2,
  reporter: process.env.CI
    ? [['github'], ['html', { open: 'never' }]]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: FRONTEND_URL,
    headless: true,
    viewport: { width: 1280, height: 800 },
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    extraHTTPHeaders: {
      'x-e2e-backend': BACKEND_URL,
    },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: process.env.CI
    ? [
        {
          command: 'npm run preview -- --port 5173',
          port: 5173,
          reuseExistingServer: false,
          timeout: 120_000,
          env: { VITE_FRONTEND_V2: 'true' },
        },
      ]
    : undefined,
});
