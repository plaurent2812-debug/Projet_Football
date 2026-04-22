import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { PushPermissionButton } from './PushPermissionButton';

// We mock the push hook to control each of the four surface states.
const mockEnable = vi.fn().mockResolvedValue(undefined);
const mockDisable = vi.fn().mockResolvedValue(undefined);
const hookState = {
  permission: 'default' as NotificationPermission,
  isSupported: true,
};

vi.mock('@/hooks/v2/useEnablePush', () => ({
  useEnablePush: () => ({
    permission: hookState.permission,
    isSupported: hookState.isSupported,
    enable: mockEnable,
    disable: mockDisable,
  }),
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  mockEnable.mockReset().mockResolvedValue(undefined);
  mockDisable.mockReset().mockResolvedValue(undefined);
  hookState.permission = 'default';
  hookState.isSupported = true;
});

afterEach(() => {
  hookState.permission = 'default';
  hookState.isSupported = true;
});

describe('PushPermissionButton', () => {
  it('shows "Non disponible" when unsupported', () => {
    hookState.isSupported = false;
    render(wrap(<PushPermissionButton push={{ subscribed: false, devices: 0 }} />));
    expect(screen.getByText(/non disponible/i)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('shows the Activer button when permission=default', () => {
    render(wrap(<PushPermissionButton push={{ subscribed: false, devices: 0 }} />));
    expect(
      screen.getByRole('button', { name: /activer les notifications push/i }),
    ).toBeInTheDocument();
  });

  it('calls enable() when the Activer button is clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<PushPermissionButton push={{ subscribed: false, devices: 0 }} />));
    await user.click(
      screen.getByRole('button', { name: /activer les notifications push/i }),
    );
    expect(mockEnable).toHaveBeenCalledTimes(1);
  });

  it('shows Activé + device count + Désactiver when granted and subscribed', () => {
    hookState.permission = 'granted';
    render(wrap(<PushPermissionButton push={{ subscribed: true, devices: 2 }} />));
    expect(screen.getByText(/activé/i)).toBeInTheDocument();
    expect(screen.getByText(/2 appareil/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /désactiver/i }),
    ).toBeInTheDocument();
  });

  it('calls disable() when Désactiver is clicked', async () => {
    hookState.permission = 'granted';
    const user = userEvent.setup();
    render(wrap(<PushPermissionButton push={{ subscribed: true, devices: 1 }} />));
    await user.click(screen.getByRole('button', { name: /désactiver/i }));
    expect(mockDisable).toHaveBeenCalledTimes(1);
  });

  it('shows a blocked message when permission=denied', () => {
    hookState.permission = 'denied';
    render(wrap(<PushPermissionButton push={{ subscribed: false, devices: 0 }} />));
    expect(screen.getByText(/bloqué/i)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('surfaces an error when enable() throws', async () => {
    mockEnable.mockRejectedValueOnce(new Error('boom'));
    const user = userEvent.setup();
    render(wrap(<PushPermissionButton push={{ subscribed: false, devices: 0 }} />));
    await user.click(
      screen.getByRole('button', { name: /activer les notifications push/i }),
    );
    await screen.findByRole('alert');
    expect(screen.getByRole('alert').textContent).toMatch(/erreur/i);
  });

  it('exposes a data-testid on the root', () => {
    render(
      wrap(
        <PushPermissionButton
          push={{ subscribed: false, devices: 0 }}
          data-testid="custom-push"
        />,
      ),
    );
    expect(screen.getByTestId('custom-push')).toBeInTheDocument();
  });

  it('has no axe violations in granted state', async () => {
    hookState.permission = 'granted';
    const { container } = render(
      wrap(<PushPermissionButton push={{ subscribed: true, devices: 1 }} />),
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no axe violations in denied state', async () => {
    hookState.permission = 'denied';
    const { container } = render(
      wrap(<PushPermissionButton push={{ subscribed: false, devices: 0 }} />),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
