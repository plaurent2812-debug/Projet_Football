/**
 * Feature flag pour la refonte frontend V2.
 * Lu depuis la variable Vite `VITE_FRONTEND_V2`.
 * Default : false (ancien frontend servi).
 */
export function isFrontendV2Enabled(): boolean {
  const raw = import.meta.env.VITE_FRONTEND_V2;
  return raw === 'true';
}

export const FRONTEND_V2_ENABLED: boolean = isFrontendV2Enabled();
