import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { BankrollSettingsModal } from './BankrollSettingsModal';

const mutateAsync = vi.fn().mockResolvedValue(undefined);
const useBankrollSettingsMock = vi.fn();

vi.mock('@/hooks/v2/useBankrollSettings', () => ({
  useBankrollSettings: () => useBankrollSettingsMock(),
  useUpdateBankrollSettings: () => ({ mutateAsync, isPending: false }),
}));

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  mutateAsync.mockClear();
  mutateAsync.mockResolvedValue(undefined);
  useBankrollSettingsMock.mockReset();
  useBankrollSettingsMock.mockReturnValue({
    data: { initialStake: 1000, kellyFraction: 0.25, stakeCapPct: 5 },
    isLoading: false,
  });
});

describe('BankrollSettingsModal', () => {
  it('does not render when open=false', () => {
    render(wrap(<BankrollSettingsModal open={false} onOpenChange={vi.fn()} />));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders an accessible dialog with the settings heading', () => {
    render(wrap(<BankrollSettingsModal open onOpenChange={vi.fn()} />));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(
      screen.getByRole('heading', { level: 2, name: /paramètres du bankroll/i }),
    ).toBeInTheDocument();
  });

  it('prefills fields with the values from useBankrollSettings', async () => {
    render(wrap(<BankrollSettingsModal open onOpenChange={vi.fn()} />));
    await waitFor(() => {
      expect(screen.getByLabelText(/mise initiale/i)).toHaveValue(1000);
    });
    expect(screen.getByLabelText(/fraction de kelly/i)).toHaveValue('0.25');
    // Slider value reflected in input
    expect(screen.getByLabelText(/plafond de mise/i)).toHaveValue('5');
  });

  it('renders a skeleton while loading', () => {
    useBankrollSettingsMock.mockReturnValue({ data: undefined, isLoading: true });
    render(wrap(<BankrollSettingsModal open onOpenChange={vi.fn()} />));
    expect(screen.getByTestId('bankroll-settings-skeleton')).toBeInTheDocument();
  });

  it('submits the form via useUpdateBankrollSettings and closes', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(wrap(<BankrollSettingsModal open onOpenChange={onOpenChange} />));

    const initial = screen.getByLabelText(/mise initiale/i);
    await user.clear(initial);
    await user.type(initial, '2000');

    const kelly = screen.getByLabelText(/fraction de kelly/i);
    await user.selectOptions(kelly, '0.5');

    await user.click(screen.getByRole('button', { name: /enregistrer/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledTimes(1);
    });
    const payload = mutateAsync.mock.calls[0][0];
    expect(payload.initialStake).toBe(2000);
    expect(payload.kellyFraction).toBe(0.5);
    expect(payload.stakeCapPct).toBe(5);

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('constrains the stake cap slider to the zod-approved 0.5–25 range', () => {
    render(wrap(<BankrollSettingsModal open onOpenChange={vi.fn()} />));
    const stakeCap = screen.getByLabelText(/plafond de mise/i) as HTMLInputElement;
    expect(stakeCap).toHaveAttribute('type', 'range');
    expect(stakeCap.min).toBe('0.5');
    expect(stakeCap.max).toBe('25');
  });

  it('displays a validation alert when initial stake is zero', async () => {
    const user = userEvent.setup();
    render(wrap(<BankrollSettingsModal open onOpenChange={vi.fn()} />));
    const initial = screen.getByLabelText(/mise initiale/i);
    await user.clear(initial);
    await user.type(initial, '0');
    await user.click(screen.getByRole('button', { name: /enregistrer/i }));
    await waitFor(() => {
      expect(screen.getByText(/mise initiale strictement positive/i)).toBeInTheDocument();
    });
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('cancels via the Annuler button without submitting', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(wrap(<BankrollSettingsModal open onOpenChange={onOpenChange} />));
    await user.click(screen.getByRole('button', { name: /annuler/i }));
    expect(onOpenChange).toHaveBeenLastCalledWith(false);
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      wrap(<BankrollSettingsModal open onOpenChange={vi.fn()} />),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
