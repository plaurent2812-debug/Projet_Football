import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { TransparencyGuarantee } from './TransparencyGuarantee';

describe('TransparencyGuarantee', () => {
  it('renders the transparency guarantee copy with CLV 30j rule', () => {
    render(<TransparencyGuarantee />);
    expect(screen.getByText(/garantie transparence/i)).toBeInTheDocument();
    // Copy: "Si le CLV 30 jours devient négatif…" — match robustly.
    expect(screen.getByText(/CLV 30 jours/i)).toBeInTheDocument();
    expect(screen.getByText(/négatif/i)).toBeInTheDocument();
    expect(screen.getByText(/mois offert/i)).toBeInTheDocument();
  });

  it('renders a Shield lucide icon with aria-hidden', () => {
    const { container } = render(<TransparencyGuarantee />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });

  it('accepts a custom data-testid prop', () => {
    render(<TransparencyGuarantee data-testid="guarantee-x" />);
    expect(screen.getByTestId('guarantee-x')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<TransparencyGuarantee />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
