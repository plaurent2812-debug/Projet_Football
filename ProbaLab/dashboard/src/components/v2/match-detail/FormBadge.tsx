import type { Outcome } from '../../../types/v2/match-detail';

/**
 * FormBadge — 5 pastilles colorées (V/N/D) pour la forme récente d'une équipe.
 *
 * - W (Win) → V (victoire), vert
 * - D (Draw) → N (nul), gris
 * - L (Loss) → D (défaite), rouge
 *
 * Utilisé dans MatchHero / MatchHeroCompact.
 */
const COLOR: Record<Outcome, string> = {
  W: 'bg-emerald-500',
  D: 'bg-slate-400',
  L: 'bg-rose-500',
};

const READABLE: Record<Outcome, string> = {
  W: 'V',
  D: 'N',
  L: 'D',
};

const SIZE: Record<NonNullable<FormBadgeProps['size']>, string> = {
  sm: 'h-2 w-2',
  md: 'h-2.5 w-2.5',
};

export interface FormBadgeProps {
  form: Outcome[];
  size?: 'sm' | 'md';
  'data-testid'?: string;
}

export function FormBadge({
  form,
  size = 'md',
  'data-testid': dataTestId,
}: FormBadgeProps) {
  const readable = form.map((o) => READABLE[o]).join(' ');
  const label = readable ? `Forme récente : ${readable}` : 'Forme récente :';
  return (
    <div
      role="img"
      aria-label={label}
      data-testid={dataTestId}
      className="flex items-center gap-1"
    >
      {form.map((o, i) => (
        <span
          key={i}
          data-testid="form-dot"
          aria-hidden="true"
          className={`inline-block rounded-full ${SIZE[size]} ${COLOR[o]}`}
        />
      ))}
    </div>
  );
}

export default FormBadge;
