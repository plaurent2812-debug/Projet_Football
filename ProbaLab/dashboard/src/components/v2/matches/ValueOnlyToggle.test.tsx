import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ValueOnlyToggle } from './ValueOnlyToggle';

expect.extend(toHaveNoViolations);

describe('ValueOnlyToggle', () => {
  it('renders an unpressed button when value is false', () => {
    render(<ValueOnlyToggle value={false} onChange={() => {}} />);
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'false');
  });

  it('marks pressed when value is true', () => {
    render(<ValueOnlyToggle value={true} onChange={() => {}} />);
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
  });

  it('flips value on click', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ValueOnlyToggle value={false} onChange={onChange} />);
    await user.click(screen.getByRole('button'));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it('displays Value only label', () => {
    render(<ValueOnlyToggle value={false} onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /value/i })).toBeInTheDocument();
  });

  it('accepts data-testid prop', () => {
    render(
      <ValueOnlyToggle
        value={false}
        onChange={() => {}}
        data-testid="value-only-toggle"
      />,
    );
    expect(screen.getByTestId('value-only-toggle')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<ValueOnlyToggle value onChange={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
