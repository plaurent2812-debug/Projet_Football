import { describe, it, expect } from 'vitest';
import { loginSchema, registerSchema } from './auth';

describe('loginSchema', () => {
  it('accepts a valid email + password', () => {
    expect(
      loginSchema.safeParse({ email: 'user@example.com', password: 'secret123' }).success,
    ).toBe(true);
  });

  it('rejects malformed email', () => {
    expect(
      loginSchema.safeParse({ email: 'not-email', password: 'secret123' }).success,
    ).toBe(false);
  });

  it('rejects password under 8 chars', () => {
    expect(
      loginSchema.safeParse({ email: 'user@example.com', password: 'short' }).success,
    ).toBe(false);
  });
});

describe('registerSchema', () => {
  const base = {
    email: 'user@example.com',
    password: 'Secret123',
    passwordConfirm: 'Secret123',
    pseudo: 'JohnDoe',
    acceptTos: true,
  } as const;

  it('accepts a valid registration', () => {
    expect(registerSchema.safeParse(base).success).toBe(true);
  });

  it('rejects when passwords do not match', () => {
    const res = registerSchema.safeParse({ ...base, passwordConfirm: 'Different1' });
    expect(res.success).toBe(false);
    if (!res.success) {
      const issue = res.error.issues.find((i) => i.path.join('.') === 'passwordConfirm');
      expect(issue).toBeDefined();
    }
  });

  it('rejects when TOS are not accepted', () => {
    expect(registerSchema.safeParse({ ...base, acceptTos: false }).success).toBe(false);
  });

  it('rejects pseudo shorter than 3 chars', () => {
    expect(registerSchema.safeParse({ ...base, pseudo: 'ab' }).success).toBe(false);
  });

  it('rejects password under 8 chars', () => {
    expect(
      registerSchema.safeParse({ ...base, password: 'short', passwordConfirm: 'short' }).success,
    ).toBe(false);
  });
});
