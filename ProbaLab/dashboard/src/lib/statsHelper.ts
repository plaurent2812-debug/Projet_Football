/**
 * Centralized stat value accessor — resolves stats_json vs top-level ambiguity.
 * Priority: stats_json field -> top-level field -> fallback.
 */
export function getStatValue(prediction: any, key: string, fallback: number | null = null): number | null {
  const sj = prediction?.stats_json || {}
  // Normalize key variations (proba_over_25 vs proba_over_2_5)
  const normalizedKeys = [key, key.replace(/_(\d)_(\d)/, '_$1$2'), key.replace(/_(\d)(\d)/, '_$1_$2')]

  for (const k of normalizedKeys) {
    if (sj[k] != null && typeof sj[k] === 'number') return sj[k]
    if (prediction?.[k] != null && typeof prediction[k] === 'number') return prediction[k]
  }
  return fallback
}

export function formatProba(val: number | null | undefined): string {
  return typeof val === 'number' ? `${Math.round(val)}%` : '—'
}

export function formatOdds(val: number | null | undefined): string {
  return typeof val === 'number' ? val.toFixed(2) : '—'
}

export function formatEV(val: number | null | undefined): string {
  if (typeof val !== 'number') return '—'
  return `${val >= 0 ? '+' : ''}${(val * 100).toFixed(1)}%`
}
