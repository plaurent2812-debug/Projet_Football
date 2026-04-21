import type { Bookmaker } from '../../../types/v2/common';
import { OddsChip } from './OddsChip';

export interface BookOddsRowProps {
  bookmakers: readonly Bookmaker[];
  'data-testid'?: string;
}

export function BookOddsRow({
  bookmakers,
  'data-testid': dataTestId = 'book-odds-row',
}: BookOddsRowProps) {
  if (bookmakers.length === 0) return null;
  const bestOdds = Math.max(...bookmakers.map((b) => b.odds));
  return (
    <ul
      data-testid={dataTestId}
      aria-label="Comparateur de cotes par bookmaker"
      style={{
        listStyle: 'none',
        padding: 0,
        margin: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
      }}
    >
      {bookmakers.map((b) => {
        const isBest = b.odds === bestOdds;
        const content = (
          <>
            <span style={{ flex: 1, fontWeight: isBest ? 600 : 400, color: 'var(--text)' }}>
              {b.name}
            </span>
            <OddsChip value={b.odds} highlight={isBest} />
          </>
        );
        return (
          <li
            key={b.name}
            data-testid={`book-row-${b.name}`}
            data-best={isBest}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
              padding: 'var(--space-2) var(--space-3)',
              background: isBest ? 'var(--primary-soft)' : 'var(--surface)',
              border: `1px solid ${isBest ? 'var(--primary)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-md)',
            }}
          >
            {b.url ? (
              <a
                href={b.url}
                rel="noopener noreferrer"
                target="_blank"
                aria-label={`Voir ${b.name}, cote ${b.odds.toFixed(2)}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  flex: 1,
                  color: 'inherit',
                }}
              >
                {content}
              </a>
            ) : (
              content
            )}
          </li>
        );
      })}
    </ul>
  );
}

export default BookOddsRow;
