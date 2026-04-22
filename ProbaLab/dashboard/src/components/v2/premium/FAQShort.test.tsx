import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { FAQShort } from './FAQShort';

describe('FAQShort', () => {
  it('renders exactly 3 FAQ cards as articles', () => {
    render(<FAQShort />);
    const items = screen.getAllByRole('article');
    expect(items).toHaveLength(3);
  });

  it('mentions CLV in at least one question', () => {
    render(<FAQShort />);
    expect(screen.getAllByText(/CLV/i).length).toBeGreaterThanOrEqual(1);
  });

  it('features the cancel question and the garanties question', () => {
    render(<FAQShort />);
    expect(screen.getByText(/puis-je annuler/i)).toBeInTheDocument();
    expect(screen.getByText(/pronos garantis/i)).toBeInTheDocument();
  });

  it('accepts a custom data-testid prop', () => {
    render(<FAQShort data-testid="faq-x" />);
    expect(screen.getByTestId('faq-x')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<FAQShort />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
