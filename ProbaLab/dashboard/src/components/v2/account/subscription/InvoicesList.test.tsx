import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import type { Invoice } from '@/hooks/v2/useInvoices';
import { InvoicesList } from './InvoicesList';

let invoicesState: { data: Invoice[] | null; isLoading: boolean } = {
  data: null,
  isLoading: true,
};

vi.mock('@/hooks/v2/useInvoices', () => ({
  useInvoices: () => invoicesState,
}));

const twoInvoices: Invoice[] = [
  {
    id: 'in_001',
    number: 'F-001',
    amountCents: 1499,
    currency: 'EUR',
    status: 'paid',
    issuedAt: '2026-04-01T00:00:00Z',
    pdfUrl: 'https://x.test/F-001.pdf',
  },
  {
    id: 'in_002',
    number: 'F-002',
    amountCents: 1499,
    currency: 'EUR',
    status: 'paid',
    issuedAt: '2026-03-01T00:00:00Z',
    pdfUrl: 'https://x.test/F-002.pdf',
  },
];

beforeEach(() => {
  invoicesState = { data: twoInvoices, isLoading: false };
});

describe('InvoicesList', () => {
  it('renders a skeleton while loading', () => {
    invoicesState = { data: null, isLoading: true };
    render(<InvoicesList />);
    expect(screen.getByTestId('invoices-list-skeleton')).toBeInTheDocument();
  });

  it('renders an empty state when there are no invoices', () => {
    invoicesState = { data: [], isLoading: false };
    render(<InvoicesList />);
    expect(screen.getByText(/aucune facture/i)).toBeInTheDocument();
  });

  it('renders a row per invoice with amount formatted in euros', () => {
    render(<InvoicesList />);
    // header + 2 rows
    expect(screen.getAllByRole('row')).toHaveLength(3);
    expect(screen.getAllByText(/14,99/).length).toBeGreaterThan(0);
  });

  it('renders a download link per invoice', () => {
    render(<InvoicesList />);
    const links = screen.getAllByRole('link', { name: /télécharger/i });
    expect(links).toHaveLength(2);
    expect(links[0]?.getAttribute('href')).toBe('https://x.test/F-001.pdf');
  });

  it('formats the issued date in fr-FR format', () => {
    render(<InvoicesList />);
    expect(screen.getByText(/01\/04\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/01\/03\/2026/)).toBeInTheDocument();
  });

  it('labels the status column with accessible text', () => {
    render(<InvoicesList />);
    expect(screen.getAllByText(/payée/i)).toHaveLength(2);
  });

  it('accepts a custom data-testid on the root', () => {
    render(<InvoicesList data-testid="my-invoices" />);
    expect(screen.getByTestId('my-invoices')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<InvoicesList />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
