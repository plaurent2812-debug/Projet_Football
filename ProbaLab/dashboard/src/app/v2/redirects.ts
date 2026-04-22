/**
 * Legacy → V2 redirect table (single source of truth shared with FastAPI).
 *
 * When a user hits a deprecated legacy URL we redirect them to the V2
 * equivalent via react-router `<Navigate replace>`. Query params of the
 * incoming request are preserved when `preserveQuery` is true; target-side
 * query params are injected only when the same key is NOT already present.
 *
 * Dynamic segments : `:id` in `from` is pulled from `actualPath` and
 * substituted into `to`.
 *
 * Lot 6 — Bloc A — migration V2.
 */

export interface RedirectEntry {
  /** React Router path pattern of the legacy route (may contain `:id`). */
  from: string;
  /** Target V2 path (may contain `:id` and/or a `?query`). */
  to: string;
  /** Whether to carry over the incoming query string. */
  preserveQuery: boolean;
}

export const V2_REDIRECTS: readonly RedirectEntry[] = [
  { from: '/paris-du-soir', to: '/matchs?signal=value', preserveQuery: true },
  {
    from: '/paris-du-soir/football',
    to: '/matchs?sport=foot&signal=value',
    preserveQuery: true,
  },
  { from: '/football', to: '/matchs?sport=foot', preserveQuery: true },
  { from: '/football/match/:id', to: '/matchs/:id', preserveQuery: true },
  { from: '/nhl', to: '/matchs?sport=nhl', preserveQuery: true },
  { from: '/nhl/match/:id', to: '/matchs/:id', preserveQuery: true },
  { from: '/watchlist', to: '/compte/bankroll', preserveQuery: true },
  { from: '/hero-showcase', to: '/', preserveQuery: false },
] as const;

/** Split a path template into (pathPart, queryPart). */
function splitPathAndQuery(target: string): { path: string; query: string } {
  const qIdx = target.indexOf('?');
  if (qIdx === -1) return { path: target, query: '' };
  return { path: target.slice(0, qIdx), query: target.slice(qIdx + 1) };
}

/** Pull the `:id` value from the actual path, using the template. */
function extractIdFromActualPath(fromTemplate: string, actualPath: string): string | null {
  if (!fromTemplate.includes(':id')) return null;

  // Convert template to regex (e.g. "/football/match/:id" -> "^/football/match/([^/]+)$")
  const pattern = fromTemplate.replace(/:id/g, '([^/?#]+)');
  const re = new RegExp('^' + pattern + '$');
  const match = actualPath.match(re);
  if (!match || match.length < 2) return null;
  return match[1] ?? null;
}

/**
 * Build a redirect target from a legacy URL.
 *
 * @param fromTemplate  Path pattern of the legacy route (may contain `:id`).
 * @param actualPath    The real pathname being visited.
 * @param incomingSearch  The `location.search` of the incoming request (e.g. `?team=PSG`).
 * @param preserveQuery Whether to merge the incoming query into the output.
 * @param toTemplate    Target template (may contain `:id` and/or `?query`).
 */
export function buildRedirectTarget(
  fromTemplate: string,
  actualPath: string,
  incomingSearch: string,
  preserveQuery: boolean,
  toTemplate: string,
): string {
  // 1. Substitute :id
  let resolved = toTemplate;
  const idValue = extractIdFromActualPath(fromTemplate, actualPath);
  if (idValue !== null) {
    // If already percent-encoded (e.g. a%2Fb) keep as-is, otherwise encode.
    const looksEncoded = /%[0-9A-Fa-f]{2}/.test(idValue);
    const safeId = looksEncoded ? idValue : encodeURIComponent(idValue);
    resolved = resolved.replace(/:id/g, safeId);
  }

  // 2. Split target into (path, query)
  const { path: targetPath, query: targetQuery } = splitPathAndQuery(resolved);

  // 3. Merge query params if preserveQuery
  if (!preserveQuery) {
    // Drop incoming completely; keep target's own query
    return targetQuery ? `${targetPath}?${targetQuery}` : targetPath;
  }

  const incomingClean = incomingSearch.startsWith('?')
    ? incomingSearch.slice(1)
    : incomingSearch;

  const incomingParams = new URLSearchParams(incomingClean);
  const merged = new URLSearchParams(incomingParams);

  // Target params injected ONLY if incoming does not already have the key
  const targetParams = new URLSearchParams(targetQuery);
  for (const [k, v] of targetParams.entries()) {
    if (!merged.has(k)) merged.set(k, v);
  }

  const finalQs = merged.toString();
  return finalQs ? `${targetPath}?${finalQs}` : targetPath;
}
