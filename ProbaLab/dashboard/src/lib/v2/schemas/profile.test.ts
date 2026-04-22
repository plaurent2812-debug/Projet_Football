import { describe, it, expect } from 'vitest';
import { profileUpdateSchema, passwordChangeSchema } from './profile';

describe('profileUpdateSchema', () => {
  it('accepts a valid pseudo (alpha-numeric with underscore and hyphen)', () => {
    const res = profileUpdateSchema.safeParse({ pseudo: 'John_Doe-42' });
    expect(res.success).toBe(true);
  });

  it('accepts a valid email along with a pseudo', () => {
    const res = profileUpdateSchema.safeParse({
      pseudo: 'JohnDoe',
      email: 'john@example.com',
    });
    expect(res.success).toBe(true);
  });

  it('rejects pseudo under 3 chars', () => {
    expect(profileUpdateSchema.safeParse({ pseudo: 'ab' }).success).toBe(false);
  });

  it('rejects pseudo over 24 chars', () => {
    expect(profileUpdateSchema.safeParse({ pseudo: 'x'.repeat(25) }).success).toBe(false);
  });

  it('rejects pseudo with spaces', () => {
    expect(profileUpdateSchema.safeParse({ pseudo: 'john doe' }).success).toBe(false);
  });

  it('rejects pseudo with special characters', () => {
    expect(profileUpdateSchema.safeParse({ pseudo: 'john@doe' }).success).toBe(false);
  });

  it('rejects malformed email', () => {
    const res = profileUpdateSchema.safeParse({ pseudo: 'JohnDoe', email: 'not-an-email' });
    expect(res.success).toBe(false);
  });
});

describe('passwordChangeSchema', () => {
  it('accepts matching current/next/confirm (min 8)', () => {
    const res = passwordChangeSchema.safeParse({
      current: 'oldpass123',
      next: 'newpass123',
      confirm: 'newpass123',
    });
    expect(res.success).toBe(true);
  });

  it('rejects when next does not match confirm', () => {
    const res = passwordChangeSchema.safeParse({
      current: 'oldpass123',
      next: 'newpass123',
      confirm: 'different1',
    });
    expect(res.success).toBe(false);
    if (!res.success) {
      const issue = res.error.issues.find((i) => i.path.join('.') === 'confirm');
      expect(issue).toBeDefined();
    }
  });

  it('rejects when new password is under 8 chars', () => {
    const res = passwordChangeSchema.safeParse({
      current: 'oldpass123',
      next: 'short',
      confirm: 'short',
    });
    expect(res.success).toBe(false);
  });

  it('rejects when next equals current (no change)', () => {
    const res = passwordChangeSchema.safeParse({
      current: 'samepass1',
      next: 'samepass1',
      confirm: 'samepass1',
    });
    expect(res.success).toBe(false);
  });
});
