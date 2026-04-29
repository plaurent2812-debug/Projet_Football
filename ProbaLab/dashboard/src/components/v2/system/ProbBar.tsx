export interface ProbBarProps {
  home: number | null | undefined;
  draw: number | null | undefined;
  away: number | null | undefined;
  homeLabel: string;
  awayLabel: string;
  'data-testid'?: string;
}

function pct(n: number): number {
  return Math.round(n * 100);
}

function finiteOrZero(n: number | null | undefined): number {
  return typeof n === 'number' && Number.isFinite(n) ? n : 0;
}

export function ProbBar({
  home,
  draw,
  away,
  homeLabel,
  awayLabel,
  'data-testid': dataTestId = 'prob-bar',
}: ProbBarProps) {
  // Tolerate missing probabilities (e.g. NHL fixtures without a prediction yet).
  // Normalize small rounding errors silently; treat sum=0 as a neutral bar.
  const hasDraw = typeof draw === 'number' && Number.isFinite(draw);
  let safeHome = finiteOrZero(home);
  let safeDraw = finiteOrZero(draw);
  let safeAway = finiteOrZero(away);
  const rawSum = safeHome + safeDraw + safeAway;
  if (rawSum <= 0) {
    return (
      <div
        role="img"
        aria-label="Probabilités non disponibles"
        data-testid={dataTestId}
        className="flex h-2 w-full rounded overflow-hidden"
        style={{ background: 'var(--surface-2)' }}
      />
    );
  }
  // Normalize if off from 1 (rounding) by renormalizing proportionally.
  safeHome = safeHome / rawSum;
  safeDraw = safeDraw / rawSum;
  safeAway = safeAway / rawSum;
  const max = Math.max(safeHome, safeDraw, safeAway);
  const dominant = safeHome === max ? 'home' : safeDraw === max ? 'draw' : 'away';
  const label = hasDraw
    ? `${homeLabel} ${pct(safeHome)}%, Nul ${pct(safeDraw)}%, ${awayLabel} ${pct(safeAway)}%`
    : `${homeLabel} ${pct(safeHome)}%, ${awayLabel} ${pct(safeAway)}%`;

  const bg = (isDom: boolean, muted: boolean): string => {
    if (isDom) return 'var(--primary)';
    return muted ? 'var(--surface-2)' : '#334155';
  };

  return (
    <div
      role="img"
      data-testid={dataTestId}
      aria-label={label}
      style={{
        display: 'flex',
        width: '100%',
        height: 8,
        borderRadius: 'var(--radius-sm)',
        overflow: 'hidden',
        background: 'var(--surface-2)',
      }}
    >
      <span
        data-segment="home"
        data-testid="segment-home"
        data-dominant={dominant === 'home'}
        style={{ width: `${pct(safeHome)}%`, background: bg(dominant === 'home', false) }}
      />
      {hasDraw && (
        <span
          data-segment="draw"
          data-testid="segment-draw"
          data-dominant={dominant === 'draw'}
          style={{ width: `${pct(safeDraw)}%`, background: bg(dominant === 'draw', true) }}
        />
      )}
      <span
        data-segment="away"
        data-testid="segment-away"
        data-dominant={dominant === 'away'}
        style={{ width: `${pct(safeAway)}%`, background: bg(dominant === 'away', false) }}
      />
    </div>
  );
}

export default ProbBar;
