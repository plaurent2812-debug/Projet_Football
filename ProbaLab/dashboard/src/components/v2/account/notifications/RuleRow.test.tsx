import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { RuleRow } from './RuleRow';
import type { NotificationRule } from '@/lib/v2/schemas/rules';

const toggleMutate = vi.fn();

vi.mock('@/hooks/v2/useNotificationRules', async () => {
  const actual = await vi.importActual<
    typeof import('@/hooks/v2/useNotificationRules')
  >('@/hooks/v2/useNotificationRules');
  return {
    ...actual,
    useToggleRule: () => ({
      mutate: toggleMutate,
      mutateAsync: vi.fn().mockResolvedValue({}),
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
  toggleMutate.mockClear();
});

const VALUE_RULE: NotificationRule = {
  id: 'rule-001',
  name: 'Value bets haut edge',
  conditions: [{ type: 'edge_min', value: 8 }],
  logic: 'AND',
  channels: ['email', 'telegram'],
  action: { notify: true, pauseSuggestion: false },
  enabled: true,
};

const BANKROLL_RULE: NotificationRule = {
  id: 'rule-003',
  name: 'Drawdown critique',
  conditions: [{ type: 'bankroll_drawdown', value: 10 }],
  logic: 'AND',
  channels: ['email', 'telegram', 'push'],
  action: { notify: true, pauseSuggestion: true },
  enabled: false,
};

const SAFE_RULE: NotificationRule = {
  id: 'rule-002',
  name: 'Safe du jour kick-off',
  conditions: [{ type: 'kickoff_within', value: 2 }],
  logic: 'AND',
  channels: ['push'],
  action: { notify: true, pauseSuggestion: false },
  enabled: true,
};

describe('RuleRow', () => {
  it('renders the rule name', () => {
    render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    expect(screen.getByText('Value bets haut edge')).toBeInTheDocument();
  });

  it('renders QUAND / ET / NOTIFIER RuleChip labels', () => {
    render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    // Label chips are uppercase — QUAND / NOTIFIER at minimum.
    expect(screen.getByText('QUAND')).toBeInTheDocument();
    expect(screen.getByText('NOTIFIER')).toBeInTheDocument();
  });

  it('renders ET chip only when the rule has more than one condition', () => {
    render(
      wrap(
        <RuleRow
          rule={{
            ...VALUE_RULE,
            conditions: [
              { type: 'edge_min', value: 8 },
              { type: 'confidence', value: 'HIGH' },
            ],
          }}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    expect(screen.getByText('ET')).toBeInTheDocument();
  });

  it('renders channel chips for each channel', () => {
    render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    expect(screen.getByText(/telegram/i)).toBeInTheDocument();
    expect(screen.getByText(/email/i)).toBeInTheDocument();
  });

  it('reflects enabled state on the switch via aria-checked', () => {
    render(
      wrap(
        <RuleRow
          rule={BANKROLL_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    const sw = screen.getByRole('switch', {
      name: /activer drawdown critique/i,
    });
    expect(sw).toHaveAttribute('aria-checked', 'false');
  });

  it('calls useToggleRule when the switch is clicked', async () => {
    const user = userEvent.setup();
    render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    await user.click(
      screen.getByRole('switch', { name: /activer value bets haut edge/i }),
    );
    expect(toggleMutate).toHaveBeenCalledWith(false);
  });

  it('opens the kebab menu and fires onEdit', async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={onEdit}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    await user.click(
      screen.getByRole('button', { name: /menu value bets haut edge/i }),
    );
    await user.click(screen.getByRole('menuitem', { name: /modifier/i }));
    expect(onEdit).toHaveBeenCalledWith(VALUE_RULE);
  });

  it('opens the kebab menu and fires onDeleteRequest', async () => {
    const user = userEvent.setup();
    const onDeleteRequest = vi.fn();
    render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={onDeleteRequest}
        />,
      ),
    );
    await user.click(
      screen.getByRole('button', { name: /menu value bets haut edge/i }),
    );
    await user.click(screen.getByRole('menuitem', { name: /supprimer/i }));
    expect(onDeleteRequest).toHaveBeenCalledWith(VALUE_RULE);
  });

  it('renders a distinct icon for bankroll drawdown rules', () => {
    render(
      wrap(
        <RuleRow
          rule={BANKROLL_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    // Wallet icon is surfaced via data-lucide / aria-label on the wrapper.
    const icon = screen.getByTestId('rule-row-icon');
    expect(icon.getAttribute('data-icon')).toBe('wallet');
  });

  it('renders a Star icon for safe kick-off rules', () => {
    render(
      wrap(
        <RuleRow
          rule={SAFE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    const icon = screen.getByTestId('rule-row-icon');
    expect(icon.getAttribute('data-icon')).toBe('star');
  });

  it('renders a Zap icon for value bets (edge_min) rules', () => {
    render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    const icon = screen.getByTestId('rule-row-icon');
    expect(icon.getAttribute('data-icon')).toBe('zap');
  });

  it('exposes a data-testid on the row', () => {
    render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
          data-testid="my-row"
        />,
      ),
    );
    expect(screen.getByTestId('my-row')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      wrap(
        <RuleRow
          rule={VALUE_RULE}
          onEdit={vi.fn()}
          onDeleteRequest={vi.fn()}
        />,
      ),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
