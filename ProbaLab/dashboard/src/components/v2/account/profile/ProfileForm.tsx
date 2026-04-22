import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AlertTriangle, CheckCircle2, Eye, EyeOff } from 'lucide-react';
import {
  profileUpdateSchema,
  passwordChangeSchema,
  type ProfileUpdate,
  type PasswordChange,
} from '@/lib/v2/schemas/profile';
import {
  useProfile,
  useUpdateProfile,
  useChangePassword,
  useDeleteAccount,
} from '@/hooks/v2/useProfile';

export interface ProfileFormProps {
  'data-testid'?: string;
}

/**
 * "Profil" tab form — pseudo update + password change + RGPD deletion.
 *
 * Three forms stacked in a single component so the page stays flat :
 *   1. `<FormInfo />`      — email (readonly) + pseudo, validated by
 *                             profileUpdateSchema.
 *   2. `<FormPassword />`  — current / next / confirm, validated by
 *                             passwordChangeSchema (cross-field refine).
 *   3. `<DangerZone />`    — two-step deletion with a literal "SUPPRIMER"
 *                             typed confirmation (RGPD).
 */
export function ProfileForm({
  'data-testid': dataTestId = 'profile-form',
}: ProfileFormProps = {}) {
  const { data, isLoading } = useProfile();
  const update = useUpdateProfile();
  const changePw = useChangePassword();
  const del = useDeleteAccount();

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState('');

  const infoForm = useForm<ProfileUpdate>({
    resolver: zodResolver(profileUpdateSchema),
    values: { pseudo: data?.pseudo ?? '' },
  });

  const pwForm = useForm<PasswordChange>({
    resolver: zodResolver(passwordChangeSchema),
    defaultValues: { current: '', next: '', confirm: '' },
  });

  if (isLoading || !data) {
    return (
      <div
        data-testid="profile-form-skeleton"
        aria-busy="true"
        aria-label="Chargement du profil"
        className="space-y-4"
      >
        <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />
        <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-900" />
      </div>
    );
  }

  const onInfoSubmit = infoForm.handleSubmit(async (values) => {
    await update.mutateAsync({ pseudo: values.pseudo });
  });

  const onPasswordSubmit = pwForm.handleSubmit(async (values) => {
    await changePw.mutateAsync({ current: values.current, next: values.next });
    pwForm.reset({ current: '', next: '', confirm: '' });
  });

  const cardClass =
    'rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900';

  return (
    <div
      data-testid={dataTestId}
      aria-label="Formulaire de profil"
      className="space-y-6"
    >
      {/* Section 1 — Informations */}
      <section className={cardClass}>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          Informations
        </h2>
        <form onSubmit={onInfoSubmit} className="mt-4 space-y-4" noValidate>
          <div>
            <label
              htmlFor="profile-email"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Email
            </label>
            <div className="mt-1 flex items-center gap-2">
              <input
                id="profile-email"
                type="email"
                value={data.email}
                readOnly
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200"
              />
              <span
                className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
                role="status"
              >
                <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                Vérifié
              </span>
            </div>
          </div>

          <div>
            <label
              htmlFor="profile-pseudo"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Pseudo
            </label>
            <input
              id="profile-pseudo"
              type="text"
              {...infoForm.register('pseudo')}
              aria-invalid={infoForm.formState.errors.pseudo ? 'true' : 'false'}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
            />
            {infoForm.formState.errors.pseudo && (
              <p className="mt-1 text-xs text-rose-600" role="alert">
                {infoForm.formState.errors.pseudo.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={update.isPending}
            className="inline-flex items-center rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {update.isPending ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </form>
      </section>

      {/* Section 2 — Mot de passe */}
      <section className={cardClass}>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          Changer le mot de passe
        </h2>
        <form onSubmit={onPasswordSubmit} className="mt-4 space-y-4" noValidate>
          <PasswordField
            id="pw-current"
            label="Mot de passe actuel"
            visible={showCurrent}
            onToggle={() => setShowCurrent((v) => !v)}
            error={pwForm.formState.errors.current?.message}
            register={pwForm.register('current')}
          />
          <PasswordField
            id="pw-next"
            label="Nouveau mot de passe"
            visible={showNext}
            onToggle={() => setShowNext((v) => !v)}
            error={pwForm.formState.errors.next?.message}
            register={pwForm.register('next')}
          />
          <PasswordField
            id="pw-confirm"
            label="Confirmer le nouveau mot de passe"
            visible={showConfirm}
            onToggle={() => setShowConfirm((v) => !v)}
            error={pwForm.formState.errors.confirm?.message}
            register={pwForm.register('confirm')}
          />
          <button
            type="submit"
            disabled={changePw.isPending}
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {changePw.isPending
              ? 'Mise à jour…'
              : 'Mettre à jour le mot de passe'}
          </button>
        </form>
      </section>

      {/* Section 3 — Zone dangereuse (RGPD) */}
      <section
        className={`${cardClass} border-rose-200 dark:border-rose-900`}
        aria-label="Zone dangereuse"
      >
        <div className="flex items-start gap-3">
          <AlertTriangle
            className="mt-0.5 h-5 w-5 text-rose-500"
            aria-hidden="true"
          />
          <div>
            <h2 className="text-lg font-semibold text-rose-600">
              Supprimer mon compte
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Suppression définitive (RGPD) : l'ensemble de tes données
              personnelles, paris et préférences seront effacés.
            </p>
          </div>
        </div>
        {!confirmOpen ? (
          <button
            type="button"
            onClick={() => setConfirmOpen(true)}
            className="mt-4 inline-flex items-center rounded-lg bg-rose-500 px-4 py-2 text-sm font-medium text-white hover:bg-rose-600"
          >
            Supprimer mon compte
          </button>
        ) : (
          <div className="mt-4 space-y-3">
            <label
              htmlFor="confirm-delete"
              className="block text-sm font-medium text-slate-700 dark:text-slate-300"
            >
              Tapez SUPPRIMER pour confirmer
            </label>
            <input
              id="confirm-delete"
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
              autoComplete="off"
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={confirmText !== 'SUPPRIMER' || del.isPending}
                onClick={() => del.mutateAsync()}
                className="inline-flex items-center rounded-lg bg-rose-500 px-4 py-2 text-sm font-medium text-white hover:bg-rose-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {del.isPending ? 'Suppression…' : 'Confirmer la suppression'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setConfirmOpen(false);
                  setConfirmText('');
                }}
                className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Annuler
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

interface PasswordFieldProps {
  id: string;
  label: string;
  visible: boolean;
  onToggle: () => void;
  error?: string;
  register: ReturnType<ReturnType<typeof useForm<PasswordChange>>['register']>;
}

function PasswordField({
  id,
  label,
  visible,
  onToggle,
  error,
  register,
}: PasswordFieldProps) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-slate-700 dark:text-slate-300"
      >
        {label}
      </label>
      <div className="relative mt-1">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          {...register}
          aria-invalid={error ? 'true' : 'false'}
          className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 pr-10 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-white"
        />
        <button
          type="button"
          onClick={onToggle}
          aria-label={
            visible
              ? `Masquer le ${label.toLowerCase()}`
              : `Afficher le ${label.toLowerCase()}`
          }
          className="absolute inset-y-0 right-2 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
        >
          {visible ? (
            <EyeOff className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Eye className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>
      {error && (
        <p className="mt-1 text-xs text-rose-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export default ProfileForm;
