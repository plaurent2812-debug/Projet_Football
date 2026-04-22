import { useEffect, useRef, useState } from 'react';
import {
  Bell,
  Clock,
  Edit2,
  MoreHorizontal,
  Star,
  Trash2,
  TrendingDown,
  Trophy,
  Wallet,
  Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { RuleChip } from '@/components/v2/system/RuleChip';
import { useToggleRule } from '@/hooks/v2/useNotificationRules';
import type {
  ConditionType,
  NotificationRule,
  RuleCondition,
} from '@/lib/v2/schemas/rules';

export interface RuleRowProps {
  rule: NotificationRule;
  onEdit: (rule: NotificationRule) => void;
  onDeleteRequest: (rule: NotificationRule) => void;
  'data-testid'?: string;
}

const ICON_BY_TYPE: Record<
  ConditionType,
  { icon: LucideIcon; key: string }
> = {
  edge_min: { icon: Zap, key: 'zap' },
  league_in: { icon: Trophy, key: 'trophy' },
  sport: { icon: Trophy, key: 'trophy' },
  confidence: { icon: Star, key: 'star' },
  kickoff_within: { icon: Star, key: 'star' },
  bankroll_drawdown: { icon: Wallet, key: 'wallet' },
};

function humanReadableCondition(c: RuleCondition): string {
  switch (c.type) {
    case 'edge_min':
      return `Edge ≥ ${c.value}%`;
    case 'league_in':
      return `Ligue ∈ ${c.value.join(', ')}`;
    case 'sport':
      return `Sport = ${c.value}`;
    case 'confidence':
      return `Confiance = ${c.value}`;
    case 'kickoff_within':
      return `Coup d’envoi < ${c.value} h`;
    case 'bankroll_drawdown':
      return `Drawdown ≥ ${c.value}%`;
  }
}

function humanReadableChannel(c: NotificationRule['channels'][number]): string {
  if (c === 'telegram') return 'Telegram';
  if (c === 'email') return 'Email';
  return 'Push';
}

/**
 * Compact card for a single notification rule. Renders the primary
 * icon (derived from the first condition), the name, the chips
 * (QUAND / ET / NOTIFIER) via `RuleChip`, the on/off switch and a
 * kebab menu with Modifier / Supprimer actions.
 *
 * The switch drives `useToggleRule` directly. Modifier and Supprimer
 * bubble up so the parent can show the modals it owns.
 */
export function RuleRow({
  rule,
  onEdit,
  onDeleteRequest,
  'data-testid': dataTestId = 'rule-list-item',
}: RuleRowProps) {
  const toggle = useToggleRule(rule.id ?? '');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const primary = rule.conditions[0];
  const iconMeta = primary
    ? ICON_BY_TYPE[primary.type]
    : { icon: Bell, key: 'bell' };
  const Icon = iconMeta.icon;

  const hasDrawdown = rule.conditions.some(
    (c) => c.type === 'bankroll_drawdown',
  );
  const WarnIcon = hasDrawdown ? TrendingDown : null;

  // Close kebab menu on outside click.
  useEffect(() => {
    if (!menuOpen) return;
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [menuOpen]);

  const onToggle = () => {
    toggle.mutate(!rule.enabled);
  };

  return (
    <article
      data-testid={dataTestId}
      className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex flex-1 items-start gap-3">
        <div
          data-testid="rule-row-icon"
          data-icon={iconMeta.key}
          className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400"
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-base font-semibold text-slate-900 dark:text-white">
              {rule.name}
            </h3>
            {WarnIcon && (
              <WarnIcon
                className="h-4 w-4 text-rose-500"
                aria-hidden="true"
              />
            )}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <RuleChip variant="label" text="QUAND" />
            {rule.conditions.map((c, idx) => (
              <RuleChip
                key={`${c.type}-${idx}`}
                variant="condition"
                text={humanReadableCondition(c)}
              />
            ))}
            {rule.conditions.length > 1 && (
              <>
                <RuleChip variant="label" text="ET" />
                <span
                  className="text-xs font-medium text-slate-400"
                  aria-hidden="true"
                >
                  {rule.logic}
                </span>
              </>
            )}
            <RuleChip variant="label" text="NOTIFIER" />
            {rule.channels.map((c) => (
              <RuleChip
                key={c}
                variant="action"
                text={humanReadableChannel(c)}
              />
            ))}
            {rule.action.pauseSuggestion && (
              <RuleChip variant="action" text="Suggérer pause" />
            )}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          role="switch"
          aria-checked={rule.enabled}
          aria-label={`Activer ${rule.name}`}
          onClick={onToggle}
          disabled={toggle.isPending}
          className={
            rule.enabled
              ? 'relative inline-flex h-5 w-9 items-center rounded-full bg-emerald-500 transition disabled:cursor-not-allowed disabled:opacity-50'
              : 'relative inline-flex h-5 w-9 items-center rounded-full bg-slate-300 transition disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-700'
          }
        >
          <span
            className={
              rule.enabled
                ? 'block h-4 w-4 translate-x-4 rounded-full bg-white transition-transform'
                : 'block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform'
            }
          />
        </button>
        <div ref={menuRef} className="relative">
          <button
            type="button"
            aria-label={`Menu ${rule.name}`}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-700 focus-visible:outline focus-visible:outline-2 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
          </button>
          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-9 z-20 w-40 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  onEdit(rule);
                }}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                <Edit2 className="h-4 w-4" aria-hidden="true" />
                Modifier
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  onDeleteRequest(rule);
                }}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Supprimer
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

export default RuleRow;
