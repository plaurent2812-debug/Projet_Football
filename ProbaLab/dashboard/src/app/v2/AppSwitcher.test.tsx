import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock AppLegacy to avoid loading the full legacy providers/routes.
vi.mock('../../AppLegacy', () => ({
  default: () => <div data-testid="legacy-root">Legacy Root</div>,
}));

// Mock AppV2 to keep this test focused on the switcher.
vi.mock('./AppV2', () => ({
  AppV2: () => <div data-testid="v2-root">V2 Root</div>,
}));

describe('App switcher', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('renders AppV2 when VITE_FRONTEND_V2 is true', async () => {
    vi.stubEnv('VITE_FRONTEND_V2', 'true');
    const { default: App } = await import('../../App');
    render(<App />);
    expect(screen.getByTestId('v2-root')).toBeInTheDocument();
  });

  it('renders AppLegacy when VITE_FRONTEND_V2 is not set', async () => {
    vi.stubEnv('VITE_FRONTEND_V2', '');
    const { default: App } = await import('../../App');
    render(<App />);
    expect(screen.getByTestId('legacy-root')).toBeInTheDocument();
  });
});
