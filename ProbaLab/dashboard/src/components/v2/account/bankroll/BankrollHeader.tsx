import { useState } from 'react';
import { Plus, Settings } from 'lucide-react';
import { AddBetModal } from './AddBetModal';
import { BankrollSettingsModal } from './BankrollSettingsModal';

export interface BankrollHeaderProps {
  'data-testid'?: string;
}

/**
 * Bankroll tab header — page heading + the two action buttons
 * ("Paramètres" and "+ Ajouter un pari"). Owns the local state for
 * both modals, keeping the parent page thin.
 */
export function BankrollHeader({
  'data-testid': dataTestId = 'bankroll-header',
}: BankrollHeaderProps = {}) {
  const [addOpen, setAddOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <header
      data-testid={dataTestId}
      className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
        Suivi de mes paris
      </h1>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
          Paramètres
        </button>
        <button
          type="button"
          onClick={() => setAddOpen(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Ajouter un pari
        </button>
      </div>

      <AddBetModal open={addOpen} onOpenChange={setAddOpen} />
      <BankrollSettingsModal
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
      />
    </header>
  );
}

export default BankrollHeader;
