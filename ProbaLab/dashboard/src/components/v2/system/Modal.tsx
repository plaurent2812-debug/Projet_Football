import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import type { ReactNode } from 'react';

export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** Optional descriptive text shown below the title — used for aria-describedby. */
  description?: string;
  children: ReactNode;
  /** Optional footer (submit / cancel buttons). */
  footer?: ReactNode;
  'data-testid'?: string;
}

/**
 * Lightweight accessible modal primitive.
 *
 * We keep this local rather than pulling `@radix-ui/react-dialog` because
 * the footprint already ships Radix for other primitives only when needed
 * and the dashboard bundle is tight. The primitive renders a portal with
 * a backdrop, a `role="dialog"` panel, focus trap and Escape-to-close.
 *
 * The title is wired to `aria-labelledby` and the optional description
 * to `aria-describedby`, so jest-axe passes out of the box.
 */
export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  'data-testid': dataTestId = 'modal',
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const descId = useId();

  // Focus trap + restore previous focus on close.
  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    if (!panel) return;

    // Move focus to the first interactive element in the panel (or the
    // panel itself as a fallback).
    const focusables = panel.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusables[0];
    (first ?? panel).focus();

    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onOpenChange(false);
        return;
      }
      if (e.key !== 'Tab') return;
      const current = panel?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!current || current.length === 0) return;
      const firstEl = current[0];
      const lastEl = current[current.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    }

    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('keydown', handleKey);
      previousFocus.current?.focus?.();
    };
  }, [open, onOpenChange]);

  if (!open) return null;

  const content = (
    <div
      data-testid={dataTestId}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div
        aria-hidden="true"
        onClick={() => onOpenChange(false)}
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        tabIndex={-1}
        className="relative z-10 w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl focus:outline-none dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2
              id={titleId}
              className="text-lg font-semibold text-slate-900 dark:text-white"
            >
              {title}
            </h2>
            {description && (
              <p
                id={descId}
                className="mt-1 text-sm text-slate-500 dark:text-slate-400"
              >
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            aria-label="Fermer"
            onClick={() => onOpenChange(false)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-700 focus-visible:outline focus-visible:outline-2 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <div className="mt-4">{children}</div>
        {footer && (
          <div className="mt-6 flex flex-wrap items-center justify-end gap-2">
            {footer}
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(content, document.body);
}

export default Modal;
