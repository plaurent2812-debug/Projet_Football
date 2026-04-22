import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { RuleBuilderModal } from './RuleBuilderModal';
import type { NotificationRule } from '@/lib/v2/schemas/rules';

const createMutateAsync = vi.fn().mockResolvedValue({ id: 'rule-new' });
const updateMutateAsync = vi.fn().mockResolvedValue({ id: 'rule-001' });

vi.mock('@/hooks/v2/useNotificationRules', async () => {
  const actual = await vi.importActual<
    typeof import('@/hooks/v2/useNotificationRules')
  >('@/hooks/v2/useNotificationRules');
  return {
    ...actual,
    useCreateRule: () => ({
      mutateAsync: createMutateAsync,
      isPending: false,
    }),
    useUpdateRule: () => ({
      mutateAsync: updateMutateAsync,
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
  createMutateAsync.mockClear();
  updateMutateAsync.mockClear();
  createMutateAsync.mockResolvedValue({ id: 'rule-new' });
  updateMutateAsync.mockResolvedValue({ id: 'rule-001' });
});

const EXISTING_RULE: NotificationRule = {
  id: 'rule-001',
  name: 'Value bets haut edge',
  conditions: [
    { type: 'edge_min', value: 8 },
    { type: 'confidence', value: 'HIGH' },
  ],
  logic: 'AND',
  channels: ['email', 'telegram'],
  action: { notify: true, pauseSuggestion: false },
  enabled: true,
};

describe('RuleBuilderModal', () => {
  it('does not render when open=false', () => {
    render(wrap(<RuleBuilderModal open={false} onOpenChange={vi.fn()} />));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders a dialog with create title when no initialRule', () => {
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(
      screen.getByRole('heading', { level: 2, name: /nouvelle règle/i }),
    ).toBeInTheDocument();
  });

  it('renders a dialog with edit title when initialRule provided', () => {
    render(
      wrap(
        <RuleBuilderModal
          open
          onOpenChange={vi.fn()}
          initialRule={EXISTING_RULE}
        />,
      ),
    );
    expect(
      screen.getByRole('heading', { level: 2, name: /modifier la règle/i }),
    ).toBeInTheDocument();
  });

  it('starts with a single empty condition row in create mode', () => {
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    expect(screen.getAllByTestId('rule-condition-row')).toHaveLength(1);
  });

  it('prefills name, conditions, channels, action and logic in edit mode', () => {
    render(
      wrap(
        <RuleBuilderModal
          open
          onOpenChange={vi.fn()}
          initialRule={EXISTING_RULE}
        />,
      ),
    );
    expect(screen.getByLabelText(/nom de la règle/i)).toHaveValue(
      'Value bets haut edge',
    );
    expect(screen.getAllByTestId('rule-condition-row')).toHaveLength(2);
    expect(screen.getByLabelText(/email/i)).toBeChecked();
    expect(screen.getByLabelText(/telegram/i)).toBeChecked();
    expect(screen.getByLabelText(/push/i)).not.toBeChecked();
  });

  it('adds conditions up to 3 then disables add button', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    const addBtn = screen.getByRole('button', {
      name: /ajouter une condition/i,
    });
    await user.click(addBtn);
    await user.click(addBtn);
    expect(screen.getAllByTestId('rule-condition-row')).toHaveLength(3);
    expect(addBtn).toBeDisabled();
  });

  it('removes a condition when clicking the remove button', async () => {
    const user = userEvent.setup();
    render(
      wrap(
        <RuleBuilderModal
          open
          onOpenChange={vi.fn()}
          initialRule={EXISTING_RULE}
        />,
      ),
    );
    expect(screen.getAllByTestId('rule-condition-row')).toHaveLength(2);
    const removeButtons = screen.getAllByRole('button', {
      name: /supprimer condition/i,
    });
    await user.click(removeButtons[0]);
    expect(screen.getAllByTestId('rule-condition-row')).toHaveLength(1);
  });

  it('does not show the remove button when only 1 condition', () => {
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    expect(
      screen.queryByRole('button', { name: /supprimer condition/i }),
    ).not.toBeInTheDocument();
  });

  it('shows AND/OR toggle only when more than one condition', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    expect(screen.queryByRole('button', { name: 'AND' })).not.toBeInTheDocument();
    await user.click(
      screen.getByRole('button', { name: /ajouter une condition/i }),
    );
    expect(screen.getByRole('button', { name: 'AND' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'OR' })).toBeInTheDocument();
  });

  it('toggles AND/OR logic via aria-pressed', async () => {
    const user = userEvent.setup();
    render(
      wrap(
        <RuleBuilderModal
          open
          onOpenChange={vi.fn()}
          initialRule={EXISTING_RULE}
        />,
      ),
    );
    const andBtn = screen.getByRole('button', { name: 'AND' });
    const orBtn = screen.getByRole('button', { name: 'OR' });
    expect(andBtn).toHaveAttribute('aria-pressed', 'true');
    expect(orBtn).toHaveAttribute('aria-pressed', 'false');
    await user.click(orBtn);
    expect(orBtn).toHaveAttribute('aria-pressed', 'true');
    expect(andBtn).toHaveAttribute('aria-pressed', 'false');
  });

  it('renders a pauseSuggestion checkbox', () => {
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    expect(
      screen.getByLabelText(/suggérer pause paris/i),
    ).toBeInTheDocument();
  });

  it('renders an enabled switch', () => {
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    const sw = screen.getByRole('switch', { name: /activer la règle/i });
    expect(sw).toBeInTheDocument();
    expect(sw).toHaveAttribute('aria-checked', 'true');
  });

  it('submits a valid rule in create mode and calls useCreateRule', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const onSaved = vi.fn();
    render(
      wrap(
        <RuleBuilderModal
          open
          onOpenChange={onOpenChange}
          onSaved={onSaved}
        />,
      ),
    );

    await user.type(screen.getByLabelText(/nom de la règle/i), 'Value L1');
    // The default condition is edge_min — set its value to 5.
    const edgeInput = screen.getByLabelText(/valeur condition 1/i);
    await user.clear(edgeInput);
    await user.type(edgeInput, '5');
    await user.click(screen.getByLabelText(/email/i));

    await user.click(
      screen.getByRole('button', { name: /enregistrer la règle/i }),
    );

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledTimes(1);
    });
    const payload = createMutateAsync.mock.calls[0][0];
    expect(payload.name).toBe('Value L1');
    expect(payload.conditions).toEqual([{ type: 'edge_min', value: 5 }]);
    expect(payload.channels).toEqual(['email']);
    expect(payload.logic).toBe('AND');
    expect(payload.action).toEqual({ notify: true, pauseSuggestion: false });
    expect(payload.enabled).toBe(true);

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
      expect(onSaved).toHaveBeenCalledTimes(1);
    });
  });

  it('submits an edit with useUpdateRule when initialRule.id is provided', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      wrap(
        <RuleBuilderModal
          open
          onOpenChange={onOpenChange}
          initialRule={EXISTING_RULE}
        />,
      ),
    );

    await user.click(
      screen.getByRole('button', { name: /enregistrer la règle/i }),
    );

    await waitFor(() => {
      expect(updateMutateAsync).toHaveBeenCalledTimes(1);
    });
    const payload = updateMutateAsync.mock.calls[0][0];
    expect(payload.id).toBe('rule-001');
    expect(payload.name).toBe('Value bets haut edge');
    expect(payload.conditions).toHaveLength(2);
    expect(payload.channels).toContain('email');

    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
    expect(createMutateAsync).not.toHaveBeenCalled();
  });

  it('surfaces a validation error when name is empty', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    // Add email so only name is missing.
    await user.click(screen.getByLabelText(/email/i));
    await user.click(
      screen.getByRole('button', { name: /enregistrer la règle/i }),
    );
    await waitFor(() => {
      expect(screen.getByText(/nom requis/i)).toBeInTheDocument();
    });
    expect(createMutateAsync).not.toHaveBeenCalled();
  });

  it('surfaces a validation error when no channel is selected', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    await user.type(screen.getByLabelText(/nom de la règle/i), 'Ma règle');
    await user.click(
      screen.getByRole('button', { name: /enregistrer la règle/i }),
    );
    await waitFor(() => {
      expect(screen.getByText(/au moins 1 canal/i)).toBeInTheDocument();
    });
    expect(createMutateAsync).not.toHaveBeenCalled();
  });

  it('includes pauseSuggestion when its checkbox is checked', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    await user.type(screen.getByLabelText(/nom de la règle/i), 'R');
    await user.click(screen.getByLabelText(/email/i));
    await user.click(screen.getByLabelText(/suggérer pause paris/i));
    await user.click(
      screen.getByRole('button', { name: /enregistrer la règle/i }),
    );
    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalled();
    });
    const payload = createMutateAsync.mock.calls[0][0];
    expect(payload.action.pauseSuggestion).toBe(true);
  });

  it('changes condition type and updates the value input shape', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    const typeSelect = screen.getByLabelText(/type condition 1/i);
    await user.selectOptions(typeSelect, 'sport');
    // Now value should be a radio group for football/nhl.
    expect(screen.getByLabelText(/football/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/nhl/i)).toBeInTheDocument();
  });

  it('supports league_in with multi-select checkboxes', async () => {
    const user = userEvent.setup();
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    const typeSelect = screen.getByLabelText(/type condition 1/i);
    await user.selectOptions(typeSelect, 'league_in');
    // At least one league checkbox renders.
    expect(screen.getByLabelText('L1')).toBeInTheDocument();
    expect(screen.getByLabelText('PL')).toBeInTheDocument();
  });

  it('cancels via the Annuler button and does not submit', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(wrap(<RuleBuilderModal open onOpenChange={onOpenChange} />));
    await user.click(screen.getByRole('button', { name: /annuler/i }));
    expect(onOpenChange).toHaveBeenLastCalledWith(false);
    expect(createMutateAsync).not.toHaveBeenCalled();
  });

  it('surfaces an API error when the mutation rejects', async () => {
    const user = userEvent.setup();
    createMutateAsync.mockRejectedValueOnce(new Error('API boom'));
    render(wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />));
    await user.type(screen.getByLabelText(/nom de la règle/i), 'Ma règle');
    await user.click(screen.getByLabelText(/email/i));
    await user.click(
      screen.getByRole('button', { name: /enregistrer la règle/i }),
    );
    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toMatch(/api boom/i);
    });
  });

  it('has no axe violations', async () => {
    const { container } = render(
      wrap(<RuleBuilderModal open onOpenChange={vi.fn()} />),
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('exposes a custom data-testid on the dialog', () => {
    render(
      wrap(
        <RuleBuilderModal
          open
          onOpenChange={vi.fn()}
          data-testid="my-rule-modal"
        />,
      ),
    );
    expect(screen.getByTestId('my-rule-modal')).toBeInTheDocument();
  });
});
