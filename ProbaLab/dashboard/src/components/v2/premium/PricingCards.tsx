import { Link } from 'react-router-dom';
import { Check, ArrowRight } from 'lucide-react';

interface Props {
  'data-testid'?: string;
  /** Where the Free CTA points to. Defaults to `/register`. */
  freeHref?: string;
  /** Where the Premium CTA points to. Defaults to `/register?plan=premium&trial=30d`. */
  premiumHref?: string;
}

const FREE_FEATURES = [
  '3 prédictions par jour',
  'Marchés 1X2 uniquement',
  'Track record public en lecture',
  'Communauté Discord',
];

const PREMIUM_FEATURES = [
  'Prédictions illimitées + value bets',
  'Tous marchés (BTTS, O/U, Handicaps, Score exact)',
  'Bankroll + Kelly + ROI par marché',
  'Notifications Telegram / Push / Email',
  'Combos Safe / Fun / Jackpot',
  'Analyses narratives Gemini',
];

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className="mt-6 space-y-2 text-sm">
      {items.map((f) => (
        <li key={f} className="flex items-start gap-2">
          <Check
            size={16}
            aria-hidden="true"
            style={{ color: 'var(--primary)', flexShrink: 0, marginTop: 2 }}
          />
          <span style={{ color: 'var(--text)' }}>{f}</span>
        </li>
      ))}
    </ul>
  );
}

/**
 * Pricing grid (Free vs Premium).
 *
 * - Free card: neutral border, CTA "Créer compte gratuit".
 * - Premium card: emerald border + amber "RECOMMANDÉ" badge,
 *   CTA "Démarrer la trial 30j →".
 *
 * Both CTAs are `<Link>`s — the actual subscription flow happens in
 * `/register` which itself redirects to the Stripe portal when needed.
 */
export function PricingCards({
  'data-testid': dataTestId = 'pricing-cards',
  freeHref = '/register',
  premiumHref = '/register?plan=premium&trial=30d',
}: Props) {
  return (
    <section
      data-testid={dataTestId}
      aria-labelledby="pricing-cards-title"
      className="py-12"
    >
      <h2
        id="pricing-cards-title"
        className="text-center text-2xl md:text-3xl font-bold tracking-tight"
        style={{ color: 'var(--text)' }}
      >
        Choisissez votre plan
      </h2>
      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        {/* Free card */}
        <div
          className="rounded-2xl p-8"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <h3 className="text-xl font-semibold" style={{ color: 'var(--text)' }}>
            Free
          </h3>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
            Pour découvrir
          </p>
          <div className="mt-6 flex items-baseline gap-1">
            <span className="text-4xl font-bold" style={{ color: 'var(--text)' }}>
              0 €
            </span>
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              / pour toujours
            </span>
          </div>
          <FeatureList items={FREE_FEATURES} />
          <Link
            to={freeHref}
            className="mt-8 inline-flex w-full items-center justify-center rounded-md px-4 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2"
            style={{ border: '1px solid var(--border)', color: 'var(--text)' }}
          >
            Créer compte gratuit
          </Link>
        </div>

        {/* Premium card */}
        <div
          className="relative rounded-2xl p-8"
          style={{
            background: 'var(--surface)',
            border: '2px solid var(--primary)',
            boxShadow: '0 10px 30px -10px color-mix(in oklab, var(--primary) 40%, transparent)',
          }}
        >
          <span
            className="absolute -top-3 right-6 rounded-full px-3 py-1 text-xs font-bold"
            style={{
              background: 'var(--value, #f59e0b)',
              color: '#0a0e1a',
              letterSpacing: 0.6,
            }}
          >
            RECOMMANDÉ
          </span>
          <h3 className="text-xl font-semibold" style={{ color: 'var(--text)' }}>
            Premium
          </h3>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
            Tout ProbaLab, sans limite
          </p>
          <div className="mt-6 flex items-baseline gap-1">
            <span className="text-4xl font-bold" style={{ color: 'var(--text)' }}>
              14,99 €
            </span>
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              / mois
            </span>
          </div>
          <FeatureList items={PREMIUM_FEATURES} />
          <Link
            to={premiumHref}
            className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-md px-4 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2"
            style={{ background: 'var(--primary)', color: '#0a0e1a' }}
          >
            Démarrer la trial 30j
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
          <p className="mt-3 text-center text-xs" style={{ color: 'var(--text-muted)' }}>
            30 jours gratuits · sans carte · résiliable en 1 clic
          </p>
        </div>
      </div>
    </section>
  );
}

export default PricingCards;
