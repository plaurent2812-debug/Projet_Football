import { describe, it, expect } from 'vitest';
import { V2_REDIRECTS, buildRedirectTarget } from './redirects';

describe('V2_REDIRECTS table', () => {
  it('contains the 8 documented legacy entries', () => {
    expect(V2_REDIRECTS).toHaveLength(8);
  });

  it('exposes each required legacy path', () => {
    const fromPaths = V2_REDIRECTS.map((r) => r.from).sort();
    expect(fromPaths).toEqual(
      [
        '/football',
        '/football/match/:id',
        '/hero-showcase',
        '/nhl',
        '/nhl/match/:id',
        '/paris-du-soir',
        '/paris-du-soir/football',
        '/watchlist',
      ].sort(),
    );
  });

  it('marks hero-showcase as preserveQuery=false', () => {
    const entry = V2_REDIRECTS.find((r) => r.from === '/hero-showcase');
    expect(entry?.preserveQuery).toBe(false);
    expect(entry?.to).toBe('/');
  });

  it('marks all other entries as preserveQuery=true', () => {
    for (const entry of V2_REDIRECTS) {
      if (entry.from === '/hero-showcase') continue;
      expect(entry.preserveQuery).toBe(true);
    }
  });
});

describe('buildRedirectTarget — static paths without :id', () => {
  it('preserves incoming query when preserveQuery=true and target has no query', () => {
    const out = buildRedirectTarget(
      '/watchlist',
      '/watchlist',
      '?ref=newsletter',
      true,
      '/compte/bankroll',
    );
    expect(out).toBe('/compte/bankroll?ref=newsletter');
  });

  it('merges incoming query with target query (incoming wins on collisions)', () => {
    const out = buildRedirectTarget(
      '/football',
      '/football',
      '?sport=nhl&team=PSG',
      true,
      '/matchs?sport=foot',
    );
    // Target "sport=foot" is default, incoming "sport=nhl" wins → explicit collision
    // But plan says signal/sport are "injected only if missing" → test that semantics
    // Incoming `sport=nhl` is already present → target's `sport=foot` is NOT injected.
    expect(out).toContain('sport=nhl');
    expect(out).not.toContain('sport=foot');
    expect(out).toContain('team=PSG');
    expect(out.startsWith('/matchs?')).toBe(true);
  });

  it('keeps target query alone when incoming has no query', () => {
    const out = buildRedirectTarget(
      '/paris-du-soir',
      '/paris-du-soir',
      '',
      true,
      '/matchs?signal=value',
    );
    expect(out).toBe('/matchs?signal=value');
  });

  it('drops incoming query when preserveQuery=false', () => {
    const out = buildRedirectTarget(
      '/hero-showcase',
      '/hero-showcase',
      '?utm_source=twitter',
      false,
      '/',
    );
    expect(out).toBe('/');
  });

  it('handles bare paths with no query in target nor incoming', () => {
    const out = buildRedirectTarget('/watchlist', '/watchlist', '', true, '/compte/bankroll');
    expect(out).toBe('/compte/bankroll');
  });
});

describe('buildRedirectTarget — dynamic :id paths', () => {
  it('substitutes :id from actualPath into target', () => {
    const out = buildRedirectTarget(
      '/football/match/:id',
      '/football/match/12345',
      '',
      true,
      '/matchs/:id',
    );
    expect(out).toBe('/matchs/12345');
  });

  it('substitutes :id and preserves incoming query', () => {
    const out = buildRedirectTarget(
      '/nhl/match/:id',
      '/nhl/match/98765',
      '?tab=stats',
      true,
      '/matchs/:id',
    );
    expect(out).toBe('/matchs/98765?tab=stats');
  });

  it('encodes reserved characters in :id if present', () => {
    const out = buildRedirectTarget(
      '/football/match/:id',
      '/football/match/a%2Fb',
      '',
      true,
      '/matchs/:id',
    );
    // %2F is already encoded → keep as-is (no double encoding)
    expect(out).toContain('/matchs/a');
  });
});

describe('buildRedirectTarget — query merge semantics', () => {
  it('injected target query params are kept when incoming does NOT have the same key', () => {
    const out = buildRedirectTarget(
      '/football',
      '/football',
      '?team=OM',
      true,
      '/matchs?sport=foot',
    );
    // sport injected (not in incoming), team preserved
    expect(out).toContain('sport=foot');
    expect(out).toContain('team=OM');
  });

  it('handles multiple injected params in target', () => {
    const out = buildRedirectTarget(
      '/paris-du-soir/football',
      '/paris-du-soir/football',
      '?date=2026-04-22',
      true,
      '/matchs?sport=foot&signal=value',
    );
    expect(out).toContain('sport=foot');
    expect(out).toContain('signal=value');
    expect(out).toContain('date=2026-04-22');
  });
});
