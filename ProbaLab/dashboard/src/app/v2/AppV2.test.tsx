import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import { AppV2Content } from './AppV2';
import * as v2User from '@/hooks/v2/useV2User';

function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('AppV2', () => {
  it('renders HomeV2 at /', async () => {
    vi.spyOn(v2User, 'useV2User').mockReturnValue({ role: 'visitor', isVisitor: true });
    renderWithProviders(
      <MemoryRouter initialEntries={['/']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
      /vraie probabilité/i,
    );
  });

  it('renders MatchesV2 at /matchs', () => {
    render(
      <MemoryRouter initialEntries={['/matchs']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByText(/MatchesV2 WIP/i)).toBeInTheDocument();
  });

  it('renders MatchDetailV2 at /matchs/:fixtureId', () => {
    render(
      <MemoryRouter initialEntries={['/matchs/abc-123']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByText(/MatchDetailV2 WIP/i)).toBeInTheDocument();
  });

  it('renders PremiumV2 at /premium', () => {
    render(
      <MemoryRouter initialEntries={['/premium']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByText(/PremiumV2 WIP/i)).toBeInTheDocument();
  });

  it('renders AccountV2 at /compte', () => {
    render(
      <MemoryRouter initialEntries={['/compte']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByText(/AccountV2 WIP/i)).toBeInTheDocument();
  });

  it('renders LoginV2 at /login', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByText(/LoginV2 WIP/i)).toBeInTheDocument();
  });

  it('renders RegisterV2 at /register', () => {
    render(
      <MemoryRouter initialEntries={['/register']}>
        <AppV2Content />
      </MemoryRouter>
    );
    expect(screen.getByText(/RegisterV2 WIP/i)).toBeInTheDocument();
  });
});
