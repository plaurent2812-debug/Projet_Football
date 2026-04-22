import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ValueBadge } from './ValueBadge';

describe('ValueBadge', () => {
  it('formats edge as percentage with one decimal', () => {
    render(<ValueBadge edge={0.072} />);
    expect(screen.getByText(/\+7\.2%/)).toBeInTheDocument();
  });

  it('uses aria-label with VALUE prefix', () => {
    render(<ValueBadge edge={0.072} />);
    expect(screen.getByLabelText(/value bet \+7\.2%/i)).toBeInTheDocument();
  });

  it('rounds to one decimal', () => {
    render(<ValueBadge edge={0.05678} />);
    expect(screen.getByText(/\+5\.7%/)).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ValueBadge edge={0.072} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
