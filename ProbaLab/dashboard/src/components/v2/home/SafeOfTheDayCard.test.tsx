import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { SafeOfTheDayCard } from './SafeOfTheDayCard';
import { mockSafePick } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

function renderCard(props: Partial<React.ComponentProps<typeof SafeOfTheDayCard>> = {}) {
  return render(
    <MemoryRouter>
      <SafeOfTheDayCard data={mockSafePick} {...props} />
    </MemoryRouter>,
  );
}

describe('SafeOfTheDayCard', () => {
  it('displays the bet label, odd and justification', () => {
    renderCard();
    expect(screen.getByText('PSG gagne vs Lens')).toBeInTheDocument();
    expect(screen.getByText('1.85')).toBeInTheDocument();
    expect(screen.getByText(/xG moyen 2\.3/)).toBeInTheDocument();
  });

  it('shows probability as aria-labelled progress', () => {
    renderCard();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '58');
    expect(bar.getAttribute('aria-label')).toMatch(/58%/);
  });

  it('links to match detail page when clicked', async () => {
    const user = userEvent.setup();
    renderCard();
    const link = screen.getByRole('link', { name: /voir le match/i });
    expect(link).toHaveAttribute('href', '/matchs/fx-1');
    await user.click(link);
  });

  it('renders a FREE chip', () => {
    renderCard();
    expect(screen.getByText(/FREE/)).toBeInTheDocument();
  });

  it('renders the SAFE label with no emoji', () => {
    renderCard();
    expect(screen.getByText(/SAFE · PRONOSTIC DU JOUR/i)).toBeInTheDocument();
  });

  it('accepts a data-testid prop', () => {
    renderCard({ 'data-testid': 'safe-card' });
    expect(screen.getByTestId('safe-card')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderCard();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('renders an empty state when data is null', () => {
    render(<SafeOfTheDayCard data={null} />);
    expect(screen.getByText(/pas de pronostic safe/i)).toBeInTheDocument();
  });
});
