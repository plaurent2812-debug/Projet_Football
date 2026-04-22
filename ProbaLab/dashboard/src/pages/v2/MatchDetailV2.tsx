import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { useMatchDetail } from '@/hooks/v2/useMatchDetail';
import { useAnalysis } from '@/hooks/v2/useAnalysis';
import { useV2User } from '@/hooks/v2/useV2User';
import {
  MatchHero,
  MatchHeroCompact,
  StatsComparative,
  H2HSection,
  AIAnalysis,
  CompositionsSection,
  AllMarketsGrid,
  RecoCard,
  BookOddsList,
  ValueBetsList,
  StickyActions,
} from '@/components/v2/match-detail';
import { ProbBar } from '@/components/v2/system/ProbBar';
import { Skeleton } from '@/components/ui/skeleton';
import type { FixtureId } from '@/types/v2/common';
import type {
  AnalysisPayload,
  BookOdd,
  Recommendation,
} from '@/types/v2/match-detail';

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

/**
 * Dérive une liste minimale de cotes bookmaker à partir de la reco principale.
 * Tant que le Lot 4 ne livre pas `useOddsComparison`, on affiche au moins le
 * meilleur prix connu pour maintenir la section dans la colonne droite.
 */
function deriveBookOdds(
  recommendation: Recommendation | null,
  kickoffUtc: string,
): BookOdd[] {
  if (!recommendation) return [];
  return [
    {
      bookmaker: recommendation.book_name,
      odds: recommendation.odds,
      is_best: true,
      updated_at: kickoffUtc,
    },
  ];
}

const EMPTY_ANALYSIS: AnalysisPayload = {
  paragraphs: [],
  generated_at: '',
};

export function MatchDetailV2() {
  const params = useParams<{ fixtureId: FixtureId }>();
  const fixtureId = params.fixtureId ?? null;
  const { role } = useV2User();
  const isDesktop = useIsDesktop();

  const match = useMatchDetail(fixtureId);
  const analysis = useAnalysis(fixtureId);

  if (match.isLoading) {
    return (
      <main
        data-testid="match-detail-loading"
        aria-label="Chargement du match"
        className="mx-auto max-w-7xl px-4 md:px-8 py-6 space-y-4"
      >
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-40 w-full" />
        <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </main>
    );
  }

  if (match.isError || !match.data) {
    return (
      <main
        data-testid="match-detail-error"
        aria-label="Erreur chargement match"
        className="mx-auto max-w-3xl px-4 md:px-8 py-10 text-center"
      >
        <p className="text-sm text-rose-600">
          Impossible de charger le match. Réessaie dans un instant.
        </p>
        <Link
          to="/matchs"
          className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          Retour aux matchs
        </Link>
      </main>
    );
  }

  const d = match.data;
  const matchTitle = `${d.header.home.name} vs ${d.header.away.name}`;
  const analysisPayload: AnalysisPayload = analysis.data ?? EMPTY_ANALYSIS;
  const hasAnalysis = analysisPayload.paragraphs.length > 0;
  const bookOdds = deriveBookOdds(d.recommendation, d.header.kickoff_utc);
  const canUseSticky = role === 'trial' || role === 'premium' || role === 'admin';
  const canAddToBankroll = canUseSticky && d.recommendation !== null;

  const breadcrumb = (
    <nav
      data-testid="match-detail-breadcrumb"
      aria-label="Fil d'Ariane"
      className="flex items-center gap-1 text-xs text-slate-500"
    >
      <Link
        to="/matchs"
        className="inline-flex items-center gap-1 hover:text-slate-800"
      >
        <ChevronLeft className="h-3 w-3" aria-hidden="true" />
        Matchs
      </Link>
      <span className="mx-1" aria-hidden="true">
        /
      </span>
      <span className="truncate text-slate-700">{d.header.league_name}</span>
      <span className="mx-1" aria-hidden="true">
        /
      </span>
      <span className="truncate font-medium text-slate-900">{matchTitle}</span>
    </nav>
  );

  if (!isDesktop) {
    // Mobile-first — ordre A (décision rapide) :
    // 1. Breadcrumb / back
    // 2. MatchHeroCompact
    // 3. RecoCard
    // 4. ProbBar 1X2
    // 5. ValueBetsList
    // 6. StatsComparative
    // 7. AIAnalysis
    // 8. AllMarketsGrid
    // 9. CompositionsSection
    return (
      <main
        data-testid="match-detail-v2"
        data-fixture-id={fixtureId ?? ''}
        data-layout="mobile"
        aria-label={`Détail du match ${matchTitle}`}
        className="mx-auto max-w-3xl px-4 py-4 space-y-4"
      >
        {breadcrumb}
        <MatchHeroCompact header={d.header} />
        <RecoCard recommendation={d.recommendation} />
        <ProbBar
          home={d.probs_1x2.home}
          draw={d.probs_1x2.draw}
          away={d.probs_1x2.away}
          homeLabel={d.header.home.name}
          awayLabel={d.header.away.name}
        />
        <ValueBetsList
          valueBets={d.value_bets}
          userRole={role}
          matchTitle={matchTitle}
        />
        {canAddToBankroll && d.recommendation && (
          <StickyActions
            fixtureId={fixtureId ?? ''}
            recommendation={d.recommendation}
          />
        )}
        <StatsComparative
          stats={d.stats}
          label="Stats comparées (5 derniers)"
        />
        {hasAnalysis && (
          <AIAnalysis analysis={analysisPayload} userRole={role} />
        )}
        <AllMarketsGrid markets={d.all_markets} userRole={role} />
        <CompositionsSection
          compositions={d.compositions}
          homeName={d.header.home.name}
          awayName={d.header.away.name}
        />
      </main>
    );
  }

  // Desktop — 2 colonnes sticky
  return (
    <main
      data-testid="match-detail-v2"
      data-fixture-id={fixtureId ?? ''}
      data-layout="desktop"
      aria-label={`Détail du match ${matchTitle}`}
      className="mx-auto max-w-7xl px-4 md:px-8 py-6 space-y-5"
    >
      {breadcrumb}
      <MatchHero header={d.header} />
      <div className="grid gap-7 lg:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <StatsComparative
            stats={d.stats}
            label="Stats comparées (5 derniers)"
          />
          <H2HSection
            h2h={d.h2h}
            homeName={d.header.home.name}
            awayName={d.header.away.name}
          />
          {hasAnalysis && (
            <AIAnalysis analysis={analysisPayload} userRole={role} />
          )}
          <CompositionsSection
            compositions={d.compositions}
            homeName={d.header.home.name}
            awayName={d.header.away.name}
          />
          <AllMarketsGrid markets={d.all_markets} userRole={role} />
        </div>
        <aside
          data-testid="match-detail-right-col"
          className="sticky top-5 space-y-4 self-start"
        >
          <RecoCard recommendation={d.recommendation} />
          <ProbBar
            home={d.probs_1x2.home}
            draw={d.probs_1x2.draw}
            away={d.probs_1x2.away}
            homeLabel={d.header.home.name}
            awayLabel={d.header.away.name}
          />
          <BookOddsList bookOdds={bookOdds} />
          <ValueBetsList
            valueBets={d.value_bets}
            userRole={role}
            matchTitle={matchTitle}
          />
          {canAddToBankroll && d.recommendation && (
            <StickyActions
              fixtureId={fixtureId ?? ''}
              recommendation={d.recommendation}
            />
          )}
        </aside>
      </div>
    </main>
  );
}

export default MatchDetailV2;
