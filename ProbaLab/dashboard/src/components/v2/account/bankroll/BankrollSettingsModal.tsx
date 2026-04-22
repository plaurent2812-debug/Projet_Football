import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  bankrollSettingsSchema,
  type BankrollSettings,
} from '@/lib/v2/schemas/bankroll';
import {
  useBankrollSettings,
  useUpdateBankrollSettings,
} from '@/hooks/v2/useBankrollSettings';
import { Modal } from '@/components/v2/system/Modal';

export interface BankrollSettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  'data-testid'?: string;
}

const KELLY_OPTIONS: Array<{ value: 0.1 | 0.25 | 0.5; label: string }> = [
  { value: 0.1, label: 'Conservateur (0.1)' },
  { value: 0.25, label: 'Équilibré (0.25)' },
  { value: 0.5, label: 'Agressif (0.5)' },
];

/**
 * Bankroll settings dialog — edits the three tunables that drive the
 * value-betting engine : initial stake (euros), Kelly fraction, and
 * per-bet cap (percent of bankroll).
 *
 * Prefills from `useBankrollSettings` on open and persists via
 * `useUpdateBankrollSettings`. On success the modal closes and the
 * bankroll caches are invalidated by the mutation hook.
 */
export function BankrollSettingsModal({
  open,
  onOpenChange,
  'data-testid': dataTestId = 'bankroll-settings-modal',
}: BankrollSettingsModalProps) {
  const { data, isLoading } = useBankrollSettings();
  const update = useUpdateBankrollSettings();

  const form = useForm<BankrollSettings>({
    resolver: zodResolver(bankrollSettingsSchema),
    defaultValues: {
      initialStake: 1000,
      kellyFraction: 0.25,
      stakeCapPct: 5,
    },
  });

  useEffect(() => {
    if (!open || !data) return;
    form.reset({
      initialStake: data.initialStake,
      kellyFraction: data.kellyFraction,
      stakeCapPct: data.stakeCapPct,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, data]);

  const onSubmit = form.handleSubmit(async (values) => {
    await update.mutateAsync(values);
    onOpenChange(false);
  });

  const fieldError = (name: keyof BankrollSettings): string | undefined =>
    form.formState.errors[name]?.message as string | undefined;

  const stakeCapValue = form.watch('stakeCapPct');

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Paramètres du bankroll"
      description="Ces valeurs pilotent la mise suggérée (Kelly fractionnel)."
      data-testid={dataTestId}
      footer={
        !isLoading && (
          <>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Annuler
            </button>
            <button
              type="submit"
              form="bankroll-settings-form"
              disabled={update.isPending}
              className="inline-flex items-center rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {update.isPending ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </>
        )
      }
    >
      {isLoading ? (
        <div
          data-testid="bankroll-settings-skeleton"
          aria-busy="true"
          aria-label="Chargement des paramètres"
          className="space-y-4"
        >
          <div className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />
          <div className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />
        </div>
      ) : (
        <form
          id="bankroll-settings-form"
          onSubmit={onSubmit}
          className="space-y-5"
          noValidate
        >
          <div>
            <label
              htmlFor="bankroll-initial"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Mise initiale (€)
            </label>
            <input
              id="bankroll-initial"
              type="number"
              step="1"
              min={1}
              {...form.register('initialStake', { valueAsNumber: true })}
              aria-invalid={fieldError('initialStake') ? 'true' : 'false'}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            />
            {fieldError('initialStake') && (
              <p className="mt-1 text-xs text-rose-600" role="alert">
                {fieldError('initialStake')}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="bankroll-kelly"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Fraction de Kelly
            </label>
            <select
              id="bankroll-kelly"
              {...form.register('kellyFraction', { valueAsNumber: true })}
              aria-invalid={fieldError('kellyFraction') ? 'true' : 'false'}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            >
              {KELLY_OPTIONS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
            {fieldError('kellyFraction') && (
              <p className="mt-1 text-xs text-rose-600" role="alert">
                {fieldError('kellyFraction')}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="bankroll-stake-cap"
              className="flex items-center justify-between text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              <span>Plafond de mise par pari</span>
              <span
                className="tabular-nums text-xs text-slate-500 dark:text-slate-400"
                data-testid="stake-cap-display"
              >
                {Number(stakeCapValue ?? 0).toFixed(1)}%
              </span>
            </label>
            <input
              id="bankroll-stake-cap"
              type="range"
              step="0.5"
              min={0.5}
              max={25}
              {...form.register('stakeCapPct', { valueAsNumber: true })}
              aria-invalid={fieldError('stakeCapPct') ? 'true' : 'false'}
              className="mt-2 w-full accent-emerald-500"
            />
            {fieldError('stakeCapPct') && (
              <p className="mt-1 text-xs text-rose-600" role="alert">
                {fieldError('stakeCapPct')}
              </p>
            )}
          </div>
        </form>
      )}
    </Modal>
  );
}

export default BankrollSettingsModal;
