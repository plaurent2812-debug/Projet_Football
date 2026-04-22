import { describe, it, expect, beforeAll } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('tokens.css', () => {
  let css = '';

  beforeAll(() => {
    css = fs.readFileSync(
      path.resolve(__dirname, './tokens.css'),
      'utf-8'
    );
  });

  it('defines :root dark palette', () => {
    expect(css).toMatch(/:root\s*{[^}]*--bg:\s*#0a0e1a/);
    expect(css).toMatch(/--surface:\s*#111827/);
    expect(css).toMatch(/--primary:\s*#10b981/);
    expect(css).toMatch(/--value:\s*#fbbf24/);
    expect(css).toMatch(/--danger:\s*#ef4444/);
  });

  it('defines [data-theme="light"] palette', () => {
    expect(css).toMatch(/\[data-theme="light"\]\s*{[^}]*--bg:\s*#fafaf8/);
    expect(css).toMatch(/--primary:\s*#059669/);
  });

  it('defines spacing scale on 4px grid', () => {
    expect(css).toMatch(/--space-1:\s*4px/);
    expect(css).toMatch(/--space-2:\s*8px/);
    expect(css).toMatch(/--space-4:\s*16px/);
  });

  it('defines focus ring using primary', () => {
    expect(css).toMatch(/--focus-ring:\s*2px solid var\(--primary\)/);
  });
});
