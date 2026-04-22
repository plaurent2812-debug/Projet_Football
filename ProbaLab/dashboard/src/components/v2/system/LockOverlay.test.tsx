import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { LockOverlay } from './LockOverlay';

describe('LockOverlay', () => {
  it('renders the message', () => {
    render(
      <LockOverlay message="Débloque avec Premium">
        <p>hidden content</p>
      </LockOverlay>,
    );
    expect(screen.getByText('Débloque avec Premium')).toBeInTheDocument();
  });

  it('keeps children visible but blurred', () => {
    render(
      <LockOverlay message="locked">
        <p data-testid="child">hidden content</p>
      </LockOverlay>,
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.getByTestId('lock-children')).toHaveAttribute('aria-hidden', 'true');
  });

  it('exposes a descriptive role and aria-label', () => {
    render(
      <LockOverlay message="Débloque avec Premium">
        <p>x</p>
      </LockOverlay>,
    );
    expect(screen.getByRole('region', { name: /contenu verrouillé/i })).toBeInTheDocument();
  });

  it('defaults data-testid to lock-overlay and data-variant to inline', () => {
    render(
      <LockOverlay message="locked">
        <p>x</p>
      </LockOverlay>,
    );
    const overlay = screen.getByTestId('lock-overlay');
    expect(overlay).toHaveAttribute('data-variant', 'inline');
  });

  it('reflects fullCover variant via data-variant', () => {
    render(
      <LockOverlay message="locked" variant="fullCover">
        <p>x</p>
      </LockOverlay>,
    );
    expect(screen.getByTestId('lock-overlay')).toHaveAttribute('data-variant', 'fullCover');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <LockOverlay message="locked">
        <p>content</p>
      </LockOverlay>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
