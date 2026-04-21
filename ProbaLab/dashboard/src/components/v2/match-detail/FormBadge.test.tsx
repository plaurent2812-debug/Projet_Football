import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { FormBadge } from './FormBadge';

describe('FormBadge', () => {
  it('renders aria-label with W/D/L mapped to V/N/D', () => {
    render(<FormBadge form={['W', 'W', 'D', 'W', 'W']} />);
    const el = screen.getByLabelText('Forme récente : V V N V V');
    expect(el).toBeInTheDocument();
  });

  it('maps L to D (défaite) in aria-label', () => {
    render(<FormBadge form={['W', 'L', 'D', 'L', 'W']} />);
    const el = screen.getByLabelText('Forme récente : V D N D V');
    expect(el).toBeInTheDocument();
  });

  it('applies color class per outcome', () => {
    render(<FormBadge form={['W', 'L', 'D', 'W', 'L']} />);
    const dots = screen.getAllByTestId('form-dot');
    expect(dots).toHaveLength(5);
    expect(dots[0].className).toMatch(/bg-emerald/);
    expect(dots[1].className).toMatch(/bg-rose/);
    expect(dots[2].className).toMatch(/bg-slate/);
    expect(dots[3].className).toMatch(/bg-emerald/);
    expect(dots[4].className).toMatch(/bg-rose/);
  });

  it('renders nothing visible when form empty but stays labelled', () => {
    render(<FormBadge form={[]} />);
    const el = screen.getByLabelText('Forme récente :');
    expect(el).toBeInTheDocument();
    expect(screen.queryAllByTestId('form-dot')).toHaveLength(0);
  });

  it('accepts size="sm" without breaking render', () => {
    render(<FormBadge form={['W']} size="sm" />);
    expect(screen.getByTestId('form-dot')).toBeInTheDocument();
  });

  it('accepts a custom data-testid on the root', () => {
    render(<FormBadge form={['W']} data-testid="home-form" />);
    expect(screen.getByTestId('home-form')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<FormBadge form={['W', 'W', 'D', 'L', 'W']} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
