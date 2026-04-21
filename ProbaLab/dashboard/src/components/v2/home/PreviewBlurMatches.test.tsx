import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { PreviewBlurMatches } from './PreviewBlurMatches';
import { mockMatches } from '@/test/mocks/fixtures';

expect.extend(toHaveNoViolations);

function wrap(ui: React.ReactElement) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

describe('PreviewBlurMatches', () => {
  it('renders 3 blurred match rows with a sign-up overlay', () => {
    render(wrap(<PreviewBlurMatches matches={mockMatches} />));
    expect(screen.getAllByTestId('preview-blur-row')).toHaveLength(3);
    expect(
      screen.getByRole('link', { name: /S'inscrire|Créer un compte/i }),
    ).toHaveAttribute('href', '/register');
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<PreviewBlurMatches matches={mockMatches} />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
