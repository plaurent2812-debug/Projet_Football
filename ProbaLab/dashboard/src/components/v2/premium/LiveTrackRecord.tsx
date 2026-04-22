import { lazy, Suspense, useMemo, useState } from 'react';
import { Radio } from 'lucide-react';
import { useTrackRecordLive } from '@/hooks/v2/useTrackRecordLive';
import { StatTile } from '@/components/v2/system/StatTile';
import type { StatTone } from '@/components/v2/system/StatTile';
import type { TrackRecordPoint } from '@/hooks/v2/useTrackRecordLive';

// Lazy boundary so Recharts lives in its own chunk.
const ROIChart = lazy(() => import('./ROIChart'));

type Period = '30j' | '90j' | '1an';

interface Props {
  /** Anchor id — the Premium hero smooth-scrolls to this value. */
  id?: string;
  'data-testid'?: string;
}

function minutesSince(iso: string | undefined): number {
  if (!iso) return 0;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return 0;
  return Math.max(0, Math.round((Date.now() - t) / 60_000));
}

function sliceForPeriod(curve: TrackRecordPoint[], period: Period): TrackRecordPoint[] {
  if (period === '30j') return curve.slice(-30);
  if (period === '90j') return curve;
  // 1-year view is gracefully degraded to 90j until the backend exposes a longer window.
  return curve;
}

function toneForDelta(value: number): StatTone {
  if (value > 0) return 'positive';
  if (value < 0) return 'negative';
  return 'neutral';
}

/**
 * Live track record section — the killer feature of the Premium landing.
 *
 * Composition:
 * - Emerald eyebrow + pulsing LIVE dot + last-updated mention.
 * - 4 StatTiles (CLV 30j, ROI 90j, Brier 30j, Safe 90j).
 * - Period toggle (30j / 90j / 1 an) — purely local UI state.
 * - Area chart (lazy-loaded) rendering cumulative ROI.
 * - Transparency footer linking to the public audit repo.
 */
export function LiveTrackRecord({
  id = 'track-record',
  'data-testid': dataTestId = 'live-track-record',
}: Props) {
  const { data, isLoading, isError } = useTrackRecordLive();
  const [period, setPeriod] = useState<Period>('90j');

  const chartData = useMemo(
    () => (data ? sliceForPeriod(data.roiCurve90d, period) : []),
    [data, period],
  );

  if (isLoading) {
    return (
      <section
        id={id}
        aria-labelledby="live-track-record-title"
        data-testid={dataTestId}
        className="py-16"
      >
        <div
          data-testid="live-track-record-skeleton"
          className="grid animate-pulse gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              style={{
                height: 92,
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface)',
                border: '1px solid var(--border)',
              }}
            />
          ))}
        </div>
      </section>
    );
  }

  if (isError || !data) {
    return (
      <section
        id={id}
        aria-labelledby="live-track-record-title"
        data-testid={dataTestId}
        className="py-16 text-center"
      >
        <h2 id="live-track-record-title" className="text-xl font-semibold" style={{ color: 'var(--text)' }}>
          La preuve, pas les promesses.
        </h2>
        <p className="mt-3 text-sm" style={{ color: 'var(--text-muted)' }}>
          Impossible de charger le track record live. Réessayez dans quelques instants.
        </p>
      </section>
    );
  }

  const updatedAgo = minutesSince(data.lastUpdatedAt);
  const periods: Period[] = ['30j', '90j', '1an'];

  return (
    <section
      id={id}
      aria-labelledby="live-track-record-title"
      data-testid={dataTestId}
      className="py-16 space-y-8"
    >
      <header className="space-y-3 text-center">
        <span
          className="inline-flex items-center gap-2 text-xs font-semibold tracking-[0.2em]"
          style={{ color: 'var(--primary)' }}
        >
          <Radio size={14} aria-hidden="true" />
          TRACK RECORD LIVE
        </span>
        <div className="flex items-center justify-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span
            data-testid="live-dot"
            aria-hidden="true"
            className="inline-block rounded-full animate-pulse"
            style={{
              width: 8,
              height: 8,
              background: 'var(--primary)',
            }}
          />
          <span className="uppercase tracking-widest" style={{ color: 'var(--primary)' }}>LIVE</span>
          <span aria-hidden="true">·</span>
          <span>Dernière MAJ il y a {updatedAgo} min</span>
        </div>
        <h2
          id="live-track-record-title"
          className="text-2xl md:text-4xl font-bold tracking-tight"
          style={{ color: 'var(--text)' }}
        >
          La preuve, pas les promesses.
        </h2>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="CLV 30j"
          value={`${data.clv30d >= 0 ? '+' : ''}${data.clv30d.toFixed(1)}%`}
          tone={toneForDelta(data.clv30d)}
          data-testid="tile-clv"
        />
        <StatTile
          label="ROI 90j"
          value={`${data.roi90d >= 0 ? '+' : ''}${data.roi90d.toFixed(1)}%`}
          tone={toneForDelta(data.roi90d)}
          data-testid="tile-roi"
        />
        <StatTile
          label="Brier 30j"
          value={data.brier30d.toFixed(3)}
          tone="neutral"
          data-testid="tile-brier"
        />
        <StatTile
          label="Safe 90j"
          value={`${data.safeRate90d.toFixed(1)}%`}
          tone="neutral"
          data-testid="tile-safe"
        />
      </div>

      <div
        className="flex flex-col gap-4"
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-4, 16px)',
        }}
      >
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
            ROI cumulé
          </p>
          <div role="group" aria-label="Sélection de période" className="inline-flex gap-1">
            {periods.map((p) => {
              const active = p === period;
              return (
                <button
                  key={p}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setPeriod(p)}
                  className="rounded-md px-3 py-1 text-xs font-semibold focus-visible:outline focus-visible:outline-2"
                  style={{
                    background: active ? 'var(--primary)' : 'transparent',
                    color: active ? '#0a0e1a' : 'var(--text-muted)',
                    border: active ? '1px solid var(--primary)' : '1px solid var(--border)',
                  }}
                >
                  {p === '1an' ? '1 an' : p}
                </button>
              );
            })}
          </div>
        </div>
        <Suspense
          fallback={
            <div
              data-testid="roi-chart-fallback"
              style={{
                height: 280,
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface)',
                border: '1px dashed var(--border)',
              }}
            />
          }
        >
          <ROIChart data={chartData} />
        </Suspense>
      </div>

      <p className="text-center text-xs" style={{ color: 'var(--text-muted)' }}>
        Toutes les métriques sont calculées sur l'intégralité des paris, sans cherry-picking.{' '}
        Source :{' '}
        <a
          href="https://github.com/probalab/track-record"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--primary)', textDecoration: 'underline' }}
        >
          github.com/probalab/track-record
        </a>
      </p>
    </section>
  );
}

export default LiveTrackRecord;
