"""Custom Prometheus metrics for ProbaLab business logic."""

from prometheus_client import Counter, Histogram

# ─── Prediction pipeline ─────────────────────────────────────────────────────

predictions_generated: Counter = Counter(
    "probalab_predictions_generated_total",
    "Total predictions generated",
    ["sport", "league"],
)

pipeline_runs: Counter = Counter(
    "probalab_pipeline_runs_total",
    "Total pipeline runs",
    ["mode", "status"],
)

pipeline_duration: Histogram = Histogram(
    "probalab_pipeline_duration_seconds",
    "Pipeline execution time in seconds",
    ["mode"],
)

# ─── AI / Gemini ─────────────────────────────────────────────────────────────

gemini_calls: Counter = Counter(
    "probalab_gemini_calls_total",
    "Total Gemini API calls",
    ["status"],
)

gemini_latency: Histogram = Histogram(
    "probalab_gemini_latency_seconds",
    "Gemini API call latency in seconds",
)

# ─── Best bets resolution ─────────────────────────────────────────────────────

bets_resolved: Counter = Counter(
    "probalab_bets_resolved_total",
    "Total bets resolved after match completion",
    ["result"],  # win, loss, void
)
