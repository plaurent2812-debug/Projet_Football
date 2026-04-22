import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { addBetSchema, type AddBet } from '@/lib/v2/schemas/bets';
import { useAddBet } from '@/hooks/v2/useBankrollBets';
import { Modal } from '@/components/v2/system/Modal';

export interface PrefilledFixture {
  fixture_id: string;
  match_title: string;
  market: string;
  selection: string;
  odds: number;
  /** Stake suggestion from Kelly — optional prefill. */
  stake?: number;
}

export interface AddBetModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  prefilledFixture?: PrefilledFixture;
  'data-testid'?: string;
}

const MARKET_OPTIONS = [
  { value: '1X2', label: '1X2' },
  { value: 'DC', label: 'Double Chance' },
  { value: 'BTTS', label: 'Les deux équipes marquent' },
  { value: 'O/U 2.5', label: 'Plus/Moins 2.5' },
  { value: 'O/U 1.5', label: 'Plus/Moins 1.5' },
  { value: 'O/U 3.5', label: 'Plus/Moins 3.5' },
  { value: 'Handicap', label: 'Handicap' },
  { value: 'Score', label: 'Score exact' },
  { value: 'Buteur', label: 'Buteur' },
];

/**
 * Add-a-bet dialog. Form state is driven by `react-hook-form` with
 * `zodResolver(addBetSchema)`; on success the parent receives an
 * `onOpenChange(false)` and the bankroll query cache is invalidated
 * by `useAddBet`.
 *
 * `prefilledFixture` is used to drop in from a match page CTA ("Suivre
 * dans mon bankroll"). When omitted, the form starts empty except for
 * the default market value.
 */
export function AddBetModal({
  open,
  onOpenChange,
  prefilledFixture,
  'data-testid': dataTestId = 'add-bet-modal',
}: AddBetModalProps) {
  const addBet = useAddBet();

  const defaultValues: Partial<AddBet> = {
    fixtureLabel: prefilledFixture?.match_title ?? '',
    market: prefilledFixture?.market ?? '1X2',
    pick: prefilledFixture?.selection ?? '',
    odds: prefilledFixture?.odds,
    stake: prefilledFixture?.stake,
    placedAt: new Date().toISOString(),
  };

  const form = useForm<AddBet>({
    resolver: zodResolver(addBetSchema),
    defaultValues,
  });

  // Re-sync when a new prefill arrives while the modal is still open.
  useEffect(() => {
    if (!open) return;
    form.reset(defaultValues);
    // Only depend on prefilledFixture identity + open flag — resetting
    // on every keystroke would trash in-progress input.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefilledFixture, open]);

  const onSubmit = form.handleSubmit(async (values) => {
    await addBet.mutateAsync({
      fixture_id: prefilledFixture?.fixture_id ?? `manual-${Date.now()}`,
      match_title: values.fixtureLabel,
      market: values.market,
      selection: values.pick,
      odds: values.odds,
      stake: values.stake,
      placed_at: values.placedAt,
    });
    onOpenChange(false);
    form.reset();
  });

  const fieldError = (name: keyof AddBet): string | undefined =>
    form.formState.errors[name]?.message as string | undefined;

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Ajouter un pari"
      description="Enregistre un pari dans ton bankroll."
      data-testid={dataTestId}
      footer={
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
            form="add-bet-form"
            disabled={addBet.isPending}
            className="inline-flex items-center rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {addBet.isPending ? 'Ajout…' : 'Ajouter'}
          </button>
        </>
      }
    >
      <form
        id="add-bet-form"
        onSubmit={onSubmit}
        className="space-y-4"
        noValidate
      >
        <Field
          id="add-bet-match"
          label="Match"
          error={fieldError('fixtureLabel')}
        >
          <input
            id="add-bet-match"
            type="text"
            {...form.register('fixtureLabel')}
            aria-invalid={fieldError('fixtureLabel') ? 'true' : 'false'}
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          />
        </Field>

        <Field id="add-bet-market" label="Marché" error={fieldError('market')}>
          <select
            id="add-bet-market"
            {...form.register('market')}
            aria-invalid={fieldError('market') ? 'true' : 'false'}
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          >
            {MARKET_OPTIONS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="add-bet-pick" label="Sélection" error={fieldError('pick')}>
          <input
            id="add-bet-pick"
            type="text"
            {...form.register('pick')}
            aria-invalid={fieldError('pick') ? 'true' : 'false'}
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          />
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field id="add-bet-odds" label="Cote" error={fieldError('odds')}>
            <input
              id="add-bet-odds"
              type="number"
              step="0.01"
              min={1.01}
              max={1000}
              {...form.register('odds', { valueAsNumber: true })}
              aria-invalid={fieldError('odds') ? 'true' : 'false'}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            />
          </Field>

          <Field id="add-bet-stake" label="Mise (€)" error={fieldError('stake')}>
            <input
              id="add-bet-stake"
              type="number"
              step="0.01"
              min={0.01}
              {...form.register('stake', { valueAsNumber: true })}
              aria-invalid={fieldError('stake') ? 'true' : 'false'}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            />
          </Field>
        </div>
      </form>
    </Modal>
  );
}

interface FieldProps {
  id: string;
  label: string;
  error?: string;
  children: React.ReactNode;
}

function Field({ id, label, error, children }: FieldProps) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700 dark:text-slate-300"
      >
        {label}
      </label>
      {children}
      {error && (
        <p className="mt-1 text-xs text-rose-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export default AddBetModal;
