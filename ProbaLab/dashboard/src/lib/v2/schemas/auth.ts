import { z } from 'zod';

/**
 * Login form schema — email + password only. No captcha field (handled
 * out-of-band). Minimal strength rules here; real strength checks are
 * performed server-side.
 */
export const loginSchema = z.object({
  email: z.string().email('Email invalide'),
  password: z.string().min(8, 'Mot de passe trop court (min 8)'),
});
export type Login = z.infer<typeof loginSchema>;

/**
 * Registration form schema.
 *
 * - `password` + `passwordConfirm` must match.
 * - `pseudo` must mirror the profile pseudo constraints.
 * - `acceptTos` must be `true` explicitly.
 */
export const registerSchema = z
  .object({
    email: z.string().email('Email invalide'),
    password: z.string().min(8, 'Mot de passe trop court (min 8)'),
    passwordConfirm: z.string().min(8, 'Mot de passe trop court (min 8)'),
    pseudo: z
      .string()
      .min(3, 'Pseudo trop court (min 3)')
      .max(24, 'Pseudo trop long (max 24)')
      .regex(/^[A-Za-z0-9_-]+$/, 'Caractères autorisés : A-Z, a-z, 0-9, _ -'),
    acceptTos: z.literal(true, { message: 'Acceptation des CGU requise' }),
  })
  .refine((d) => d.password === d.passwordConfirm, {
    message: 'Les mots de passe ne correspondent pas',
    path: ['passwordConfirm'],
  });
export type Register = z.infer<typeof registerSchema>;
