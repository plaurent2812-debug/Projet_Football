import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import type {
  SubscriptionData,
} from '@/hooks/v2/useSubscription';
import { SubscriptionStatus } from './SubscriptionStatus';

let subState: {
  data: SubscriptionData | null;
  isLoading: boolean;
} = {
  data: {
    plan: 'PREMIUM',
    status: 'active',
    renewsAt: '2026-05-21T00:00:00Z',
    cancelAtPeriodEnd: false,
  },
  isLoading: false,
};

vi.mock('@/hooks/v2/useSubscription', () => ({
  useSubscription: () => subState,
}));

beforeEach(() => {
  subState = {
    data: {
      plan: 'PREMIUM',
      status: 'active',
      renewsAt: '2026-05-21T00:00:00Z',
      cancelAtPeriodEnd: false,
    },
    isLoading: false,
  };
});

describe('SubscriptionStatus', () => {
  it('renders a skeleton while loading', () => {
    subState = { data: null, isLoading: true };
    render(<SubscriptionStatus />);
    expect(screen.getByTestId('subscription-status-skeleton')).toBeInTheDocument();
  });

  it('renders PREMIUM badge + renewal date formatted fr-FR', () => {
    render(<SubscriptionStatus />);
    expect(screen.getByText(/premium/i)).toBeInTheDocument();
    expect(screen.getByText(/21\/05\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/renouvellement/i)).toBeInTheDocument();
  });

  it('labels the date as "Se termine le" when cancelAtPeriodEnd', () => {
    subState = {
      data: {
        plan: 'PREMIUM',
        status: 'active',
        renewsAt: '2026-05-21T00:00:00Z',
        cancelAtPeriodEnd: true,
      },
      isLoading: false,
    };
    render(<SubscriptionStatus />);
    expect(screen.getByText(/se termine le/i)).toBeInTheDocument();
  });

  it('labels the status past_due with a warning tone', () => {
    subState = {
      data: {
        plan: 'PREMIUM',
        status: 'past_due',
      },
      isLoading: false,
    };
    render(<SubscriptionStatus />);
    expect(screen.getByText(/paiement en retard/i)).toBeInTheDocument();
  });

  it('labels FREE plan without any renewal date', () => {
    subState = {
      data: { plan: 'FREE', status: 'none' },
      isLoading: false,
    };
    render(<SubscriptionStatus />);
    expect(screen.getByText(/free/i)).toBeInTheDocument();
    expect(screen.queryByText(/renouvellement/i)).not.toBeInTheDocument();
  });

  it('exposes a Stripe customer portal link', () => {
    render(<SubscriptionStatus />);
    const link = screen.getByRole('link', {
      name: /gérer (mon |l')abonnement/i,
    }) as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/api/billing/portal');
  });

  it('shows a cancel CTA when the subscription is active and not already cancelled', () => {
    render(<SubscriptionStatus />);
    expect(
      screen.getByRole('link', { name: /annuler mon abonnement/i }),
    ).toBeInTheDocument();
  });

  it('hides the cancel CTA when already set to cancel at period end', () => {
    subState = {
      data: {
        plan: 'PREMIUM',
        status: 'active',
        renewsAt: '2026-05-21T00:00:00Z',
        cancelAtPeriodEnd: true,
      },
      isLoading: false,
    };
    render(<SubscriptionStatus />);
    expect(
      screen.queryByRole('link', { name: /annuler mon abonnement/i }),
    ).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<SubscriptionStatus />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('accepts a custom data-testid on the root', () => {
    render(<SubscriptionStatus data-testid="my-status" />);
    expect(screen.getByTestId('my-status')).toBeInTheDocument();
  });
});
