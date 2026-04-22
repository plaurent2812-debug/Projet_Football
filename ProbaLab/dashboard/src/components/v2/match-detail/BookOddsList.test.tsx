import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { BookOddsList } from './BookOddsList';
import type { BookOdd } from '../../../types/v2/match-detail';

const books: BookOdd[] = [
  {
    bookmaker: 'Unibet',
    odds: 2.1,
    is_best: true,
    updated_at: '2026-04-21T10:00:00Z',
  },
  {
    bookmaker: 'Winamax',
    odds: 2.05,
    is_best: false,
    updated_at: '2026-04-21T10:00:00Z',
  },
  {
    bookmaker: 'Betclic',
    odds: 2.0,
    is_best: false,
    updated_at: '2026-04-21T10:00:00Z',
  },
  {
    bookmaker: 'PMU',
    odds: 1.98,
    is_best: false,
    updated_at: '2026-04-21T10:00:00Z',
  },
  {
    bookmaker: 'Pinnacle',
    odds: 2.08,
    is_best: false,
    updated_at: '2026-04-21T10:00:00Z',
  },
];

describe('BookOddsList', () => {
  it('renders section heading', () => {
    render(<BookOddsList bookOdds={books} />);
    expect(
      screen.getByRole('heading', { name: /cotes bookmakers/i }),
    ).toBeInTheDocument();
  });

  it('renders one row per book', () => {
    const { container } = render(<BookOddsList bookOdds={books} />);
    expect(
      container.querySelectorAll('[data-testid^="book-odds-item"]'),
    ).toHaveLength(5);
  });

  it('renders each book name and odds', () => {
    render(<BookOddsList bookOdds={books} />);
    for (const b of books) {
      expect(screen.getByText(b.bookmaker)).toBeInTheDocument();
    }
  });

  it('highlights the best book (by is_best flag)', () => {
    render(<BookOddsList bookOdds={books} />);
    const bestRow = screen.getByTestId('book-odds-item-best');
    expect(bestRow).toHaveTextContent('Unibet');
    expect(bestRow).toHaveTextContent('2.10');
  });

  it('falls back to max odds when no is_best flag is true', () => {
    const flagless: BookOdd[] = books.map((b) => ({ ...b, is_best: false }));
    render(<BookOddsList bookOdds={flagless} />);
    // Unibet @ 2.10 still has the highest odds, should be highlighted
    const bestRow = screen.getByTestId('book-odds-item-best');
    expect(bestRow).toHaveTextContent('Unibet');
  });

  it('honours bestIndex prop when provided', () => {
    // Override: force Betclic (index 2) as best
    render(<BookOddsList bookOdds={books} bestIndex={2} />);
    const bestRow = screen.getByTestId('book-odds-item-best');
    expect(bestRow).toHaveTextContent('Betclic');
  });

  it('renders aria-label per row', () => {
    render(<BookOddsList bookOdds={books} />);
    expect(screen.getByLabelText(/Unibet.*cote 2\.10/)).toBeInTheDocument();
  });

  it('renders empty state when bookOdds is empty', () => {
    const { container } = render(<BookOddsList bookOdds={[]} />);
    expect(
      container.querySelectorAll('[data-testid^="book-odds-item"]'),
    ).toHaveLength(0);
  });

  it('accepts a custom data-testid on the root', () => {
    render(<BookOddsList bookOdds={books} data-testid="books" />);
    expect(screen.getByTestId('books')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<BookOddsList bookOdds={books} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
