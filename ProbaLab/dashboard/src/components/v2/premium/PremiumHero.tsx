import { Link } from 'react-router-dom';
import { ArrowRight, ArrowDown } from 'lucide-react';

interface Props {
  'data-testid'?: string;
  /** Anchor id the secondary CTA smooth-scrolls to. Defaults to `track-record`. */
  scrollTargetId?: string;
}

/**
 * Premium landing hero section.
 *
 * - Label "PROBALAB PREMIUM" in emerald.
 * - Main h1 (44px) carrying the positioning.
 * - CLV subtitle.
 * - Primary CTA → `/register` (Essai gratuit 30 jours).
 * - Secondary CTA → smooth-scroll to the live track record section.
 * - A trust line closes the section (no card required, 1-click cancel).
 */
export function PremiumHero({
  'data-testid': dataTestId = 'premium-hero',
  scrollTargetId = 'track-record',
}: Props) {
  const scrollToTrackRecord = () => {
    if (typeof document === 'undefined') return;
    const el = document.getElementById(scrollTargetId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <section
      data-testid={dataTestId}
      aria-labelledby="premium-hero-title"
      className="py-16 md:py-24 text-center"
    >
      <span
        className="inline-block text-xs font-semibold tracking-[0.2em]"
        style={{ color: 'var(--primary)' }}
      >
        PROBALAB PREMIUM
      </span>
      <h1
        id="premium-hero-title"
        className="mt-4 mx-auto max-w-3xl text-3xl md:text-[44px] font-bold leading-tight tracking-tight"
        style={{ color: 'var(--text)' }}
      >
        Parier avec une vraie probabilité, pas un feeling.
      </h1>
      <p
        className="mt-4 max-w-2xl mx-auto text-base md:text-lg"
        style={{ color: 'var(--text-muted)' }}
      >
        Le seul pronostiqueur français qui publie son CLV vs Pinnacle en temps
        réel. Des prédictions calibrées, pas des promesses.
      </p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link
          to="/register"
          className="inline-flex items-center gap-2 rounded-md px-5 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2"
          style={{ background: 'var(--primary)', color: '#0a0e1a' }}
        >
          Essai gratuit 30 jours
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
        <button
          type="button"
          onClick={scrollToTrackRecord}
          className="inline-flex items-center gap-2 rounded-md px-5 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2"
          style={{ border: '1px solid var(--border)', color: 'var(--text)' }}
        >
          Voir le track record live
          <ArrowDown size={16} aria-hidden="true" />
        </button>
      </div>
      <p className="mt-6 text-xs" style={{ color: 'var(--text-muted)' }}>
        Sans engagement · Résiliation en 1 clic · Aucune carte requise
      </p>
    </section>
  );
}

export default PremiumHero;
