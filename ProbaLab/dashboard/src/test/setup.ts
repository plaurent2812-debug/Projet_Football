import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll, expect, vi } from 'vitest';
import { toHaveNoViolations } from 'jest-axe';
import { server } from './mocks/server';
import { resetNotificationRulesHandlerState } from './mocks/handlers';

expect.extend(toHaveNoViolations);

// jsdom does not implement IntersectionObserver; framer-motion's
// `useInView` depends on it for scroll-reveal animations. We provide a
// no-op polyfill that always reports elements as visible so
// reveal-triggered UI renders synchronously in tests.
if (typeof window !== 'undefined' && !('IntersectionObserver' in window)) {
  class MockIntersectionObserver {
    readonly root = null;
    readonly rootMargin = '';
    readonly thresholds: ReadonlyArray<number> = [];
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
    takeRecords = vi.fn(() => []);
    constructor(cb: IntersectionObserverCallback) {
      // Fire the callback once with all targets as "intersecting" so
      // framer-motion's `useInView` returns true immediately.
      queueMicrotask(() => {
        try {
          cb(
            [
              {
                isIntersecting: true,
                intersectionRatio: 1,
                target: document.body,
                boundingClientRect: {} as DOMRectReadOnly,
                intersectionRect: {} as DOMRectReadOnly,
                rootBounds: null,
                time: 0,
              } as IntersectionObserverEntry,
            ],
            this as unknown as IntersectionObserver,
          );
        } catch {
          /* ignore */
        }
      });
    }
  }
  (window as unknown as { IntersectionObserver: typeof IntersectionObserver })
    .IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver;
  (globalThis as unknown as { IntersectionObserver: typeof IntersectionObserver })
    .IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver;
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  resetNotificationRulesHandlerState();
});
afterAll(() => server.close());
