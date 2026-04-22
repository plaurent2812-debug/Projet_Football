import { useEffect, useState } from 'react';
import { useV2User } from '@/hooks/v2/useV2User';
import { useSafePick } from '@/hooks/v2/useSafePick';
import { useMatchesOfDay } from '@/hooks/v2/useMatchesOfDay';
import { usePerformanceSummary } from '@/hooks/v2/usePerformanceSummary';
import { HeroLanding } from '@/components/v2/home/HeroLanding';
import { PreviewBlurMatches } from '@/components/v2/home/PreviewBlurMatches';
import { StatStrip } from '@/components/v2/home/StatStrip';
import { SafeOfTheDayCard } from '@/components/v2/home/SafeOfTheDayCard';
import { MatchesList } from '@/components/v2/home/MatchesList';
import { ValueBetsTeaser } from '@/components/v2/home/ValueBetsTeaser';
import { PremiumCTA } from '@/components/v2/home/PremiumCTA';
import { StatTile } from '@/components/v2/system/StatTile';

const DESKTOP_BREAKPOINT = 1024;

function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.innerWidth >= DESKTOP_BREAKPOINT : true,
  );
  useEffect(() => {
    const onResize = () => setIsDesktop(window.innerWidth >= DESKTOP_BREAKPOINT);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return isDesktop;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function HomeV2() {
  const user = useV2User();
  const date = todayIso();
  const safe = useSafePick(date);
  const matches = useMatchesOfDay({ date });
  const perf = usePerformanceSummary();
  const isDesktop = useIsDesktop();

  if (user.isVisitor) {
    return (
      <main
        data-testid="home-landing"
        aria-label="Accueil ProbaLab"
        className="mx-auto max-w-5xl px-4 md:px-8 pb-10 space-y-8"
      >
        <HeroLanding />
        {matches.data && <PreviewBlurMatches matches={matches.data.matches} />}
        <section
          aria-label="Track record"
          className="grid grid-cols-1 md:grid-cols-3 gap-3"
        >
          <StatTile label="ROI public 30J" value="+12.4%" tone="positive" />
          <StatTile label="CLV vs Pinnacle" value="+2.1%" tone="positive" />
          <StatTile label="Accuracy" value="54.2%" />
        </section>
      </main>
    );
  }

  const gating: 'free' | 'trial' | 'premium' =
    user.role === 'free' ? 'free' : user.role === 'trial' ? 'trial' : 'premium';

  const showPremiumCTA = user.role !== 'premium' && user.role !== 'admin';

  return (
    <main
      data-testid="home-v2"
      aria-label="Tableau de bord ProbaLab"
      className="mx-auto max-w-7xl px-4 md:px-8 py-6 space-y-6"
    >
      <StatStrip data={perf.data} loading={perf.isLoading} />
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          {!isDesktop && <SafeOfTheDayCard data={safe.data ?? null} />}
          <section>
            <h2
              className="mb-3 text-lg font-semibold"
              style={{ color: 'var(--text)' }}
            >
              Au programme
            </h2>
            {matches.isLoading ? (
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Chargement des matchs...
              </p>
            ) : matches.isError ? (
              <p className="text-sm" style={{ color: 'var(--danger, #ef4444)' }}>
                Impossible de charger les matchs du jour.
              </p>
            ) : (
              <MatchesList matches={matches.data?.matches ?? []} />
            )}
          </section>
        </div>
        <aside
          data-testid="home-right-col"
          data-layout={isDesktop ? 'sticky' : 'inline'}
          className={isDesktop ? 'sticky top-5 space-y-4 self-start' : 'space-y-4'}
        >
          {isDesktop && <SafeOfTheDayCard data={safe.data ?? null} />}
          {matches.data && matches.data.matches.length > 0 && (
            <ValueBetsTeaser matches={matches.data.matches} gating={gating} />
          )}
          {showPremiumCTA && <PremiumCTA />}
        </aside>
      </div>
    </main>
  );
}

export default HomeV2;
