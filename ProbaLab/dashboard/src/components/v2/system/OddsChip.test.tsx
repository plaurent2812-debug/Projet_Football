import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { OddsChip } from './OddsChip';

describe('OddsChip', () => {
  it('renders odds with @ prefix and 2 decimals', () => {
    render(<OddsChip value={1.92} />);
    expect(screen.getByText('@1.92')).toBeInTheDocument();
  });

  it('pads to 2 decimals', () => {
    render(<OddsChip value={2} />);
    expect(screen.getByText('@2.00')).toBeInTheDocument();
  });

  it('applies highlight style when highlighted', () => {
    render(<OddsChip value={1.92} highlight />);
    expect(screen.getByText('@1.92')).toHaveAttribute('data-highlight', 'true');
  });

  it('uses aria-label with cote prefix', () => {
    render(<OddsChip value={1.92} />);
    expect(screen.getByLabelText(/cote 1\.92/i)).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<OddsChip value={1.92} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
