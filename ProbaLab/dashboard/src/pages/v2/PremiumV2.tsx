import { PremiumHero } from '@/components/v2/premium/PremiumHero';
import { LiveTrackRecord } from '@/components/v2/premium/LiveTrackRecord';
import { PricingCards } from '@/components/v2/premium/PricingCards';
import { TransparencyGuarantee } from '@/components/v2/premium/TransparencyGuarantee';
import { FAQShort } from '@/components/v2/premium/FAQShort';

/**
 * V2 Premium landing page.
 *
 * Orchestrates, in order:
 *   1. `<PremiumHero />`            — positioning + 2 CTAs
 *   2. `<LiveTrackRecord id=.. />`  — smooth-scroll target of the hero secondary CTA
 *   3. `<PricingCards />`           — Free vs Premium grid
 *   4. `<TransparencyGuarantee />`  — monthly guarantee banner
 *   5. `<FAQShort />`               — 3-card FAQ
 *
 * The page itself is responsive (mobile-first, centered max-width container)
 * and marks its root with `data-testid="premium-v2-page"` for e2e selection.
 */
export function PremiumV2() {
  return (
    <main
      data-testid="premium-v2-page"
      aria-label="Page Premium"
      className="mx-auto w-full max-w-6xl px-4 md:px-6 space-y-12 md:space-y-20 pb-20"
    >
      <PremiumHero />
      <LiveTrackRecord id="track-record" />
      <PricingCards />
      <TransparencyGuarantee />
      <FAQShort />
    </main>
  );
}

export default PremiumV2;
