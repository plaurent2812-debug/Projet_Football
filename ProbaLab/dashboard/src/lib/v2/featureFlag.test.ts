import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('isFrontendV2Enabled', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('returns false when VITE_FRONTEND_V2 is undefined', async () => {
    vi.stubEnv('VITE_FRONTEND_V2', '');
    const { isFrontendV2Enabled } = await import('./featureFlag');
    expect(isFrontendV2Enabled()).toBe(false);
  });

  it('returns true when VITE_FRONTEND_V2 is "true"', async () => {
    vi.stubEnv('VITE_FRONTEND_V2', 'true');
    const { isFrontendV2Enabled } = await import('./featureFlag');
    expect(isFrontendV2Enabled()).toBe(true);
  });

  it('returns false when VITE_FRONTEND_V2 is "false"', async () => {
    vi.stubEnv('VITE_FRONTEND_V2', 'false');
    const { isFrontendV2Enabled } = await import('./featureFlag');
    expect(isFrontendV2Enabled()).toBe(false);
  });

  it('returns false for any other value', async () => {
    vi.stubEnv('VITE_FRONTEND_V2', 'yes');
    const { isFrontendV2Enabled } = await import('./featureFlag');
    expect(isFrontendV2Enabled()).toBe(false);
  });
});
