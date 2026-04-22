// Performance summary for the dashboard stat strip (V2).

export interface PerformanceSummary {
  roi30d: { value: number; deltaVs7d: number }; // percent
  accuracy: { value: number; deltaVs7d: number }; // percent
  brier7d: { value: number; deltaVs7d: number }; // brier score
  bankroll: { value: number; currency: 'EUR' }; // amount
}
