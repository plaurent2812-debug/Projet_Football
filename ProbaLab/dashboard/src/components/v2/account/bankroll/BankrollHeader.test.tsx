import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { BankrollHeader } from './BankrollHeader';

// Stub the heavy modal dependencies — we only want to assert that they
// become visible in response to header button clicks.
vi.mock('./AddBetModal', () => ({
  AddBetModal: ({
    open,
    onOpenChange,
  }: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
  }) =>
    open ? (
      <div role="dialog" data-testid="mock-add-bet-modal">
        mock add bet modal
        <button onClick={() => onOpenChange(false)}>close-add</button>
      </div>
    ) : null,
}));

vi.mock('./BankrollSettingsModal', () => ({
  BankrollSettingsModal: ({
    open,
    onOpenChange,
  }: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
  }) =>
    open ? (
      <div role="dialog" data-testid="mock-bankroll-settings-modal">
        mock settings modal
        <button onClick={() => onOpenChange(false)}>close-settings</button>
      </div>
    ) : null,
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

describe('BankrollHeader', () => {
  it('renders the page heading', () => {
    render(wrap(<BankrollHeader />));
    expect(
      screen.getByRole('heading', { level: 1, name: /suivi de mes paris/i }),
    ).toBeInTheDocument();
  });

  it('renders a settings button and an add-bet primary button', () => {
    render(wrap(<BankrollHeader />));
    expect(
      screen.getByRole('button', { name: /paramètres/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /ajouter un pari/i }),
    ).toBeInTheDocument();
  });

  it('opens the AddBetModal when the primary button is clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<BankrollHeader />));
    expect(screen.queryByTestId('mock-add-bet-modal')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /ajouter un pari/i }));
    expect(screen.getByTestId('mock-add-bet-modal')).toBeInTheDocument();
  });

  it('opens the BankrollSettingsModal when the Paramètres button is clicked', async () => {
    const user = userEvent.setup();
    render(wrap(<BankrollHeader />));
    expect(
      screen.queryByTestId('mock-bankroll-settings-modal'),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /paramètres/i }));
    expect(
      screen.getByTestId('mock-bankroll-settings-modal'),
    ).toBeInTheDocument();
  });

  it('closes modals when their onOpenChange(false) fires', async () => {
    const user = userEvent.setup();
    render(wrap(<BankrollHeader />));
    await user.click(screen.getByRole('button', { name: /ajouter un pari/i }));
    expect(screen.getByTestId('mock-add-bet-modal')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'close-add' }));
    expect(screen.queryByTestId('mock-add-bet-modal')).not.toBeInTheDocument();
  });

  it('exposes a data-testid on the root', () => {
    render(wrap(<BankrollHeader data-testid="custom-header" />));
    expect(screen.getByTestId('custom-header')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<BankrollHeader />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
