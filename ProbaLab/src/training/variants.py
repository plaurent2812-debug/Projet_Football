"""Variants ML — 4 configs entraînées en parallèle sur holdout commun.

Design:
    - baseline: FEATURE_COLS actuel, poids (0.55/0.25/0.20)
    - rebalanced: FEATURE_COLS actuel, poids (0.40/0.20/0.40) — applique leçon 53
    - pure: FEATURE_COLS SANS les 6 market_*, poids (0.55/0.25/0.20) — test "edge pur"
    - pure_rebalanced: FEATURE_COLS SANS market, poids (0.65/0.35/0.0) NO_MARKET

Critère de sélection : meilleur Brier sur holdout **ET** CLV ≥ baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.constants import FEATURE_COLS

MARKET_FEATURE_NAMES: tuple[str, ...] = (
    "market_home_prob",
    "market_draw_prob",
    "market_away_prob",
    "market_btts_prob",
    "market_over25_prob",
    "market_over15_prob",
)


def _without_market(cols: list[str]) -> list[str]:
    return [c for c in cols if c not in MARKET_FEATURE_NAMES]


@dataclass(frozen=True)
class VariantConfig:
    name: str
    feature_cols: list[str] = field(default_factory=list)
    weight_poisson: float = 0.55
    weight_elo: float = 0.25
    weight_market: float = 0.20
    description: str = ""


_BASELINE = VariantConfig(
    name="baseline",
    feature_cols=list(FEATURE_COLS),
    weight_poisson=0.55,
    weight_elo=0.25,
    weight_market=0.20,
    description="Actuel en prod — 43 features incl. market_*",
)

_REBALANCED = VariantConfig(
    name="rebalanced",
    feature_cols=list(FEATURE_COLS),
    weight_poisson=0.40,
    weight_elo=0.20,
    weight_market=0.40,
    description="FEATURE_COLS baseline, poids shiftés vers marché (leçon 53)",
)

_PURE = VariantConfig(
    name="pure",
    feature_cols=_without_market(list(FEATURE_COLS)),
    weight_poisson=0.55,
    weight_elo=0.25,
    weight_market=0.20,
    description="Sans les 6 market_* — test d'edge pur indépendant",
)

_PURE_REBALANCED = VariantConfig(
    name="pure_rebalanced",
    feature_cols=_without_market(list(FEATURE_COLS)),
    weight_poisson=0.65,
    weight_elo=0.35,
    weight_market=0.0,
    description="Sans market features ET sans market dans blend (Dixon-Coles + ELO purs)",
)

ALL_VARIANTS: list[VariantConfig] = [
    _BASELINE,
    _REBALANCED,
    _PURE,
    _PURE_REBALANCED,
]

_BY_NAME: dict[str, VariantConfig] = {v.name: v for v in ALL_VARIANTS}


def get_variant(name: str) -> VariantConfig:
    cfg = _BY_NAME.get(name)
    if cfg is None:
        raise ValueError(f"Unknown variant: {name}. Known: {list(_BY_NAME)}")
    return cfg
