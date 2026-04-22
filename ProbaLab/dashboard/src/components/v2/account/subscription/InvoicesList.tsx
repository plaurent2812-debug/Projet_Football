import { Download } from 'lucide-react';
import { useInvoices } from '@/hooks/v2/useInvoices';
import type { Invoice } from '@/hooks/v2/useInvoices';

export interface InvoicesListProps {
  'data-testid'?: string;
}

const eurFmt = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'EUR',
});

const STATUS_LABEL: Record<Invoice['status'], string> = {
  paid: 'Payée',
  open: 'Ouverte',
  void: 'Annulée',
};

const STATUS_CLASS: Record<Invoice['status'], string> = {
  paid: 'text-emerald-600 dark:text-emerald-400',
  open: 'text-amber-600 dark:text-amber-400',
  void: 'text-slate-500 dark:text-slate-400',
};

/**
 * Renders the Stripe-mirrored invoice history for the current user.
 *
 * Empty state, loading skeleton, and a table with N°/Date/Montant/Statut/PDF
 * columns. Amounts are kept in cents on the wire and formatted with
 * Intl.NumberFormat fr-FR at render time.
 */
export function InvoicesList({
  'data-testid': dataTestId = 'invoices-list',
}: InvoicesListProps = {}) {
  const { data, isLoading } = useInvoices();

  if (isLoading || !data) {
    return (
      <div
        data-testid="invoices-list-skeleton"
        aria-busy="true"
        aria-label="Chargement des factures"
        className="h-32 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
      />
    );
  }

  if (data.length === 0) {
    return (
      <div
        data-testid={dataTestId}
        className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400"
      >
        Aucune facture pour le moment.
      </div>
    );
  }

  return (
    <div
      data-testid={dataTestId}
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-950 dark:text-slate-400">
          <tr>
            <th className="p-3 font-medium">N°</th>
            <th className="p-3 font-medium">Date</th>
            <th className="p-3 text-right font-medium">Montant</th>
            <th className="p-3 text-center font-medium">Statut</th>
            <th className="p-3 text-right font-medium">PDF</th>
          </tr>
        </thead>
        <tbody>
          {data.map((invoice) => (
            <tr
              key={invoice.id}
              className="border-t border-slate-200 dark:border-slate-800"
            >
              <td className="p-3 font-medium text-slate-900 dark:text-white">
                {invoice.number}
              </td>
              <td className="p-3 text-slate-600 dark:text-slate-300">
                {new Date(invoice.issuedAt).toLocaleDateString('fr-FR')}
              </td>
              <td className="p-3 text-right tabular-nums text-slate-900 dark:text-white">
                {eurFmt.format(invoice.amountCents / 100)}
              </td>
              <td className={`p-3 text-center ${STATUS_CLASS[invoice.status]}`}>
                {STATUS_LABEL[invoice.status]}
              </td>
              <td className="p-3 text-right">
                <a
                  href={invoice.pdfUrl}
                  className="inline-flex items-center gap-1 text-emerald-600 hover:underline dark:text-emerald-400"
                  aria-label={`Télécharger la facture ${invoice.number}`}
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  Télécharger
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default InvoicesList;
