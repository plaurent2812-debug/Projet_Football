import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MatchRow } from './MatchRow';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

function renderRow(match = mockMatches[0]) {
  return render(
    <MemoryRouter>
      <MatchRow match={match} />
    </MemoryRouter>,
  );
}

describe('MatchRow', () => {
  it('renders kickoff time, teams, and probabilities', () => {
    renderRow();
    expect(screen.getByText('PSG')).toBeInTheDocument();
    expect(screen.getByText('LEN')).toBeInTheDocument();
    expect(screen.getByText('58%')).toBeInTheDocument();
  });

  it('shows SAFE chip when signal present', () => {
    renderRow(mockMatches[0]);
    expect(screen.getByText(/SAFE/i)).toBeInTheDocument();
  });

  it('shows VALUE badge with edge when top value bet present', () => {
    renderRow(mockMatches[2]); // Inter vs Milan: edgePct 7.2
    expect(screen.getByText(/\+7\.2%/)).toBeInTheDocument();
  });

  it('exposes proba bar with comprehensive aria-label', () => {
    renderRow(mockMatches[0]);
    const bar = screen.getByRole('img', { name: /PSG 58%/ });
    expect(bar).toHaveAttribute('aria-label', 'PSG 58%, Nul 24%, LEN 18%');
  });

  it('is a link to match detail', async () => {
    const user = userEvent.setup();
    renderRow();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/matchs/fx-1');
    await user.click(link);
  });

  it('invokes onClick when provided', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <MemoryRouter>
        <MatchRow match={mockMatches[0]} onClick={onClick} />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole('link'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('accepts a data-testid prop on the root', () => {
    render(
      <MemoryRouter>
        <MatchRow match={mockMatches[0]} data-testid="my-row" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('my-row')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderRow();
    expect(await axe(container)).toHaveNoViolations();
  });
});
