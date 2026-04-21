import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppV2 } from './AppV2';

describe('AppV2', () => {
  it('renders HomeV2 at /', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppV2 />
      </MemoryRouter>
    );
    expect(screen.getByText(/HomeV2 WIP/i)).toBeInTheDocument();
  });

  it('renders MatchesV2 at /matchs', () => {
    render(
      <MemoryRouter initialEntries={['/matchs']}>
        <AppV2 />
      </MemoryRouter>
    );
    expect(screen.getByText(/MatchesV2 WIP/i)).toBeInTheDocument();
  });

  it('renders MatchDetailV2 at /matchs/:fixtureId', () => {
    render(
      <MemoryRouter initialEntries={['/matchs/abc-123']}>
        <AppV2 />
      </MemoryRouter>
    );
    expect(screen.getByText(/MatchDetailV2 WIP/i)).toBeInTheDocument();
  });

  it('renders PremiumV2 at /premium', () => {
    render(
      <MemoryRouter initialEntries={['/premium']}>
        <AppV2 />
      </MemoryRouter>
    );
    expect(screen.getByText(/PremiumV2 WIP/i)).toBeInTheDocument();
  });

  it('renders AccountV2 at /compte', () => {
    render(
      <MemoryRouter initialEntries={['/compte']}>
        <AppV2 />
      </MemoryRouter>
    );
    expect(screen.getByText(/AccountV2 WIP/i)).toBeInTheDocument();
  });

  it('renders LoginV2 at /login', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AppV2 />
      </MemoryRouter>
    );
    expect(screen.getByText(/LoginV2 WIP/i)).toBeInTheDocument();
  });

  it('renders RegisterV2 at /register', () => {
    render(
      <MemoryRouter initialEntries={['/register']}>
        <AppV2 />
      </MemoryRouter>
    );
    expect(screen.getByText(/RegisterV2 WIP/i)).toBeInTheDocument();
  });
});
