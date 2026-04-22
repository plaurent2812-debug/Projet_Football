import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ProbBar } from './ProbBar';

describe('ProbBar', () => {
  it('renders 3 segments', () => {
    render(<ProbBar home={0.58} draw={0.24} away={0.18} homeLabel="PSG" awayLabel="Lens" />);
    const bar = screen.getByRole('img', { name: /psg 58%/i });
    expect(bar).toBeInTheDocument();
    expect(bar.querySelectorAll('[data-segment]')).toHaveLength(3);
  });

  it('builds a complete aria-label', () => {
    render(<ProbBar home={0.58} draw={0.24} away={0.18} homeLabel="PSG" awayLabel="Lens" />);
    expect(screen.getByRole('img')).toHaveAttribute(
      'aria-label',
      expect.stringMatching(/PSG 58%.*Nul 24%.*Lens 18%/i)
    );
  });

  it('highlights the dominant segment', () => {
    render(<ProbBar home={0.58} draw={0.24} away={0.18} homeLabel="PSG" awayLabel="Lens" />);
    const dominant = screen.getByTestId('segment-home');
    expect(dominant).toHaveAttribute('data-dominant', 'true');
  });

  it('throws on probabilities not summing to ~1', () => {
    expect(() =>
      render(<ProbBar home={0.5} draw={0.2} away={0.1} homeLabel="A" awayLabel="B" />)
    ).toThrow(/sum/i);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <ProbBar home={0.58} draw={0.24} away={0.18} homeLabel="PSG" awayLabel="Lens" />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
