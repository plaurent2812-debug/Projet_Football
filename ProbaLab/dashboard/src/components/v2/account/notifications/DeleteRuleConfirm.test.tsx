import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { DeleteRuleConfirm } from './DeleteRuleConfirm';
import type { NotificationRule } from '@/lib/v2/schemas/rules';

const deleteMutateAsync = vi.fn().mockResolvedValue(undefined);

vi.mock('@/hooks/v2/useNotificationRules', async () => {
  const actual = await vi.importActual<
    typeof import('@/hooks/v2/useNotificationRules')
  >('@/hooks/v2/useNotificationRules');
  return {
    ...actual,
    useDeleteRule: () => ({
      mutateAsync: deleteMutateAsync,
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
  deleteMutateAsync.mockClear();
  deleteMutateAsync.mockResolvedValue(undefined);
});

const RULE: NotificationRule = {
  id: 'rule-001',
  name: 'Value bets haut edge',
  conditions: [{ type: 'edge_min', value: 8 }],
  logic: 'AND',
  channels: ['email'],
  action: { notify: true, pauseSuggestion: false },
  enabled: true,
};

describe('DeleteRuleConfirm', () => {
  it('does not render when rule is null', () => {
    render(wrap(<DeleteRuleConfirm rule={null} onOpenChange={vi.fn()} />));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders a dialog with the rule name when a rule is provided', () => {
    render(wrap(<DeleteRuleConfirm rule={RULE} onOpenChange={vi.fn()} />));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /supprimer la règle/i }),
    ).toBeInTheDocument();
    // The name is surfaced inside the body copy.
    expect(screen.getByText(/value bets haut edge/i)).toBeInTheDocument();
  });

  it('calls useDeleteRule on confirm and closes the modal', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      wrap(<DeleteRuleConfirm rule={RULE} onOpenChange={onOpenChange} />),
    );
    await user.click(screen.getByRole('button', { name: /supprimer/i }));
    await waitFor(() => {
      expect(deleteMutateAsync).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('closes without deleting when clicking Annuler', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      wrap(<DeleteRuleConfirm rule={RULE} onOpenChange={onOpenChange} />),
    );
    await user.click(screen.getByRole('button', { name: /annuler/i }));
    expect(onOpenChange).toHaveBeenLastCalledWith(false);
    expect(deleteMutateAsync).not.toHaveBeenCalled();
  });

  it('surfaces an API error when the mutation rejects', async () => {
    const user = userEvent.setup();
    deleteMutateAsync.mockRejectedValueOnce(new Error('Delete boom'));
    render(
      wrap(<DeleteRuleConfirm rule={RULE} onOpenChange={vi.fn()} />),
    );
    await user.click(screen.getByRole('button', { name: /supprimer/i }));
    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toMatch(/delete boom/i);
    });
  });

  it('closes when pressing Escape', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      wrap(<DeleteRuleConfirm rule={RULE} onOpenChange={onOpenChange} />),
    );
    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('exposes a data-testid on the dialog', () => {
    render(
      wrap(
        <DeleteRuleConfirm
          rule={RULE}
          onOpenChange={vi.fn()}
          data-testid="my-delete-confirm"
        />,
      ),
    );
    expect(screen.getByTestId('my-delete-confirm')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      wrap(<DeleteRuleConfirm rule={RULE} onOpenChange={vi.fn()} />),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
