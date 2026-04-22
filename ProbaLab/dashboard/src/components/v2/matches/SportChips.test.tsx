import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { SportChips } from './SportChips';

expect.extend(toHaveNoViolations);

describe('SportChips', () => {
  it('renders Tous / Football / NHL chips', () => {
    render(<SportChips value="all" onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /Tous/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Football/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /NHL/i })).toBeInTheDocument();
  });

  it('marks the selected chip as pressed', () => {
    render(<SportChips value="football" onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /Football/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: /Tous/i })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('fires onChange with the chosen sport', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SportChips value="all" onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /NHL/i }));
    expect(onChange).toHaveBeenCalledWith('nhl');
  });

  it('displays counts when provided', () => {
    render(
      <SportChips
        value="all"
        onChange={() => {}}
        counts={{ all: 12, football: 10, nhl: 2 }}
      />,
    );
    expect(screen.getByRole('button', { name: /Tous.*12/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Football.*10/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /NHL.*2/ })).toBeInTheDocument();
  });

  it('accepts a data-testid prop', () => {
    render(<SportChips value="all" onChange={() => {}} data-testid="sport-chips" />);
    expect(screen.getByTestId('sport-chips')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<SportChips value="all" onChange={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
