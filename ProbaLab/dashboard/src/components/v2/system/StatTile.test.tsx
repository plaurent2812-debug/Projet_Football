import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { StatTile } from './StatTile';

describe('StatTile', () => {
  it('renders label and value', () => {
    render(<StatTile label="ROI 30J" value="+12.4%" />);
    expect(screen.getByText('ROI 30J')).toBeInTheDocument();
    expect(screen.getByText('+12.4%')).toBeInTheDocument();
  });

  it('renders delta when provided with positive tone', () => {
    render(<StatTile label="ROI" value="+12%" delta="+0.8 vs 7j" tone="positive" />);
    const delta = screen.getByText('+0.8 vs 7j');
    expect(delta).toBeInTheDocument();
    expect(delta).toHaveAttribute('data-tone', 'positive');
  });

  it('applies negative tone when specified', () => {
    render(<StatTile label="Drawdown" value="-4.2%" delta="-1.1 vs 7j" tone="negative" />);
    expect(screen.getByText('-1.1 vs 7j')).toHaveAttribute('data-tone', 'negative');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<StatTile label="ROI" value="+12%" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
