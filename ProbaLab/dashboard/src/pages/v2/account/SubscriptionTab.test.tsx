import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { SubscriptionTab } from './SubscriptionTab';

vi.mock('@/hooks/v2/useSubscription', () => ({
  useSubscription: () => ({
    data: {
      plan: 'PREMIUM',
      status: 'active',
      renewsAt: '2026-05-21T00:00:00Z',
      cancelAtPeriodEnd: false,
    },
    isLoading: false,
  }),
}));

vi.mock('@/hooks/v2/useInvoices', () => ({
  useInvoices: () => ({
    data: [
      {
        id: 'in_001',
        number: 'F-001',
        amountCents: 1499,
        currency: 'EUR',
        status: 'paid',
        issuedAt: '2026-04-01T00:00:00Z',
        pdfUrl: '/x.pdf',
      },
    ],
    isLoading: false,
  }),
}));

describe('SubscriptionTab', () => {
  it('composes SubscriptionStatus + InvoicesList', () => {
    render(<SubscriptionTab />);
    expect(screen.getByText(/premium/i)).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /factures/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/f-001/i)).toBeInTheDocument();
  });

  it('exposes a data-testid on the root', () => {
    render(<SubscriptionTab />);
    expect(screen.getByTestId('subscription-tab')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<SubscriptionTab />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
