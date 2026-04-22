import { z } from 'zod';

/**
 * Profile update schema — used by the "Profil" tab in the account page.
 *
 * `pseudo` mirrors the DB constraint (3-24 chars, alpha-num + `_` + `-`).
 * `email` is optional in the update form: when provided it must be valid.
 */
export const profileUpdateSchema = z.object({
  pseudo: z
    .string()
    .min(3, 'Pseudo trop court (min 3)')
    .max(24, 'Pseudo trop long (max 24)')
    .regex(/^[A-Za-z0-9_-]+$/, 'Caractères autorisés : A-Z, a-z, 0-9, _ -'),
  email: z.string().email('Email invalide').optional(),
});
export type ProfileUpdate = z.infer<typeof profileUpdateSchema>;

/**
 * Password change schema.
 *
 * Enforces minimum length + confirmation match + that the new password
 * is actually different from the current one.
 */
export const passwordChangeSchema = z
  .object({
    current: z.string().min(8, 'Min 8 caractères'),
    next: z.string().min(8, 'Min 8 caractères'),
    confirm: z.string().min(8, 'Min 8 caractères'),
  })
  .refine((d) => d.next === d.confirm, {
    message: 'Les mots de passe ne correspondent pas',
    path: ['confirm'],
  })
  .refine((d) => d.next !== d.current, {
    message: 'Le nouveau mot de passe doit être différent',
    path: ['next'],
  });
export type PasswordChange = z.infer<typeof passwordChangeSchema>;
