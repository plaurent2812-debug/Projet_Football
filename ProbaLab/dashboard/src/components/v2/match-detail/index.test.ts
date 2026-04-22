import { describe, it, expect } from 'vitest';
import * as barrel from './index';

describe('match-detail barrel', () => {
  it('re-exports every match-detail component', () => {
    expect(typeof barrel.FormBadge).toBe('function');
    expect(typeof barrel.MatchHero).toBe('function');
    expect(typeof barrel.MatchHeroCompact).toBe('function');
    expect(typeof barrel.StatsComparative).toBe('function');
    expect(typeof barrel.H2HSection).toBe('function');
    expect(typeof barrel.AIAnalysis).toBe('function');
    expect(typeof barrel.CompositionsSection).toBe('function');
    expect(typeof barrel.AllMarketsGrid).toBe('function');
    expect(typeof barrel.RecoCard).toBe('function');
    expect(typeof barrel.BookOddsList).toBe('function');
    expect(typeof barrel.ValueBetsList).toBe('function');
    expect(typeof barrel.StickyActions).toBe('function');
  });
});
