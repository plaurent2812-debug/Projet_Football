import { ExternalLink } from 'lucide-react';
import { useSubscription } from '@/hooks/v2/useSubscription';
import type { SubscriptionStatus as StripeStatus } from '@/types/v2/common';
import type { SubscriptionData } from '@/hooks/v2/useSubscription';

export interface SubscriptionStatusProps {
  'data-testid'?: string;
}

const PLAN_LABELS: Record<SubscriptionData['plan'], string> = {
  FREE: 'Free',
  TRIAL: 'Essai',
  PREMIUM: 'Premium',
};

const STATUS_COPY: Record<StripeStatus, { label: string; tone: Tone }> = {
  active: { label: 'Active', tone: 'emerald' },
  trialing: { label: "En période d'essai", tone: 'amber' },
  past_due: { label: 'Paiement en retard', tone: 'rose' },
  canceled: { label: 'Annulée', tone: 'slate' },
  incomplete: { label: 'Incomplet', tone: 'amber' },
  none: { label: 'Aucune', tone: 'slate' },
};

type Tone = 'emerald' | 'amber' | 'rose' | 'slate';

const TONE_STYLES: Record<Tone, string> = {
  emerald:
    'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  amber: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  rose: 'bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300',
  slate: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
};

function fmtDate(iso: string | undefined): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString('fr-FR');
}

/**
 * "Statut" card of the subscription tab.
 *
 * Renders the plan (Free / Trial / Premium), the Stripe lifecycle status
 * (`active`, `past_due`, ...) and, when applicable, the next renewal date
 * (or cancellation date if cancelAtPeriodEnd is set).
 *
 * Always exposes a "Gérer mon abonnement" link to the Stripe customer
 * portal, plus a second "Annuler mon abonnement" link when the user has
 * an active non-cancelled subscription.
 */
export function SubscriptionStatus({
  'data-testid': dataTestId = 'subscription-status',
}: SubscriptionStatusProps = {}) {
  const { data, isLoading } = useSubscription();

  if (isLoading || !data) {
    return (
      <div
        data-testid="subscription-status-skeleton"
        aria-busy="true"
        aria-label="Chargement du statut"
        className="h-32 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
      />
    );
  }

  const statusMeta = STATUS_COPY[data.status];
  const renewDate = fmtDate(data.renewsAt);
  const isActive = data.status === 'active' || data.status === 'trialing';
  const canCancel = isActive && !data.cancelAtPeriodEnd;

  return (
    <section
      data-testid={dataTestId}
      aria-label="Statut d'abonnement"
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Statut
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${TONE_STYLES[statusMeta.tone]}`}
            >
              {PLAN_LABELS[data.plan]}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {statusMeta.label}
            </span>
          </div>
          {renewDate && (
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
              {data.cancelAtPeriodEnd ? 'Se termine le' : 'Renouvellement le'}{' '}
              <span className="font-medium text-slate-900 dark:text-white">
                {renewDate}
              </span>
            </p>
          )}
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <a
            href="/api/billing/portal"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Gérer mon abonnement
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
          {canCancel && (
            <a
              href="/api/billing/portal?action=cancel"
              className="text-xs text-rose-600 hover:underline dark:text-rose-400"
            >
              Annuler mon abonnement
            </a>
          )}
        </div>
      </div>
    </section>
  );
}

export default SubscriptionStatus;
