import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { RuleChip } from './RuleChip';

describe('RuleChip', () => {
  it('renders with label variant', () => {
    render(<RuleChip variant="label" text="QUAND" />);
    expect(screen.getByText('QUAND')).toHaveAttribute('data-variant', 'label');
  });

  it('renders with condition variant', () => {
    render(<RuleChip variant="condition" text="edge ≥ 8%" />);
    expect(screen.getByText('edge ≥ 8%')).toHaveAttribute('data-variant', 'condition');
  });

  it('renders with action variant', () => {
    render(<RuleChip variant="action" text="Notifier Telegram" />);
    expect(screen.getByText('Notifier Telegram')).toHaveAttribute('data-variant', 'action');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<RuleChip variant="condition" text="edge ≥ 8%" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
