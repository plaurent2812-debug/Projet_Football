import { SubscriptionStatus } from '@/components/v2/account/subscription/SubscriptionStatus';
import { InvoicesList } from '@/components/v2/account/subscription/InvoicesList';

/**
 * "Abonnement" tab page — composes {@link SubscriptionStatus} and
 * {@link InvoicesList}.
 *
 * Matches the design section 10.3 : the status card sits on top, the
 * invoices table below with its own "Factures" heading.
 */
export function SubscriptionTab() {
  return (
    <div data-testid="subscription-tab" className="space-y-6">
      <SubscriptionStatus />
      <section aria-label="Historique des factures">
        <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-white">
          Factures
        </h2>
        <InvoicesList />
      </section>
    </div>
  );
}

export default SubscriptionTab;
