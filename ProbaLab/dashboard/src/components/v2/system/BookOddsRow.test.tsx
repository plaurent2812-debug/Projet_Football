import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { BookOddsRow } from './BookOddsRow';

describe('BookOddsRow', () => {
  const books = [
    { name: 'Pinnacle', odds: 1.92 },
    { name: 'Bet365', odds: 1.95 },
    { name: 'Unibet', odds: 1.9 },
  ];

  it('renders one row per bookmaker', () => {
    render(<BookOddsRow bookmakers={books} />);
    expect(screen.getByText('Pinnacle')).toBeInTheDocument();
    expect(screen.getByText('Bet365')).toBeInTheDocument();
    expect(screen.getByText('Unibet')).toBeInTheDocument();
  });

  it('highlights the bookmaker with the best price', () => {
    render(<BookOddsRow bookmakers={books} />);
    const best = screen.getByTestId('book-row-Bet365');
    expect(best).toHaveAttribute('data-best', 'true');
  });

  it('renders a link when url is provided', () => {
    render(
      <BookOddsRow
        bookmakers={[{ name: 'Bet365', odds: 1.95, url: 'https://bet365.com' }]}
      />,
    );
    const link = screen.getByRole('link', { name: /bet365/i });
    expect(link).toHaveAttribute('href', 'https://bet365.com');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<BookOddsRow bookmakers={books} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
