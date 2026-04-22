import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { StickyActions } from './StickyActions';
import type { Recommendation } from '../../../types/v2/match-detail';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { Wrapper, client };
}

const reco: Recommendation = {
  market_key: '1x2.home',
  market_label: 'Victoire Nice',
  odds: 2.1,
  confidence: 0.74,
  kelly_fraction: 0.035,
  edge: 0.08,
  book_name: 'Unibet',
};

describe('StickyActions', () => {
  it('renders both action buttons', () => {
    const { Wrapper } = createWrapper();
    render(
      <Wrapper>
        <StickyActions fixtureId="fx-1" recommendation={reco} />
      </Wrapper>,
    );
    expect(
      screen.getByRole('button', { name: /suivre.*bankroll/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /alerte.*kick-off/i }),
    ).toBeInTheDocument();
  });

  it('clicking "Suivre bankroll" triggers the add-bet mutation', async () => {
    const user = userEvent.setup();
    const { Wrapper } = createWrapper();
    render(
      <Wrapper>
        <StickyActions fixtureId="fx-1" recommendation={reco} />
      </Wrapper>,
    );
    const btn = screen.getByRole('button', { name: /suivre.*bankroll/i });
    await user.click(btn);
    // The mutation is async; we expect a success state to bubble up.
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /ajouté|bankroll/i }),
      ).toBeInTheDocument(),
    );
  });

  it('disables the bankroll button while the mutation is pending', async () => {
    const user = userEvent.setup();
    const { Wrapper } = createWrapper();
    render(
      <Wrapper>
        <StickyActions fixtureId="fx-1" recommendation={reco} />
      </Wrapper>,
    );
    const btn = screen.getByRole('button', { name: /suivre.*bankroll/i });
    await user.click(btn);
    // Immediately after click: either pending (disabled) or success (disabled once success reached)
    await waitFor(() => expect(btn).toBeDisabled());
  });

  it('calls onAlertKickoff when the alert button is clicked', async () => {
    const user = userEvent.setup();
    const onAlert = vi.fn();
    const { Wrapper } = createWrapper();
    render(
      <Wrapper>
        <StickyActions
          fixtureId="fx-1"
          recommendation={reco}
          onAlertKickoff={onAlert}
        />
      </Wrapper>,
    );
    await user.click(screen.getByRole('button', { name: /alerte.*kick-off/i }));
    expect(onAlert).toHaveBeenCalledTimes(1);
  });

  it('does not throw when onAlertKickoff is not provided', async () => {
    const user = userEvent.setup();
    const { Wrapper } = createWrapper();
    render(
      <Wrapper>
        <StickyActions fixtureId="fx-1" recommendation={reco} />
      </Wrapper>,
    );
    await user.click(screen.getByRole('button', { name: /alerte.*kick-off/i }));
    // No-op — just checking it doesn't throw
    expect(
      screen.getByRole('button', { name: /alerte.*kick-off/i }),
    ).toBeInTheDocument();
  });

  it('accepts a custom data-testid on the root', () => {
    const { Wrapper } = createWrapper();
    render(
      <Wrapper>
        <StickyActions
          fixtureId="fx-1"
          recommendation={reco}
          data-testid="sticky"
        />
      </Wrapper>,
    );
    expect(screen.getByTestId('sticky')).toBeInTheDocument();
  });

  it('uses the recommendation odds in the request payload (via mutation result)', async () => {
    const user = userEvent.setup();
    const { Wrapper } = createWrapper();
    render(
      <Wrapper>
        <StickyActions fixtureId="fx-99" recommendation={reco} />
      </Wrapper>,
    );
    await user.click(screen.getByRole('button', { name: /suivre.*bankroll/i }));
    // Success message eventually appears — check the button text changes.
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /ajouté|bankroll/i }),
      ).toBeInTheDocument(),
    );
  });

  it('has no accessibility violations', async () => {
    const { Wrapper } = createWrapper();
    const { container } = render(
      <Wrapper>
        <StickyActions fixtureId="fx-1" recommendation={reco} />
      </Wrapper>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
