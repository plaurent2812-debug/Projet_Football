// Lazy-loaded MSW service worker for local dev only.
// Consumed by main.tsx when VITE_MSW_ENABLED === 'true'.

import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
