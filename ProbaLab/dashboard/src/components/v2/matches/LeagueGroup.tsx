import type { ReactNode } from 'react';
import type { LeagueRef } from '@/types/v2/matches';

interface Props {
  league: LeagueRef;
  count: number;
  children: ReactNode;
  'data-testid'?: string;
}

export function LeagueGroup({
  league,
  count,
  children,
  'data-testid': dataTestId = 'league-group',
}: Props) {
  return (
    <section
      data-testid={dataTestId}
      className="rounded-xl overflow-hidden"
      style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
    >
      <h3
        className="flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wide"
        style={{ backgroundColor: league.color, color: '#ffffff' }}
      >
        {league.name}
        <span className="ml-auto text-[11px]" style={{ opacity: 0.8 }}>
          {count}
        </span>
      </h3>
      <div>{children}</div>
    </section>
  );
}

export default LeagueGroup;
