import { describe, it, expectTypeOf } from 'vitest';
import type { FixtureId, UserRole, Sport, SubscriptionStatus, League } from './common';

describe('types/v2/common', () => {
  it('FixtureId is a string brand', () => {
    expectTypeOf<FixtureId>().toMatchTypeOf<string>();
  });

  it('UserRole has the 4 known roles', () => {
    expectTypeOf<UserRole>().toEqualTypeOf<'visitor' | 'free' | 'trial' | 'premium' | 'admin'>();
  });

  it('Sport is football or nhl', () => {
    expectTypeOf<Sport>().toEqualTypeOf<'football' | 'nhl'>();
  });

  it('SubscriptionStatus is one of the Stripe statuses', () => {
    expectTypeOf<SubscriptionStatus>().toEqualTypeOf<
      'active' | 'trialing' | 'past_due' | 'canceled' | 'incomplete' | 'none'
    >();
  });

  it('League is a string literal union of supported leagues', () => {
    expectTypeOf<League>().toMatchTypeOf<string>();
  });
});
