import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/v2/apiClient';

/**
 * Stripe invoice — returned by `GET /api/user/invoices`.
 *
 * `amountCents` stays in cents to avoid float rounding in the currency
 * formatter ; the UI divides by 100 at render time.
 */
export interface Invoice {
  id: string;
  number: string;
  amountCents: number;
  currency: 'EUR' | 'USD';
  status: 'paid' | 'open' | 'void';
  issuedAt: string;
  pdfUrl: string;
}

export function useInvoices() {
  return useQuery({
    queryKey: ['v2', 'user', 'invoices'],
    queryFn: () => apiGet<Invoice[]>('/api/user/invoices'),
    staleTime: 5 * 60 * 1000,
  });
}
