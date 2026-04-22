import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { AddBetModal } from './AddBetModal';

const mutateAsync = vi.fn().mockResolvedValue({ id: 'bet-new' });

vi.mock('@/hooks/v2/useBankrollBets', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/v2/useBankrollBets')>(
    '@/hooks/v2/useBankrollBets',
  );
  return {
    ...actual,
    useAddBet: () => ({
      mutateAsync,
      isPending: false,
    }),
  };
});

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  mutateAsync.mockClear();
  mutateAsync.mockResolvedValue({ id: 'bet-new' });
});

describe('AddBetModal', () => {
  it('does not render when open=false', () => {
    render(wrap(<AddBetModal open={false} onOpenChange={vi.fn()} />));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders a dialog with accessible title when open', () => {
    render(wrap(<AddBetModal open onOpenChange={vi.fn()} />));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(
      screen.getByRole('heading', { level: 2, name: /ajouter un pari/i }),
    ).toBeInTheDocument();
  });

  it('renders all required form fields', () => {
    render(wrap(<AddBetModal open onOpenChange={vi.fn()} />));
    expect(screen.getByLabelText(/match/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/marché/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/sélection/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/cote/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mise/i)).toBeInTheDocument();
  });

  it('prefills fields when prefilledFixture is provided', () => {
    render(
      wrap(
        <AddBetModal
          open
          onOpenChange={vi.fn()}
          prefilledFixture={{
            fixture_id: 'fx-42',
            match_title: 'PSG - OM',
            market: '1X2',
            selection: 'Home',
            odds: 1.85,
          }}
        />,
      ),
    );
    expect(screen.getByLabelText(/match/i)).toHaveValue('PSG - OM');
    expect(screen.getByLabelText(/marché/i)).toHaveValue('1X2');
    expect(screen.getByLabelText(/sélection/i)).toHaveValue('Home');
    expect(screen.getByLabelText(/cote/i)).toHaveValue(1.85);
  });

  it('submits valid form data via useAddBet and closes on success', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(wrap(<AddBetModal open onOpenChange={onOpenChange} />));

    await user.type(screen.getByLabelText(/match/i), 'PSG - Lens');
    await user.selectOptions(screen.getByLabelText(/marché/i), '1X2');
    await user.type(screen.getByLabelText(/sélection/i), 'Home');
    await user.type(screen.getByLabelText(/cote/i), '1.9');
    await user.type(screen.getByLabelText(/mise/i), '20');

    await user.click(screen.getByRole('button', { name: /^ajouter$/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledTimes(1);
    });
    const payload = mutateAsync.mock.calls[0][0];
    expect(payload.match_title).toBe('PSG - Lens');
    expect(payload.market).toBe('1X2');
    expect(payload.selection).toBe('Home');
    expect(payload.odds).toBe(1.9);
    expect(payload.stake).toBe(20);
    expect(typeof payload.placed_at).toBe('string');

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('displays validation errors when required fields are missing', async () => {
    const user = userEvent.setup();
    render(wrap(<AddBetModal open onOpenChange={vi.fn()} />));
    await user.click(screen.getByRole('button', { name: /^ajouter$/i }));
    // Two of the string fields must flag an error; we don't assert
    // the exact wording here, but at least one alert must surface.
    await waitFor(() => {
      expect(screen.getAllByRole('alert').length).toBeGreaterThan(0);
    });
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('rejects non-numeric odds below 1.01', async () => {
    const user = userEvent.setup();
    render(wrap(<AddBetModal open onOpenChange={vi.fn()} />));
    await user.type(screen.getByLabelText(/match/i), 'PSG - Lens');
    await user.selectOptions(screen.getByLabelText(/marché/i), '1X2');
    await user.type(screen.getByLabelText(/sélection/i), 'Home');
    await user.type(screen.getByLabelText(/cote/i), '1');
    await user.type(screen.getByLabelText(/mise/i), '20');
    await user.click(screen.getByRole('button', { name: /^ajouter$/i }));
    await waitFor(() => {
      expect(screen.getByText(/cote minimale/i)).toBeInTheDocument();
    });
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('cancels via the Annuler button and does not submit', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(wrap(<AddBetModal open onOpenChange={onOpenChange} />));
    await user.click(screen.getByRole('button', { name: /annuler/i }));
    expect(onOpenChange).toHaveBeenLastCalledWith(false);
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('closes when Escape is pressed', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(wrap(<AddBetModal open onOpenChange={onOpenChange} />));
    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<AddBetModal open onOpenChange={vi.fn()} />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
