import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LayoutShell } from './LayoutShell';

describe('LayoutShell', () => {
  it('wraps children with header and bottom nav', () => {
    render(
      <MemoryRouter>
        <LayoutShell userRole="free">
          <p>page content</p>
        </LayoutShell>
      </MemoryRouter>
    );
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: /navigation mobile/i })).toBeInTheDocument();
    expect(screen.getByText('page content')).toBeInTheDocument();
  });

  it('renders trial banner when role is trial', () => {
    render(
      <MemoryRouter>
        <LayoutShell userRole="trial" trialDaysLeft={5} trialEndDate="2026-04-26">
          <p>content</p>
        </LayoutShell>
      </MemoryRouter>
    );
    expect(screen.getByRole('region', { name: /trial/i })).toBeInTheDocument();
  });

  it('does not render trial banner when role is free', () => {
    render(
      <MemoryRouter>
        <LayoutShell userRole="free">
          <p>content</p>
        </LayoutShell>
      </MemoryRouter>
    );
    expect(screen.queryByRole('region', { name: /trial/i })).not.toBeInTheDocument();
  });

  it('defaults userRole to visitor when not provided', () => {
    render(
      <MemoryRouter>
        <LayoutShell>
          <p>content</p>
        </LayoutShell>
      </MemoryRouter>
    );
    expect(screen.getByText('content')).toBeInTheDocument();
  });
});
