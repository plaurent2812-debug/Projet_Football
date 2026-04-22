import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { DateScroller } from './DateScroller';

expect.extend(toHaveNoViolations);

describe('DateScroller', () => {
  const FIXED = new Date('2026-04-21T12:00:00Z');
  beforeEach(() => {
    vi.setSystemTime(FIXED);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the 7 days from yesterday to +5 days', () => {
    render(<DateScroller value="2026-04-21" onChange={() => {}} />);
    // 7 date buttons
    const buttons = screen
      .getAllByRole('button')
      .filter((b) => b.getAttribute('data-role') === 'date');
    expect(buttons).toHaveLength(7);
  });

  it("highlights AUJOURD'HUI chip for today", () => {
    render(<DateScroller value="2026-04-21" onChange={() => {}} />);
    expect(screen.getByText(/AUJOURD'HUI/i)).toBeInTheDocument();
  });

  it('marks the selected date as pressed', () => {
    render(<DateScroller value="2026-04-21" onChange={() => {}} />);
    const today = screen.getByRole('button', { name: /AUJOURD'HUI/i });
    expect(today).toHaveAttribute('aria-pressed', 'true');
  });

  it('fires onChange on click with ISO YYYY-MM-DD', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DateScroller value="2026-04-21" onChange={onChange} />);
    // Click the "+1 day" button → 2026-04-22
    const buttons = screen
      .getAllByRole('button')
      .filter((b) => b.getAttribute('data-role') === 'date');
    // Order: yesterday, today, +1, +2, +3, +4, +5
    await user.click(buttons[2]);
    expect(onChange).toHaveBeenCalledWith('2026-04-22');
  });

  it('exposes previous/next chevron buttons', () => {
    render(<DateScroller value="2026-04-21" onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /précédent/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /suivant/i })).toBeInTheDocument();
  });

  it('accepts data-testid prop', () => {
    render(
      <DateScroller value="2026-04-21" onChange={() => {}} data-testid="date-scroller" />,
    );
    expect(screen.getByTestId('date-scroller')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      <DateScroller value="2026-04-21" onChange={() => {}} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
