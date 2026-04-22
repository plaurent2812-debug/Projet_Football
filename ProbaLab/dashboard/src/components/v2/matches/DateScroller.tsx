import { useMemo, useRef } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Props {
  value: string; // YYYY-MM-DD
  onChange: (v: string) => void;
  'data-testid'?: string;
}

function toIso(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function fmtLabel(d: Date, isToday: boolean): { top: string; bottom: string } {
  if (isToday) {
    return { top: "AUJOURD'HUI", bottom: '' };
  }
  const weekday = d.toLocaleDateString('fr-FR', { weekday: 'short', timeZone: 'UTC' });
  const num = d.toLocaleDateString('fr-FR', { day: '2-digit', timeZone: 'UTC' });
  return { top: weekday.toUpperCase(), bottom: num };
}

export function DateScroller({
  value,
  onChange,
  'data-testid': dataTestId = 'date-scroller',
}: Props) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  const days = useMemo(() => {
    const now = new Date();
    const todayIso = toIso(now);
    const list: { iso: string; date: Date; isToday: boolean }[] = [];
    for (let i = -1; i <= 5; i += 1) {
      const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + i));
      const iso = toIso(d);
      list.push({ iso, date: d, isToday: iso === todayIso });
    }
    return list;
  }, []);

  const scrollBy = (delta: number) => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollBy({ left: delta, behavior: 'smooth' });
    }
  };

  return (
    <div
      data-testid={dataTestId}
      className="flex items-center gap-2"
      role="group"
      aria-label="Sélecteur de date"
    >
      <button
        type="button"
        onClick={() => scrollBy(-120)}
        aria-label="Jour précédent"
        className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-full md:inline-flex"
        style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
      >
        <ChevronLeft aria-hidden="true" size={16} />
      </button>
      <div
        ref={scrollerRef}
        className="flex flex-1 items-center gap-2 overflow-x-auto scroll-smooth"
        style={{ scrollbarWidth: 'none' }}
      >
        {days.map(({ iso, date, isToday }) => {
          const { top, bottom } = fmtLabel(date, isToday);
          const selected = iso === value;
          return (
            <button
              key={iso}
              type="button"
              data-role="date"
              data-iso={iso}
              onClick={() => onChange(iso)}
              aria-pressed={selected}
              className="flex min-w-[72px] shrink-0 flex-col items-center rounded-lg px-3 py-2 text-xs transition-colors focus-visible:outline focus-visible:outline-2"
              style={{
                border: '1px solid var(--border)',
                background: selected
                  ? isToday
                    ? 'var(--primary)'
                    : 'var(--surface-raised, var(--surface))'
                  : 'var(--surface)',
                color: selected && isToday ? '#ffffff' : 'var(--text)',
                fontWeight: isToday ? 600 : 400,
              }}
            >
              <span className="font-semibold tracking-wide">{top}</span>
              {bottom && (
                <span className="mt-0.5 text-[11px]" style={{ opacity: 0.8 }}>
                  {bottom}
                </span>
              )}
            </button>
          );
        })}
      </div>
      <button
        type="button"
        onClick={() => scrollBy(120)}
        aria-label="Jour suivant"
        className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-full md:inline-flex"
        style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
      >
        <ChevronRight aria-hidden="true" size={16} />
      </button>
    </div>
  );
}

export default DateScroller;
