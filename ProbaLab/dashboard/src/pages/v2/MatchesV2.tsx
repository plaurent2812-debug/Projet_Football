import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SportChips, type SportChipsValue } from '@/components/v2/matches/SportChips';
import { DateScroller } from '@/components/v2/matches/DateScroller';
import { ValueOnlyToggle } from '@/components/v2/matches/ValueOnlyToggle';
import { FilterSidebar } from '@/components/v2/matches/FilterSidebar';
import { MatchesTableDesktop } from '@/components/v2/matches/MatchesTableDesktop';
import { MatchesListMobile } from '@/components/v2/matches/MatchesListMobile';
import { Skeleton } from '@/components/ui/skeleton';
import { useMatchesOfDay } from '@/hooks/v2/useMatchesOfDay';
import type { League } from '@/types/v2/common';
import type { MatchesFilters, SignalKind, Sport } from '@/types/v2/matches';

const DESKTOP_BREAKPOINT = 768;

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

function parseList<T extends string>(raw: string | null): T[] | undefined {
  if (!raw) return undefined;
  const list = raw.split(',').map((s) => s.trim()).filter(Boolean) as T[];
  return list.length > 0 ? list : undefined;
}

function sportChipsValue(sports: Sport[] | undefined): SportChipsValue {
  if (!sports || sports.length !== 1) return 'all';
  return sports[0];
}

export function MatchesV2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const isDesktop = useIsDesktop();

  const date = searchParams.get('date') ?? todayIso();
  const sports = parseList<Sport>(searchParams.get('sport'));
  const leagues = parseList<League>(searchParams.get('league'));
  const signals = parseList<SignalKind>(searchParams.get('signals'));
  const valueOnly = searchParams.get('value_only') === 'true';
  const sort = (searchParams.get('sort') as MatchesFilters['sort']) ?? undefined;

  const filters: MatchesFilters = useMemo(
    () => ({ date, sports, leagues, signals, valueOnly: valueOnly || undefined, sort }),
    [date, sports, leagues, signals, valueOnly, sort],
  );

  const { data, isLoading, isError } = useMatchesOfDay(filters);

  const updateParams = useCallback(
    (mutator: (p: URLSearchParams) => void) => {
      const next = new URLSearchParams(searchParams);
      mutator(next);
      setSearchParams(next, { replace: false });
    },
    [searchParams, setSearchParams],
  );

  const onDateChange = (iso: string) => {
    updateParams((p) => {
      p.set('date', iso);
    });
  };

  const onSportChipsChange = (v: SportChipsValue) => {
    updateParams((p) => {
      if (v === 'all') p.delete('sport');
      else p.set('sport', v);
    });
  };

  const onFiltersChange = (next: MatchesFilters) => {
    updateParams((p) => {
      if (next.sports?.length) p.set('sport', next.sports.join(','));
      else p.delete('sport');
      if (next.leagues?.length) p.set('league', next.leagues.join(','));
      else p.delete('league');
      if (next.signals?.length) p.set('signals', next.signals.join(','));
      else p.delete('signals');
      if (next.valueOnly) p.set('value_only', 'true');
      else p.delete('value_only');
      if (next.sort) p.set('sort', next.sort);
      else p.delete('sort');
    });
  };

  const onValueOnlyChange = (v: boolean) => {
    updateParams((p) => {
      if (v) p.set('value_only', 'true');
      else p.delete('value_only');
    });
  };

  const matches = data?.matches ?? [];
  const isEmpty = !isLoading && !isError && matches.length === 0;

  return (
    <main
      data-testid="matches-v2-page"
      data-date={date}
      data-sport={sports?.join(',') ?? 'all'}
      data-leagues={leagues?.join(',') ?? ''}
      aria-label="Matchs du jour"
      className="mx-auto max-w-7xl px-4 md:px-8 py-4 md:py-6 space-y-4"
    >
      {!isDesktop && (
        <>
          <header className="flex items-center justify-between">
            <h1 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>
              Matchs
            </h1>
          </header>
          <SportChips
            value={sportChipsValue(sports)}
            onChange={onSportChipsChange}
            counts={
              data
                ? {
                    all: data.counts.total,
                    football: data.counts.bySport.football,
                    nhl: data.counts.bySport.nhl,
                  }
                : undefined
            }
          />
          <DateScroller value={date} onChange={onDateChange} />
          <div className="flex items-center justify-between">
            <ValueOnlyToggle value={valueOnly} onChange={onValueOnlyChange} />
          </div>
          {isLoading && (
            <div className="space-y-2" data-testid="matches-loading">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          )}
          {isError && (
            <p
              data-testid="matches-error"
              className="rounded-lg p-6 text-center text-sm"
              style={{
                border: '1px solid var(--border)',
                background: 'var(--surface)',
                color: 'var(--danger, #ef4444)',
              }}
            >
              Impossible de charger les matchs. Réessayez dans un instant.
            </p>
          )}
          {isEmpty && (
            <p
              data-testid="matches-empty"
              className="rounded-lg p-6 text-center text-sm"
              style={{
                border: '1px solid var(--border)',
                background: 'var(--surface)',
                color: 'var(--text-muted)',
              }}
            >
              Pas de match ce jour.
            </p>
          )}
          {!isLoading && !isError && !isEmpty && <MatchesListMobile matches={matches} />}
        </>
      )}

      {isDesktop && (
        <>
          <DateScroller value={date} onChange={onDateChange} />
          <div className="grid gap-6 md:grid-cols-[220px_1fr]">
            <FilterSidebar
              filters={filters}
              onChange={onFiltersChange}
              matchesByLeague={
                data
                  ? (Object.fromEntries(
                      Object.entries(data.counts.byLeague),
                    ) as Partial<Record<League, number>>)
                  : undefined
              }
            />
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <SportChips
                  value={sportChipsValue(sports)}
                  onChange={onSportChipsChange}
                  counts={
                    data
                      ? {
                          all: data.counts.total,
                          football: data.counts.bySport.football,
                          nhl: data.counts.bySport.nhl,
                        }
                      : undefined
                  }
                />
                <ValueOnlyToggle value={valueOnly} onChange={onValueOnlyChange} />
              </div>
              {isLoading && (
                <div className="space-y-2" data-testid="matches-loading">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              )}
              {isError && (
                <p
                  data-testid="matches-error"
                  className="rounded-lg p-6 text-center text-sm"
                  style={{
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    color: 'var(--danger, #ef4444)',
                  }}
                >
                  Impossible de charger les matchs. Réessayez dans un instant.
                </p>
              )}
              {isEmpty && (
                <p
                  data-testid="matches-empty"
                  className="rounded-lg p-6 text-center text-sm"
                  style={{
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    color: 'var(--text-muted)',
                  }}
                >
                  Pas de match ce jour.
                </p>
              )}
              {!isLoading && !isError && !isEmpty && <MatchesTableDesktop matches={matches} />}
            </div>
          </div>
        </>
      )}
    </main>
  );
}

export default MatchesV2;
