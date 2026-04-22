import { Link } from 'react-router-dom';
import type { MatchRowData } from '@/types/v2/matches';

interface Props {
  matches: MatchRowData[];
  'data-testid'?: string;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    });
  } catch {
    return '--:--';
  }
}

export function PreviewBlurMatches({
  matches,
  'data-testid': dataTestId = 'preview-blur-matches',
}: Props) {
  const preview = matches.slice(0, 3);
  return (
    <section
      data-testid={dataTestId}
      className="relative rounded-xl p-4"
      style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
    >
      <ul className="space-y-2" aria-hidden="true">
        {preview.map((m) => (
          <li
            key={m.fixtureId}
            data-testid="preview-blur-row"
            className="flex items-center gap-3 py-2"
            style={{ filter: 'blur(4px)' }}
          >
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {formatTime(m.kickoffUtc)}
            </span>
            <span className="text-sm" style={{ color: 'var(--text)' }}>
              {m.home.short} vs {m.away.short}
            </span>
            <span
              className="ml-auto text-sm tabular-nums"
              style={{ color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
            >
              {Math.round(m.prob1x2.home * 100)}% / {Math.round(m.prob1x2.draw * 100)}% /{' '}
              {Math.round(m.prob1x2.away * 100)}%
            </span>
          </li>
        ))}
      </ul>
      <div
        className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-4 text-center"
        style={{ background: 'rgba(10, 14, 26, 0.55)', borderRadius: 'var(--radius-md, 12px)' }}
      >
        <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
          Crée un compte gratuit pour voir les probabilités
        </p>
        <Link
          to="/register"
          className="rounded-md px-4 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2"
          style={{ background: 'var(--primary)', color: '#0a0e1a' }}
        >
          S'inscrire
        </Link>
      </div>
    </section>
  );
}

export default PreviewBlurMatches;
