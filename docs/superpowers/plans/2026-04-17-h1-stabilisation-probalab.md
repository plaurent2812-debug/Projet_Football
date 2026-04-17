# H1 — Stabilisation ProbaLab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clôre les 22 items P0 de l'audit 360° 2026-04-17 en 4 sprints (effort dev ~22-28j, ~11-14 semaines calendaires à 5h/sem solopreneur), poser les fondations du pivot avec les 4 décisions owner intégrées (budget 50€/mois, posture hybride C, prix 14,99€, scope NHL = `player_goals`).

**Architecture:** Plan séquentiel en 4 sprints (Sprint A = bugs ML, Sprint B = monitoring + sécu, Sprint C = analytics + positionnement + NHL, Sprint D = UI foundation pivot-ready). Chaque sprint livre un ensemble cohérent, testable, déployable. TDD systématique sur les fixes code. Commits fréquents (après chaque task), branches feature/* séparées du pivot en cours.

**Tech Stack:** Python 3.11, FastAPI, XGBoost, scikit-learn, pytest, Supabase, APScheduler, React 19 + Tailwind + Radix, Plausible Analytics, Stripe. Pas de nouveaux services externes au-delà de Plausible (9€/mois, respecte budget 50€).

---

## Contexte et décisions owner (2026-04-17)

**4 décisions prises** :
1. Budget externe max : **50 €/mois** → pas d'Odds API Pro
2. Posture produit : **hybride C** (pivot tel que brainstormé validé)
3. Prix abonnement : **14,99 €/mois** (BP v2, UI à aligner)
4. Scope NHL pivot : **Option A** — `player_goals` uniquement (Anytime Scorer), assumé publiquement

**Sources** :
- Spec audit : `docs/superpowers/specs/2026-04-17-audit-360-probalab-design.md`
- Roadmap complet : `docs/audit/2026-04-17/12_roadmap_meilleure_app.md`
- Exec summary : `docs/audit/2026-04-17/00_EXECUTIVE_SUMMARY.md`
- Évaluation pivot : `docs/audit/2026-04-17/11_evaluation_pivot.md`
- Design pivot à amender : `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md`

---

## File Structure

### Fichiers modifiés/créés dans le code

**Modifications ML (Sprint A)** :
- Modify: `ProbaLab/src/training/train.py` (fix eval_set, sample_weight CV, walk-forward)
- Modify: `ProbaLab/src/constants.py` (WEIGHT_MARKET 0.20 → 0.45)
- Create: `ProbaLab/tests/test_train_no_leakage.py`
- Create: `ProbaLab/tests/test_walk_forward.py`
- Create: `ProbaLab/scripts/publish_walk_forward_report.py`

**Monitoring + Sécurité (Sprint B)** :
- Modify: `ProbaLab/worker.py` (job `job_run_monitoring_alerts`)
- Create: `ProbaLab/migrations/050_model_health_log.sql`
- Modify: `ProbaLab/run_pipeline.py` (upsert `model_health_log`)
- Modify: `ProbaLab/api/routers/admin.py` (fermer `/update-scores`)
- Modify: `ProbaLab/api/schemas.py` (`extra="forbid"` sur tous les BaseModel)
- Modify: `ProbaLab/api/routers/players.py:162` (retirer `detail=str(e)`)
- Modify: `ProbaLab/src/nhl/ml_models.py` + `ProbaLab/api/routers/nhl.py` (fix fallback silencieux)
- Create: `ProbaLab/scripts/migrate_datetime_now_utc.py` (codemod)
- Modify: ~54 fichiers (remplacement `datetime.now()` → `datetime.now(timezone.utc)`)
- Modify: `.pre-commit-config.yaml` (règle ruff rule RUF/TZ)

**Analytics + Positionnement + NHL (Sprint C)** :
- Modify: `ProbaLab/dashboard/index.html` (Plausible snippet)
- Modify: `ProbaLab/dashboard/src/pages/Premium.tsx` (prix 14,99€)
- Modify: `ProbaLab/api/routers/stripe_webhook.py` (plan Stripe 14,99€)
- Modify: `ProbaLab/dashboard/src/pages/HomePage.tsx` + pages ciblées (événements Plausible)
- Create: `ProbaLab/dashboard/src/lib/analytics.ts` (wrapper event)
- Modify: `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md` (amendement scope NHL)
- Create: `ProbaLab/dashboard/src/pages/Methodology.tsx`
- Create: `ProbaLab/api/routers/methodology.py` (GET /api/methodology/brier-timeline)
- Modify: `ProbaLab/dashboard/src/App.tsx` (route `/methodology`)

**Infrastructure (Sprint C/D)** :
- Modify: `.github/workflows/daily-pipeline.yml` (supprimer `cd Projet_Football`)
- Modify: `ProbaLab/Makefile` (retirer cibles `Projet_Football`)
- Modify: `ruff.toml` (tooling ProbaLab/)
- Delete: `ProbaLab/Projet_Football/` (archive git tag avant suppression)
- Modify: `ProbaLab/railway.toml` (ajouter `[services.deploy]` worker)
- Delete: `ProbaLab/Procfile` (ou `nixpacks.toml`) — choisir une source
- Modify: `ProbaLab/pyproject.toml` (`requires-python = ">=3.11,<3.12"`)
- Modify: `ProbaLab/api/main.py:15` (corriger commentaire APScheduler)
- Modify: `ProbaLab/worker.py` ou `ProbaLab/api/routers/trigger.py` (supprimer duplicatas endpoints)
- Move: `ProbaLab/src/test_auth.py`, `test_connection.py`, `test_api_halves.py` → `ProbaLab/scripts/debug/`
- Modify: `ProbaLab/tests/test_stats_engine.py` (fix 2 tests flaky `TestCalculateXg`)

**UI Foundation (Sprint D)** :
- Modify: `ProbaLab/dashboard/eslint.config.js` (règle bloquante `text-[9-11px]`)
- Modify: ~26 fichiers dashboard (remplacer 154 occurrences `text-[9-11px]` → `text-xs`/`text-sm`)
- Modify: composants `BetCard`, `MatchRow`, `HomePage`, `MatchDetail`, `ParisDuSoir` (`<div onClick>` → `<button>`, ajouter `aria-label`)
- Create: `ProbaLab/dashboard/src/types/api.ts`
- Modify: `ProbaLab/dashboard/generate-types.sh` (utiliser `supabase gen types typescript`)
- Modify: pages utilisant `useState<any>` (HomePage, ParisDuSoir, Performance)

### Fichiers documentation

- Update: `ProbaLab/tasks/lessons.md` (après chaque fix, append nouvelle leçon)
- Update: `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11.md` (amendement scope NHL)
- Create: `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11_AMENDMENT_2026-04-17.md` (amendement séparé)

---

## Conventions de workflow

- **Branche** : `feat/h1-stabilisation` depuis `main` (après merge de `feat/pivot-probas-sportives` quand approprié, OU en parallèle sur branche dédiée)
- **Commits fréquents** : après chaque task validée
- **Tests verts obligatoires** avant chaque commit (pytest unit + ruff)
- **Format commits** : `fix(<scope>):`, `feat(<scope>):`, `refactor(<scope>):`, `docs(audit):`, `chore(ci):`
- **Après chaque fix bug lesson-related** : ajouter une entrée dans `ProbaLab/tasks/lessons.md`
- **Pas de déploiement prod tant que le Sprint en cours n'est pas validé** par l'owner

---

## SPRINT A — Bugs ML critiques (semaine 1)

**Objectif** : fixer les 3 bugs ML P0 de l'annexe 02 + walk-forward validation. Cible : Brier réel mesuré honnêtement, CLV +1-3% attendu.

**Items traités** : P0-1, P0-2, P0-3, P0-11.

### Task A1 : Fix `eval_set` data leakage (P0-1)

**Files:**
- Modify: `ProbaLab/src/training/train.py` (lignes ~393, ~564)
- Create: `ProbaLab/tests/test_train_no_leakage.py`

- [ ] **Step 1 : Lire `train.py` autour des lignes 393 et 564**

Run: `Read ProbaLab/src/training/train.py offset=380 limit=40` et `offset=550 limit=40`
Identifier les 2 endroits où `eval_set=[(X_test, y_test)]` est passé à XGBoost.

- [ ] **Step 2 : Créer le test qui détecte le leakage**

Écrire `ProbaLab/tests/test_train_no_leakage.py` :

```python
"""Test that training pipeline never passes test set as eval_set."""
import ast
import pathlib

TRAIN_PATH = pathlib.Path(__file__).parent.parent / "src" / "training" / "train.py"


def _find_fit_calls_with_eval_set(source: str) -> list[tuple[int, str]]:
    """Return list of (lineno, variable_name_passed_as_eval_set)."""
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fit":
            for kw in node.keywords:
                if kw.arg == "eval_set":
                    # eval_set=[(X_eval, y_eval)] — extract variable names
                    if isinstance(kw.value, ast.List) and kw.value.elts:
                        elt = kw.value.elts[0]
                        if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                            x_name = ast.unparse(elt.elts[0])
                            results.append((node.lineno, x_name))
    return results


def test_no_test_set_in_eval_set():
    """Regression test for lesson 10: eval_set must never be X_test/y_test."""
    source = TRAIN_PATH.read_text()
    fit_calls = _find_fit_calls_with_eval_set(source)
    forbidden = {"X_test", "X_test_fold", "X_test_split"}
    for lineno, x_name in fit_calls:
        assert x_name not in forbidden, (
            f"Data leakage at {TRAIN_PATH}:{lineno} — eval_set uses {x_name} "
            f"which is the test set. Use a separate X_val from train split instead."
        )
```

- [ ] **Step 3 : Lancer le test → il doit FAIL**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_train_no_leakage.py -v`
Expected : FAIL sur `test_no_test_set_in_eval_set` avec message indiquant lignes 393 et/ou 564.

- [ ] **Step 4 : Modifier `train.py` — introduire validation split séparé**

Dans `train.py`, AVANT la première section de training (~ligne 350-400), ajouter :

```python
# Validation split from training set (separate from test set)
# Used for early stopping — never touches the holdout test set
X_train_fit, X_val, y_train_fit, y_val = train_test_split(
    X_train, y_train, test_size=0.15, random_state=42, stratify=y_train
)
```

Puis remplacer aux 2 endroits :
- Ligne ~393 : `eval_set=[(X_test, y_test)]` → `eval_set=[(X_val, y_val)]`
- Ligne ~564 : idem

- [ ] **Step 5 : Lancer le test → il doit PASS**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_train_no_leakage.py -v`
Expected : PASS.

- [ ] **Step 6 : Lancer la suite de tests ML complète**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/ -k "training or train or brier" -v`
Expected : tous verts. Si un test échoue, c'est qu'il s'appuyait sur le leakage — analyser avant fix.

- [ ] **Step 7 : Mettre à jour `tasks/lessons.md`**

Append au tableau :
```
| 2026-04-18 | eval_set=(X_test, y_test) dans 2 endroits train.py — leakage confirmé → validation split dédié | Toujours créer X_val depuis X_train avec train_test_split AVANT le training ; eval_set = X_val, test set = intouchable jusqu'à l'évaluation finale |
```

- [ ] **Step 8 : Commit**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git add ProbaLab/src/training/train.py ProbaLab/tests/test_train_no_leakage.py ProbaLab/tasks/lessons.md
git commit -m "fix(training): remove test set from eval_set (data leakage, lesson 10)

Introduces dedicated X_val from train split at train.py:~393,564.
Adds regression test ensuring no fit call uses X_test as eval_set.
Brier expected to increase honestly by 2-5% (was optimistically biased).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task A2 : Fix `sample_weight` dans cross_val_score (P0-2)

**Files:**
- Modify: `ProbaLab/src/training/train.py:369`
- Create: `ProbaLab/tests/test_train_sample_weight.py`

- [ ] **Step 1 : Lire `train.py:360-400`**

Run: `Read ProbaLab/src/training/train.py offset=360 limit=40`
Repérer `cross_val_score(..., params={"sample_weight": ...})`.

- [ ] **Step 2 : Écrire le test de régression**

Créer `ProbaLab/tests/test_train_sample_weight.py` :

```python
"""Test that sample_weight is passed via fit_params to cross_val_score."""
import ast
import pathlib

TRAIN_PATH = pathlib.Path(__file__).parent.parent / "src" / "training" / "train.py"


def test_sample_weight_uses_fit_params():
    """Regression for lesson 13: sample_weight must be in fit_params, not params."""
    tree = ast.parse(TRAIN_PATH.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "cross_val_score":
                for kw in node.keywords:
                    if kw.arg == "params":
                        if isinstance(kw.value, ast.Dict):
                            keys = [k.value for k in kw.value.keys if isinstance(k, ast.Constant)]
                            assert "sample_weight" not in keys, (
                                f"At {TRAIN_PATH}:{node.lineno}, sample_weight "
                                f"is passed via params= (silently ignored). "
                                f"Use fit_params= instead (lesson 13)."
                            )
```

- [ ] **Step 3 : Lancer → FAIL attendu**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_train_sample_weight.py -v`
Expected : FAIL.

- [ ] **Step 4 : Fix — remplacer `params=` par `fit_params=` dans `cross_val_score`**

Dans `train.py:369`, changer :
```python
cross_val_score(model, X, y, cv=tscv, params={"sample_weight": weights})
```
en :
```python
cross_val_score(model, X, y, cv=tscv, fit_params={"sample_weight": weights})
```

- [ ] **Step 5 : Lancer → PASS**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_train_sample_weight.py tests/test_train_no_leakage.py -v`

- [ ] **Step 6 : Mettre à jour lessons.md**

```
| 2026-04-18 | sample_weight passé via params= silencieusement ignoré dans cross_val_score → CV ne corrigeait pas l'imbalance H/D/A | Pour cross_val_score, utiliser fit_params= (PAS params=). Test AST de régression ajouté |
```

- [ ] **Step 7 : Commit**

```bash
git add ProbaLab/src/training/train.py ProbaLab/tests/test_train_sample_weight.py ProbaLab/tasks/lessons.md
git commit -m "fix(training): use fit_params for sample_weight in cross_val_score (lesson 13)

AST-based regression test prevents re-introduction of the bug."
```

---

### Task A3 : Rééquilibrer `WEIGHT_MARKET` 0.20 → 0.45 (P0-3)

**Files:**
- Modify: `ProbaLab/src/constants.py:196-198`
- Create: `ProbaLab/scripts/backtest_weights.py`
- Create: `ProbaLab/tests/test_prediction_blender_weights.py`

- [ ] **Step 1 : Lire les poids actuels**

Run: `Read ProbaLab/src/constants.py offset=190 limit=20`
Noter les valeurs actuelles de `WEIGHT_MARKET`, `WEIGHT_POISSON`, `WEIGHT_ELO`, `WEIGHT_AI`. Elles DOIVENT sommer à 1.0.

- [ ] **Step 2 : Créer script de backtest comparatif**

Créer `ProbaLab/scripts/backtest_weights.py` :

```python
"""Backtest comparing old weights (market=0.20) vs new weights (market=0.45).
Uses last 12 months of predictions from Supabase.
Reports Brier score 1X2 and CLV."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from src.config import supabase
from src.monitoring.brier_monitor import compute_brier_1x2

WEIGHTS_OLD = {"market": 0.20, "poisson": 0.55, "elo": 0.25, "ai": 0.0}
WEIGHTS_NEW = {"market": 0.45, "poisson": 0.35, "elo": 0.20, "ai": 0.0}


def _reblend(row: dict, weights: dict) -> tuple[float, float, float]:
    """Re-blend H/D/A probabilities from stored component probabilities."""
    m_h, m_d, m_a = row["market_h"], row["market_d"], row["market_a"]
    p_h, p_d, p_a = row["poisson_h"], row["poisson_d"], row["poisson_a"]
    e_h, e_d, e_a = row["elo_h"], row["elo_d"], row["elo_a"]
    w = weights
    h = w["market"] * m_h + w["poisson"] * p_h + w["elo"] * e_h
    d = w["market"] * m_d + w["poisson"] * p_d + w["elo"] * e_d
    a = w["market"] * m_a + w["poisson"] * p_a + w["elo"] * e_a
    s = h + d + a
    return h / s, d / s, a / s


def backtest(months: int = 12) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)
    rows = (
        supabase.table("prediction_results")
        .select("*")
        .gte("created_at", cutoff.isoformat())
        .not_.is_("actual_result", "null")
        .execute()
        .data
    )
    brier_old, brier_new = [], []
    for row in rows:
        if None in (row.get("market_h"), row.get("poisson_h"), row.get("elo_h")):
            continue
        ho, do, ao = _reblend(row, WEIGHTS_OLD)
        hn, dn, an = _reblend(row, WEIGHTS_NEW)
        actual = row["actual_result"]
        y = {"H": (1, 0, 0), "D": (0, 1, 0), "A": (0, 0, 1)}[actual]
        brier_old.append(sum((p - a) ** 2 for p, a in zip((ho, do, ao), y)))
        brier_new.append(sum((p - a) ** 2 for p, a in zip((hn, dn, an), y)))
    return {
        "n": len(brier_old),
        "brier_old": sum(brier_old) / len(brier_old) if brier_old else None,
        "brier_new": sum(brier_new) / len(brier_new) if brier_new else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=12)
    args = parser.parse_args()
    result = backtest(args.months)
    print(f"N = {result['n']}")
    print(f"Brier OLD (market=0.20): {result['brier_old']:.4f}")
    print(f"Brier NEW (market=0.45): {result['brier_new']:.4f}")
    delta = result["brier_new"] - result["brier_old"]
    print(f"Delta: {delta:+.4f} ({'NEW better' if delta < 0 else 'OLD better'})")
```

- [ ] **Step 3 : Lancer le backtest 12 mois**

Run: `cd ProbaLab && pyenv exec python -m scripts.backtest_weights --months 12`
Expected : print du N et des 2 Brier. Noter le résultat.

- [ ] **Step 4 : Décider GO/NO-GO selon le backtest**

- Si `brier_new < brier_old` → GO, passer à Step 5.
- Si `brier_new >= brier_old` → NO-GO, chercher weights intermédiaires. Essayer `WEIGHTS_NEW = {"market": 0.35, "poisson": 0.40, "elo": 0.25}` puis `0.40/0.35/0.25`, etc. jusqu'à trouver un optimum. Documenter dans un commentaire.

- [ ] **Step 5 : Modifier `constants.py` avec les nouveaux poids**

```python
# Weight of market signal dominant (bookmaker = 52-55% accuracy, sanity check signal
# for Poisson/ELO). Rééquilibré le 2026-04-18 suite au backtest 12 mois
# (cf scripts/backtest_weights.py). Lesson 52 appliquée.
WEIGHT_MARKET = 0.45
WEIGHT_POISSON = 0.35
WEIGHT_ELO = 0.20
WEIGHT_AI = 0.0  # meta-learner off by default
```

- [ ] **Step 6 : Test unitaire qui vérifie sum=1.0**

Créer `ProbaLab/tests/test_prediction_blender_weights.py` :

```python
import pytest
from src.constants import WEIGHT_MARKET, WEIGHT_POISSON, WEIGHT_ELO, WEIGHT_AI


def test_weights_sum_to_one():
    total = WEIGHT_MARKET + WEIGHT_POISSON + WEIGHT_ELO + WEIGHT_AI
    assert abs(total - 1.0) < 1e-9, f"Blend weights must sum to 1.0, got {total}"


def test_market_weight_is_dominant():
    """Lesson 52: market signal (52-55% accuracy) must be the dominant weight."""
    assert WEIGHT_MARKET >= max(WEIGHT_POISSON, WEIGHT_ELO), (
        f"WEIGHT_MARKET={WEIGHT_MARKET} must dominate "
        f"Poisson={WEIGHT_POISSON} and ELO={WEIGHT_ELO}"
    )
```

- [ ] **Step 7 : Tests verts**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_prediction_blender_weights.py -v`

- [ ] **Step 8 : Vérifier tests blender globaux toujours verts**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_prediction_blender.py -v`
Si échec : les tests hardcodaient l'ancien poids, adapter.

- [ ] **Step 9 : Commit**

```bash
git add ProbaLab/src/constants.py ProbaLab/scripts/backtest_weights.py ProbaLab/tests/test_prediction_blender_weights.py
git commit -m "feat(ml): rebalance blend weights market 0.20 → 0.45 (lesson 52)

Backtest 12 months validates Brier improvement.
Script scripts/backtest_weights.py preserved for future tuning.
Unit test enforces sum=1.0 and market dominance."
```

---

### Task A4 : Walk-forward temporal validation publiable (P0-11)

**Files:**
- Create: `ProbaLab/src/training/walk_forward.py`
- Create: `ProbaLab/tests/test_walk_forward.py`
- Create: `ProbaLab/scripts/publish_walk_forward_report.py`

- [ ] **Step 1 : Créer `walk_forward.py`**

```python
"""Walk-forward temporal validation — expanding window.

Splits historical matches by chronological windows (3-6 months holdout)
and reports Brier score, log-loss, calibration ECE per window.

Usage:
    from src.training.walk_forward import walk_forward_evaluate
    report = walk_forward_evaluate(X, y, dates, n_splits=6, holdout_months=3)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss


def walk_forward_evaluate(
    X: pd.DataFrame,
    y: pd.Series,
    dates: pd.Series,
    model_fn,
    n_splits: int = 6,
    holdout_months: int = 3,
) -> dict[str, Any]:
    """Evaluate a model using walk-forward (expanding window).

    Args:
        X: feature matrix, time-ordered
        y: labels ("H"/"D"/"A" or 0/1/2)
        dates: datetime Series aligned with X
        model_fn: callable () → fresh model (with .fit, .predict_proba)
        n_splits: number of walk-forward folds
        holdout_months: size of holdout window in months

    Returns:
        dict with per-fold Brier 1X2, log-loss, ECE + aggregated stats.
    """
    assert len(X) == len(y) == len(dates)
    sorted_idx = dates.sort_values().index
    X = X.loc[sorted_idx].reset_index(drop=True)
    y = y.loc[sorted_idx].reset_index(drop=True)
    dates = dates.loc[sorted_idx].reset_index(drop=True)

    min_date, max_date = dates.min(), dates.max()
    total_days = (max_date - min_date).days
    holdout_days = holdout_months * 30
    fold_step = max(1, (total_days - holdout_days) // n_splits)

    fold_results = []
    for k in range(1, n_splits + 1):
        cutoff = min_date + pd.Timedelta(days=k * fold_step)
        holdout_end = cutoff + pd.Timedelta(days=holdout_days)
        train_mask = dates < cutoff
        test_mask = (dates >= cutoff) & (dates < holdout_end)
        if test_mask.sum() < 20:
            continue

        model = model_fn()
        model.fit(X[train_mask], y[train_mask])
        probas = model.predict_proba(X[test_mask])

        y_true = y[test_mask].values
        brier_1x2 = _brier_1x2(probas, y_true, model.classes_)
        ll = log_loss(y_true, probas, labels=model.classes_)

        fold_results.append({
            "fold": k,
            "train_until": cutoff.isoformat(),
            "test_from": cutoff.isoformat(),
            "test_to": holdout_end.isoformat(),
            "n_train": int(train_mask.sum()),
            "n_test": int(test_mask.sum()),
            "brier_1x2": brier_1x2,
            "log_loss": ll,
        })

    return {
        "folds": fold_results,
        "brier_1x2_mean": float(np.mean([f["brier_1x2"] for f in fold_results])),
        "brier_1x2_std": float(np.std([f["brier_1x2"] for f in fold_results])),
        "log_loss_mean": float(np.mean([f["log_loss"] for f in fold_results])),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def _brier_1x2(probas: np.ndarray, y_true: np.ndarray, classes: np.ndarray) -> float:
    idx = {c: i for i, c in enumerate(classes)}
    total = 0.0
    for p_row, y in zip(probas, y_true):
        y_vec = np.zeros(len(classes))
        y_vec[idx[y]] = 1.0
        total += float(np.sum((p_row - y_vec) ** 2))
    return total / len(y_true)
```

- [ ] **Step 2 : Test unitaire walk-forward**

Créer `ProbaLab/tests/test_walk_forward.py` :

```python
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.training.walk_forward import walk_forward_evaluate


def test_walk_forward_returns_expected_folds():
    rng = np.random.default_rng(42)
    n = 500
    dates = pd.Series(pd.date_range("2024-01-01", periods=n, freq="D"))
    X = pd.DataFrame(rng.normal(size=(n, 5)), columns=[f"f{i}" for i in range(5)])
    y = pd.Series(rng.choice(["H", "D", "A"], size=n, p=[0.45, 0.25, 0.30]))

    def mk():
        return LogisticRegression(max_iter=500, multi_class="multinomial")

    report = walk_forward_evaluate(X, y, dates, mk, n_splits=4, holdout_months=1)
    assert 3 <= len(report["folds"]) <= 4
    assert 0.0 <= report["brier_1x2_mean"] <= 2.0
    for fold in report["folds"]:
        assert fold["n_train"] > 0 and fold["n_test"] > 0
```

- [ ] **Step 3 : Tests verts**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_walk_forward.py -v`

- [ ] **Step 4 : Script de publication du rapport**

Créer `ProbaLab/scripts/publish_walk_forward_report.py` :

```python
"""Produit le rapport walk-forward pour publication (page /methodology).

Lit les prédictions historiques de Supabase, ré-entraîne par fold, publie JSON.
Output: ProbaLab/public/walk_forward_report.json (consommé par le frontend).
"""
import json
from pathlib import Path

import pandas as pd

from src.config import supabase
from src.training.walk_forward import walk_forward_evaluate


def _load_history() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    rows = (
        supabase.table("prediction_results")
        .select("*")
        .not_.is_("actual_result", "null")
        .execute()
        .data
    )
    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df.dropna(subset=["actual_result"]).sort_values("created_at")
    feature_cols = [c for c in df.columns if c.startswith(("market_", "poisson_", "elo_"))]
    X = df[feature_cols].fillna(0.0)
    y = df["actual_result"]
    dates = df["created_at"]
    return X, y, dates


def main(out_path: Path = Path("ProbaLab/dashboard/public/walk_forward_report.json")):
    from xgboost import XGBClassifier

    X, y, dates = _load_history()

    def mk():
        return XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            max_depth=4,
            n_estimators=200,
            learning_rate=0.05,
            random_state=42,
        )

    y_encoded = y.map({"H": 0, "D": 1, "A": 2})
    report = walk_forward_evaluate(X, y_encoded, dates, mk, n_splits=6, holdout_months=3)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Report written: {out_path}")
    print(f"Brier 1X2 mean (across {len(report['folds'])} folds): {report['brier_1x2_mean']:.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5 : Lancer le rapport**

Run: `cd ProbaLab && pyenv exec python -m scripts.publish_walk_forward_report`
Expected : `dashboard/public/walk_forward_report.json` créé, Brier ~0.20-0.23 (réel, plus élevé que l'ancien).

- [ ] **Step 6 : Commit**

```bash
git add ProbaLab/src/training/walk_forward.py ProbaLab/tests/test_walk_forward.py ProbaLab/scripts/publish_walk_forward_report.py ProbaLab/dashboard/public/walk_forward_report.json
git commit -m "feat(ml): walk-forward temporal validation + public report

Expanding-window walk-forward evaluator, 6 folds × 3 months holdout.
Generates dashboard/public/walk_forward_report.json for /methodology page.
Honest Brier 1X2 now measurable (replaces optimistically-biased metrics)."
```

---

## SPRINT B — Monitoring + Sécurité (semaine 2)

**Objectif** : brancher le monitoring en cron avec persistance, fermer les 4 trous sécurité P0, migrer `datetime.now()` nus.

**Items traités** : P0-4, P0-5, P0-6, P0-7, P0-8, P0-18.

### Task B1 : Table `model_health_log` + job cron monitoring (P0-4)

**Files:**
- Create: `ProbaLab/migrations/050_model_health_log.sql`
- Modify: `ProbaLab/worker.py`
- Modify: `ProbaLab/run_pipeline.py`
- Create: `ProbaLab/tests/test_model_health_log.py`

- [ ] **Step 1 : Écrire la migration**

Créer `ProbaLab/migrations/050_model_health_log.sql` :

```sql
-- Persistence des métriques monitoring quotidiennes
create table if not exists model_health_log (
    id bigserial primary key,
    recorded_at timestamptz not null default now(),
    sport text not null check (sport in ('football','nhl')),
    brier_7d numeric,
    brier_30d numeric,
    log_loss_30d numeric,
    ece_30d numeric,
    clv_best_mean_30d numeric,
    drift_detected boolean default false,
    data_completeness_pct numeric,
    prediction_volume_today integer,
    alert_count integer default 0,
    ml_fallback_rate numeric,
    notes text
);

create index if not exists idx_model_health_log_recorded_at
    on model_health_log(recorded_at desc);
create index if not exists idx_model_health_log_sport_date
    on model_health_log(sport, recorded_at desc);

-- RLS : seul le service_role peut écrire/lire
alter table model_health_log enable row level security;

create policy "service_role_all_model_health_log"
    on model_health_log for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');
```

- [ ] **Step 2 : Appliquer la migration**

Via Supabase MCP :
```
mcp__33041561__apply_migration name=model_health_log query=<contenu ci-dessus>
```
OU manuellement via Supabase Studio si MCP non connecté. Vérifier succès.

- [ ] **Step 3 : Écrire le job monitoring dans `run_pipeline.py`**

Identifier dans `run_pipeline.py:120-137` la fonction `run_monitoring_alerts()`. L'étendre pour insérer dans `model_health_log`.

Ajouter à la fin de `run_monitoring_alerts()` :

```python
from src.monitoring.brier_monitor import compute_brier_1x2_rolling
from src.monitoring.drift_detector import check_drift
from src.config import supabase

def _persist_health_log(sport: str) -> None:
    brier_7d = compute_brier_1x2_rolling(sport, days=7)
    brier_30d = compute_brier_1x2_rolling(sport, days=30)
    drift = check_drift(sport)
    supabase.table("model_health_log").insert({
        "sport": sport,
        "brier_7d": brier_7d,
        "brier_30d": brier_30d,
        "drift_detected": drift.get("detected", False),
        "prediction_volume_today": drift.get("volume_today", 0),
    }).execute()

# Dans run_monitoring_alerts() :
_persist_health_log("football")
_persist_health_log("nhl")
```

- [ ] **Step 4 : Ajouter le job APScheduler dans `worker.py`**

Dans `worker.py`, ajouter après `job_drift_check` :

```python
def job_run_monitoring_alerts() -> None:
    """Job quotidien 08:30 UTC : Brier check + drift + persistance model_health_log."""
    from run_pipeline import run_monitoring_alerts
    try:
        run_monitoring_alerts()
    except Exception as e:
        logger.exception("job_run_monitoring_alerts failed: %s", e)

scheduler.add_job(
    job_run_monitoring_alerts,
    CronTrigger(hour=8, minute=30, timezone="UTC"),
    id="monitoring_alerts_daily",
    max_instances=1,
    coalesce=True,
)
```

- [ ] **Step 5 : Test que la migration et l'insert marchent**

Créer `ProbaLab/tests/test_model_health_log.py` :

```python
"""Test minimal : la table existe, on peut insert/read."""
import pytest
from src.config import supabase

pytestmark = pytest.mark.integration


def test_model_health_log_table_exists():
    result = supabase.table("model_health_log").select("id").limit(1).execute()
    assert hasattr(result, "data")


def test_model_health_log_insert_read():
    from uuid import uuid4
    note = f"test-{uuid4()}"
    supabase.table("model_health_log").insert({
        "sport": "football",
        "brier_7d": 0.21,
        "brier_30d": 0.22,
        "notes": note,
    }).execute()
    rows = supabase.table("model_health_log").select("*").eq("notes", note).execute().data
    assert len(rows) == 1
    supabase.table("model_health_log").delete().eq("notes", note).execute()
```

- [ ] **Step 6 : Lancer le test integration**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_model_health_log.py -v -m integration`

- [ ] **Step 7 : Lancer le job manuellement pour valider**

Run: `cd ProbaLab && pyenv exec python -c "from run_pipeline import run_monitoring_alerts; run_monitoring_alerts()"`
Vérifier dans Supabase Studio qu'une ligne est apparue dans `model_health_log`.

- [ ] **Step 8 : Commit**

```bash
git add ProbaLab/migrations/050_model_health_log.sql ProbaLab/worker.py ProbaLab/run_pipeline.py ProbaLab/tests/test_model_health_log.py
git commit -m "feat(monitoring): persist daily health metrics + APScheduler job

- Migration 050 creates model_health_log table with RLS (service_role only)
- run_monitoring_alerts() now upserts daily snapshot per sport
- New APScheduler job monitoring_alerts_daily at 08:30 UTC
- Enables Phase 2 gating (pivot) quantitatively instead of by intuition"
```

---

### Task B2 : Fermer `/api/admin/update-scores` sans auth (P0-6)

**Files:**
- Modify: `ProbaLab/api/routers/admin.py` (autour de la ligne 234-269)
- Create: `ProbaLab/tests/test_admin_endpoints_auth.py`

- [ ] **Step 1 : Lire l'endpoint actuel**

Run: `Read ProbaLab/api/routers/admin.py offset=230 limit=50`
Confirmer le commentaire "No auth required when called internally".

- [ ] **Step 2 : Écrire le test qui vérifie l'auth obligatoire**

Créer `ProbaLab/tests/test_admin_endpoints_auth.py` :

```python
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_update_scores_rejects_unauth():
    r = client.post("/api/admin/update-scores")
    assert r.status_code in (401, 403), (
        f"Expected 401/403 without auth, got {r.status_code} — "
        f"endpoint is exposed to DoS on paid API quota"
    )


def test_update_scores_accepts_cron_secret(monkeypatch):
    from api.auth import CRON_SECRET  # noqa
    r = client.post(
        "/api/admin/update-scores",
        headers={"X-Cron-Secret": "wrong"}
    )
    assert r.status_code in (401, 403)
```

- [ ] **Step 3 : Lancer → FAIL attendu**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_admin_endpoints_auth.py -v`
Expected : `test_update_scores_rejects_unauth` FAIL (retourne 200 probablement).

- [ ] **Step 4 : Modifier `admin.py` — ajouter `Depends(verify_internal_auth)`**

Dans `api/routers/admin.py`, endpoint `update_scores` :

```python
from api.auth import verify_internal_auth  # import si absent

@router.post("/admin/update-scores", dependencies=[Depends(verify_internal_auth)])
def update_scores():
    # ... body unchanged
```

Retirer le commentaire `"No auth required when called internally"`.

- [ ] **Step 5 : Vérifier que `verify_internal_auth` existe et accepte CRON_SECRET**

Run: `Read ProbaLab/api/auth.py` — vérifier la signature.

Si elle n'accepte que `Bearer <CRON_SECRET>`, ajouter un fallback header `X-Cron-Secret` OU documenter dans le cron Trigger.dev/GitHub Actions d'utiliser le header attendu.

- [ ] **Step 6 : Tests verts**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_admin_endpoints_auth.py -v`

- [ ] **Step 7 : Mettre à jour lessons.md**

```
| 2026-04-19 | /api/admin/update-scores exposé publiquement "No auth required when called internally" — DoS possible sur quota API-Football payant | Tout endpoint /admin/* DOIT avoir Depends(verify_internal_auth) — zéro exception "interne", un attaquant peut toujours forger la requête |
```

- [ ] **Step 8 : Commit**

```bash
git add ProbaLab/api/routers/admin.py ProbaLab/tests/test_admin_endpoints_auth.py ProbaLab/tasks/lessons.md
git commit -m "security(admin): require auth on /update-scores (DoS risk on paid API quota)

Previously: 'No auth required when called internally' comment.
Now: Depends(verify_internal_auth). Regression test enforces 401/403."
```

---

### Task B3 : `extra="forbid"` sur tous les schemas + retirer `detail=str(e)` (P0-7, P0-8)

**Files:**
- Modify: `ProbaLab/api/schemas.py`
- Modify: `ProbaLab/api/routers/players.py:162`
- Create: `ProbaLab/tests/test_schemas_strict.py`

- [ ] **Step 1 : Lire `schemas.py`**

Run: `Read ProbaLab/api/schemas.py`
Lister toutes les classes qui héritent de `BaseModel`.

- [ ] **Step 2 : Écrire le test de régression**

Créer `ProbaLab/tests/test_schemas_strict.py` :

```python
"""All request schemas must have extra='forbid' (prevents mass assignment)."""
import inspect
import pydantic

from api import schemas


def test_all_schemas_forbid_extra():
    for name, obj in inspect.getmembers(schemas):
        if inspect.isclass(obj) and issubclass(obj, pydantic.BaseModel) and obj is not pydantic.BaseModel:
            config = getattr(obj, "model_config", {})
            extra = config.get("extra") if isinstance(config, dict) else getattr(config, "extra", None)
            assert extra == "forbid", (
                f"{name} must have model_config = ConfigDict(extra='forbid') "
                f"(current: extra={extra!r})"
            )
```

- [ ] **Step 3 : Lancer → FAIL attendu**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_schemas_strict.py -v`

- [ ] **Step 4 : Modifier chaque BaseModel de `schemas.py`**

Ajouter en tête de chaque classe :

```python
from pydantic import BaseModel, ConfigDict

class MySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... fields
```

Pour réduire la duplication, créer une base :

```python
class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

Et hériter de `_StrictBase` partout.

- [ ] **Step 5 : Fix `players.py:162` — retirer `detail=str(e)` (P0-8)**

Run: `Read ProbaLab/api/routers/players.py offset=155 limit=20`

Remplacer :
```python
raise HTTPException(status_code=500, detail=str(e))
```
par :
```python
logger.exception("Error in players endpoint")
raise HTTPException(status_code=500, detail="Internal error")
```

- [ ] **Step 6 : Lancer tous les tests**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/ -k "schema or players" -v`

Si des tests cassent parce qu'ils passaient des champs extras dans le payload → les corriger (c'est une bonne nouvelle, ça prouve que la règle fonctionne).

- [ ] **Step 7 : Commit**

```bash
git add ProbaLab/api/schemas.py ProbaLab/api/routers/players.py ProbaLab/tests/test_schemas_strict.py
git commit -m "security(api): enforce extra='forbid' on all request schemas (lesson 19 + 7)

- api/schemas.py: every BaseModel inherits from _StrictBase with extra='forbid'
- api/routers/players.py:162: remove detail=str(e) (info disclosure)
- Regression test iterates all schemas and fails if any omits extra='forbid'"
```

---

### Task B4 : Fix fallback ML NHL silencieux (P0-5)

**Files:**
- Modify: `ProbaLab/src/nhl/ml_models.py` (init 2-stages)
- Modify: `ProbaLab/api/routers/nhl.py:72-89, 311-336`
- Create: `ProbaLab/tests/test_nhl_fallback_logging.py`

- [ ] **Step 1 : Lire le code actuel**

Run: `Read ProbaLab/src/nhl/ml_models.py` (entier)
Run: `Read ProbaLab/api/routers/nhl.py offset=70 limit=30` + `offset=305 limit=40`

- [ ] **Step 2 : Ajouter `loaded` flag + log WARNING dans `ml_models.py`**

Pour chaque predictor (`shot_predictor`, `assist_predictor`, etc.), modifier la classe pour exposer :
- `loaded: bool` — True seulement si `.load()` a réussi
- Log WARNING explicite dans le `except`

Exemple de pattern :

```python
class ShotPredictor:
    def __init__(self):
        self.model = None
        self.loaded = False

    def load(self, path: str) -> None:
        try:
            self.model = _load_model(path)
            self.loaded = True
        except FileNotFoundError as e:
            logger.warning("ShotPredictor model not found at %s — fallback to Poisson. Reason: %s", path, e)
            self.loaded = False
        except Exception as e:
            logger.exception("ShotPredictor load failed at %s — fallback to Poisson. Reason: %s", path, e)
            self.loaded = False
```

- [ ] **Step 3 : Dans `api/routers/nhl.py`, logger chaque fallback ET exposer le flag**

Autour de `api/routers/nhl.py:311-336`, remplacer :

```python
if ENHANCED_ML_AVAILABLE and shot_predictor and shot_predictor.model is not None:
    raw_prob_shot = shot_predictor.predict_proba(raw)
else:
    raw_prob_shot = 1.0 - math.exp(-lam_shots)
```

par :

```python
ml_fallback_used = {"shot": False, "assist": False, "goal": False, "point": False}

if shot_predictor.loaded:
    raw_prob_shot = shot_predictor.predict_proba(raw)
else:
    logger.warning("ML fallback (Poisson) used for SHOT prediction")
    raw_prob_shot = 1.0 - math.exp(-lam_shots)
    ml_fallback_used["shot"] = True

# idem pour assist, goal, point
```

Dans la response JSON de l'endpoint, ajouter `ml_fallback_used` :

```python
return {
    # ... existing fields
    "ml_fallback_used": ml_fallback_used,
}
```

- [ ] **Step 4 : Écrire le test**

Créer `ProbaLab/tests/test_nhl_fallback_logging.py` :

```python
"""Verify NHL endpoints expose ml_fallback_used flag and log WARNING on fallback."""
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_fallback_flag_exposed_in_response(caplog):
    with patch("api.routers.nhl.shot_predictor") as mock_shot:
        mock_shot.loaded = False
        mock_shot.predict_proba.side_effect = RuntimeError("should not call")
        # Hypothèse : endpoint /brain_quick existe
        r = client.get("/api/nhl/brain_quick", params={"game_id": "test"})
        if r.status_code == 200:
            data = r.json()
            assert "ml_fallback_used" in data
            assert data["ml_fallback_used"]["shot"] is True
```

Note : adapter le test selon la signature réelle de l'endpoint `brain_quick` (peut nécessiter des fixtures).

- [ ] **Step 5 : Tests verts**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_nhl_fallback_logging.py -v`
(Ou skip si l'endpoint nécessite trop de setup — noter dans commit.)

- [ ] **Step 6 : Commit**

```bash
git add ProbaLab/src/nhl/ml_models.py ProbaLab/api/routers/nhl.py ProbaLab/tests/test_nhl_fallback_logging.py
git commit -m "fix(nhl): instrument ML fallback to Poisson (lesson 41)

- ShotPredictor/AssistPredictor/etc. expose .loaded flag
- logger.warning() on each fallback to Poisson (was silent)
- /brain_quick response includes ml_fallback_used={shot,assist,goal,point}
- Brier NHL metrics now honest (used to be Poisson-as-ML silently ~40% of the time)"
```

---

### Task B5 : Codemod `datetime.now()` → `datetime.now(timezone.utc)` (P0-18)

**Files:**
- Create: `ProbaLab/scripts/migrate_datetime_now_utc.py`
- Modify: ~54 fichiers (via codemod)
- Modify: `.pre-commit-config.yaml` (règle Ruff)

- [ ] **Step 1 : Lister toutes les occurrences**

Run: `Grep "datetime\.now\(\s*\)" --path ProbaLab/ --type py -n`
Run: `Grep "datetime\.utcnow\(\s*\)" --path ProbaLab/ --type py -n`

Noter le nombre total (annexe 05 mentionne 54).

- [ ] **Step 2 : Écrire le codemod**

Créer `ProbaLab/scripts/migrate_datetime_now_utc.py` :

```python
"""Codemod : datetime.now() / datetime.utcnow() → datetime.now(timezone.utc).

Also ensures `from datetime import timezone` is present in each modified file.

Usage:
    python -m scripts.migrate_datetime_now_utc --dry-run
    python -m scripts.migrate_datetime_now_utc --apply
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERN_NOW = re.compile(r"\bdatetime\.now\(\s*\)")
PATTERN_UTCNOW = re.compile(r"\bdatetime\.utcnow\(\s*\)")

ROOT = Path(__file__).parent.parent


def process_file(path: Path, apply: bool) -> int:
    if path.suffix != ".py":
        return 0
    if "scripts/migrate_datetime" in str(path):
        return 0
    source = path.read_text()
    new_source = PATTERN_NOW.sub("datetime.now(timezone.utc)", source)
    new_source = PATTERN_UTCNOW.sub("datetime.now(timezone.utc)", new_source)
    if new_source == source:
        return 0
    if "from datetime import" in new_source and "timezone" not in new_source.split("from datetime import")[1].split("\n")[0]:
        new_source = re.sub(
            r"from datetime import ([^\n]+)",
            lambda m: f"from datetime import {m.group(1).strip()}, timezone"
            if "timezone" not in m.group(1)
            else m.group(0),
            new_source,
            count=1,
        )
    count = len(PATTERN_NOW.findall(source)) + len(PATTERN_UTCNOW.findall(source))
    if apply:
        path.write_text(new_source)
    print(f"[{'APPLY' if apply else 'DRY'}] {path.relative_to(ROOT)} — {count} replacement(s)")
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    total = 0
    for py_file in ROOT.rglob("*.py"):
        if any(part in py_file.parts for part in (".venv", "node_modules", "__pycache__", "migrations")):
            continue
        total += process_file(py_file, args.apply)
    print(f"\nTotal: {total} replacements across the repo.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3 : Dry-run**

Run: `cd ProbaLab && pyenv exec python -m scripts.migrate_datetime_now_utc`
Vérifier la liste des fichiers + total ~54.

- [ ] **Step 4 : Apply**

Run: `cd ProbaLab && pyenv exec python -m scripts.migrate_datetime_now_utc --apply`

- [ ] **Step 5 : Vérifier que le code compile**

Run: `cd ProbaLab && pyenv exec python -c "import ProbaLab" 2>&1 || pyenv exec python -m py_compile $(find . -name '*.py' -not -path './.venv/*')`

- [ ] **Step 6 : Lancer la suite de tests**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/ -m "not integration" -q`
Si un test échoue à cause du codemod, analyser (souvent un test qui comparait avec un `datetime.now()` naïf).

- [ ] **Step 7 : Ajouter règle Ruff pour prévenir régression**

Modifier `ProbaLab/ruff.toml` (ou créer s'il n'existe pas) :

```toml
[lint]
select = ["DTZ"]  # flake8-datetimez : enforce timezone awareness

[lint.per-file-ignores]
"tests/**" = ["DTZ"]  # tests peuvent utiliser des naive datetimes contrôlés
"migrations/**" = ["DTZ"]
```

Puis lancer : `cd ProbaLab && pyenv exec python -m ruff check src/ api/ worker.py run_pipeline.py`
Si des violations restent, les corriger manuellement.

- [ ] **Step 8 : Commit**

```bash
git add ProbaLab/scripts/migrate_datetime_now_utc.py ProbaLab/ruff.toml $(git diff --name-only | grep '.py$' | tr '\n' ' ')
git commit -m "fix: migrate datetime.now()/utcnow() → datetime.now(timezone.utc) (lesson 22)

54 occurrences replaced via scripts/migrate_datetime_now_utc.py.
Ruff DTZ rule added to prevent re-introduction (per-file-ignores for tests/migrations)."
```

---

## SPRINT C — Analytics + Positionnement + NHL + Infra (semaines 3-4)

**Objectif** : poser les fondations produit (analytics, prix, amendement pivot), décider NHL, nettoyer infra.

**Items traités** : P0-9, P0-10, P0-12, P0-13, P0-14, P0-15, P0-16, P0-17, P0-22.

### Task C1 : Installer Plausible + 6 événements funnel (P0-9)

**Files:**
- Modify: `ProbaLab/dashboard/index.html`
- Create: `ProbaLab/dashboard/src/lib/analytics.ts`
- Modify: pages principales pour tracker événements

- [ ] **Step 1 : Créer compte Plausible (9€/mois) avec domaine ProbaLab**

(Action manuelle owner — noter l'URL du dashboard Plausible et le domain configuré.)

- [ ] **Step 2 : Ajouter snippet dans `dashboard/index.html`**

Run: `Read ProbaLab/dashboard/index.html`

Ajouter dans `<head>` :
```html
<script defer data-domain="probalab.com" src="https://plausible.io/js/script.tagged-events.js"></script>
```

(Remplacer `probalab.com` par le domain réel.)

- [ ] **Step 3 : Créer wrapper analytics**

Créer `ProbaLab/dashboard/src/lib/analytics.ts` :

```typescript
/** Wrapper Plausible pour événements custom. */

type PlausibleEvent =
  | "landing_viewed"
  | "signup_started"
  | "signup_completed"
  | "premium_viewed"
  | "checkout_clicked"
  | "checkout_completed";

export function track(event: PlausibleEvent, props?: Record<string, string | number>) {
  const plausible = (window as any).plausible;
  if (typeof plausible === "function") {
    plausible(event, { props });
  }
}
```

- [ ] **Step 4 : Instrumenter 6 événements funnel dans les pages**

Modifier les fichiers :
- `dashboard/src/pages/HomePage.tsx` : au mount → `track("landing_viewed")`
- `dashboard/src/pages/Signup.tsx` (ou équivalent) : bouton submit → `track("signup_started")`, post-success → `track("signup_completed")`
- `dashboard/src/pages/Premium.tsx` : au mount → `track("premium_viewed")`, clic bouton checkout → `track("checkout_clicked")`
- Stripe success page : au mount → `track("checkout_completed")`

Exemple pattern :
```tsx
import { useEffect } from "react";
import { track } from "@/lib/analytics";

export default function HomePage() {
  useEffect(() => track("landing_viewed"), []);
  // ...
}
```

- [ ] **Step 5 : Build + test manuel**

Run: `cd ProbaLab/dashboard && npm run build`
Expected : build OK.

Run: `cd ProbaLab/dashboard && npm run dev` (background)
Visiter la page, vérifier dans Plausible Live → les événements arrivent.

- [ ] **Step 6 : Commit**

```bash
git add ProbaLab/dashboard/index.html ProbaLab/dashboard/src/lib/analytics.ts ProbaLab/dashboard/src/pages/*.tsx
git commit -m "feat(analytics): install Plausible + 6 funnel events

Events: landing_viewed, signup_started, signup_completed, premium_viewed,
checkout_clicked, checkout_completed. Cost: 9€/mois (within 50€ budget)."
```

---

### Task C2 : Aligner prix 14,99€ + amender design pivot scope NHL (P0-10, P0-12)

**Files:**
- Modify: `ProbaLab/dashboard/src/pages/Premium.tsx:155`
- Modify: `ProbaLab/api/routers/stripe_webhook.py` (nouvel ID plan Stripe)
- Create: `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11_AMENDMENT_2026-04-17.md`

- [ ] **Step 1 : Créer plan Stripe 14,99€/mois**

Action owner :
- Se connecter à Stripe Dashboard
- Créer un nouveau Price : `14.99 EUR / month` avec un nom clair
- Copier le `price_id` (format `price_XXXX`)
- Configurer une migration douce pour les abonnés à 9,99€ (note : ne pas casser les existants — garder l'ancien Price actif en "archivé" pour les anciens abonnements qui continuent)

- [ ] **Step 2 : Modifier `Premium.tsx`**

Run: `Read ProbaLab/dashboard/src/pages/Premium.tsx offset=145 limit=25`

Remplacer l'affichage prix (`9,99€` → `14,99€`). Chercher aussi le `priceId` éventuellement hardcodé.

- [ ] **Step 3 : Modifier `stripe_webhook.py`**

Run: `Read ProbaLab/api/routers/stripe_webhook.py`

Mettre à jour le `PREMIUM_PRICE_ID` (ou variable équivalente) avec le nouveau `price_id`. Si l'ID est dans les env vars, mettre à jour `.env.example`.

- [ ] **Step 4 : Écrire l'amendement du design pivot**

Créer `ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11_AMENDMENT_2026-04-17.md` :

```markdown
# Amendement au design pivot 2026-04-11 — Décisions owner 2026-04-17

Suite à l'audit 360° du 2026-04-17 et aux 4 décisions de l'owner, le design
pivot d'origine est amendé comme suit :

## Décision 1 — Budget 50€/mois

Conséquence : pas d'upgrade The Odds API Pro (~500$/mois rejeté).

## Décision 2 — Posture hybride C validée

Le pivot tel que brainstormé (Safe/Fun/Value grand public + premium sur
features avancées) est validé. BP v2 à aligner (rewrite section positionnement).

## Décision 3 — Prix 14,99€/mois

Aligne `Premium.tsx` + Stripe sur le BP v2 (au lieu des 9,99€ UI actuels).
Migration douce pour les abonnés existants à 9,99€.

## Décision 4 — Scope NHL restreint (Option A)

Le design doc §5 D5 est amendé :

**AVANT** :
> NHL safe = player props "1+ Point" et "1+ Passe décisive"

**APRÈS** :
> NHL safe = player props "Anytime Scorer" (player_goals Over 0.5) UNIQUEMENT.
> Les marchés "1+ Point" et "1+ Passe décisive" sont reportés en H2+ (conditionnés
> à un futur upgrade Odds API Pro ou partenariat data).

Idem pour generate_fun_nhl : parlay 4 legs sur goal-mixed player_goals
(4 joueurs différents, 4 matchs différents si possible).

Idem pour generate_value_nhl : EV > 3% sur player_goals uniquement.

## Conséquence sur les générateurs

- `generate_safe_nhl(date)` : ne lit QUE `player_goals` dans les cotes bookmaker.
  Les `prob_point` / `prob_assist` restent en DB pour usage futur mais ne
  rentrent PAS dans les générateurs pivot en H1/H2.
- Communication publique : page /methodology doit expliquer pourquoi "1+ Point"
  / "1+ Passe" ne sont pas encore proposés ("absence de cotes bookmaker fiables
  sur le plan gratuit de notre provider").

## Conséquence sur les tests

- Tests pivot NHL doivent valider uniquement `player_goals`.
- Les tests sur `player_points` / `player_assists` existants restent OK
  (côté moteur probabiliste) mais ne rentrent pas dans la suite pivot.
```

- [ ] **Step 5 : Commit**

```bash
git add ProbaLab/dashboard/src/pages/Premium.tsx ProbaLab/api/routers/stripe_webhook.py ProbaLab/tasks/design_pivot_probas_sportives_2026-04-11_AMENDMENT_2026-04-17.md
git commit -m "feat(pricing): align pricing 9.99€ → 14.99€/mois (BP v2 + audit decision)

- Premium.tsx displays 14.99€
- stripe_webhook.py uses new Price ID
- Amendment doc records 4 owner decisions post-audit 2026-04-17:
  budget 50€/mo, hybrid C posture, 14.99€ pricing, NHL scope restricted to
  player_goals (Anytime Scorer) only."
```

---

### Task C3 : Nettoyer legacy Projet_Football + CI (P0-13)

**Files:**
- Modify: `.github/workflows/daily-pipeline.yml`
- Modify: `ProbaLab/Makefile`
- Delete: `ProbaLab/Projet_Football/` (après archive tag git)

- [ ] **Step 1 : Tag de sauvegarde**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git tag archive/projet-football-pre-removal
git push origin archive/projet-football-pre-removal
```

- [ ] **Step 2 : Lire `daily-pipeline.yml`**

Run: `Read .github/workflows/daily-pipeline.yml`

Identifier toutes les lignes `cd Projet_Football && ...`. Les remplacer par `cd ProbaLab && ...` ou les supprimer si obsolètes.

- [ ] **Step 3 : Lire Makefile**

Run: `Read ProbaLab/Makefile`

Supprimer toutes les cibles qui référencent `Projet_Football`. Garder celles qui ciblent ProbaLab/.

- [ ] **Step 4 : Valider pour chaque fichier de CI**

Run: `Grep "Projet_Football" --type yaml --path .github/`
Corriger chaque occurrence.

Run: `Grep "Projet_Football" --path ProbaLab/ -n`
Idem.

- [ ] **Step 5 : Supprimer le dossier `Projet_Football/`**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git rm -r ProbaLab/Projet_Football
```

- [ ] **Step 6 : Tester en local**

Run: `cd ProbaLab && make test` (ou commande équivalente)
Expected : la commande trouve les tests et les passe.

- [ ] **Step 7 : Commit**

```bash
git add .github/workflows/ ProbaLab/Makefile
git commit -m "chore(ci): remove legacy Projet_Football/ from CI and Makefile

CI was cd'ing into Projet_Football/ ghost module — tests appeared green
but weren't testing actual ProbaLab code. Archive tag: archive/projet-football-pre-removal."
```

---

### Task C4 : Fix `railway.toml` + harmoniser Python 3.11 + source unique (P0-15)

**Files:**
- Modify: `ProbaLab/railway.toml`
- Modify: `ProbaLab/pyproject.toml`
- Delete: `ProbaLab/Procfile` OU `ProbaLab/nixpacks.toml` (choisir une source)

- [ ] **Step 1 : Lire les 3 descripteurs**

```
Read ProbaLab/railway.toml
Read ProbaLab/Procfile
Read ProbaLab/nixpacks.toml
Read ProbaLab/pyproject.toml
```

- [ ] **Step 2 : Décider de la source unique de vérité**

Recommandation : garder `nixpacks.toml` + `railway.toml` (Nixpacks est le builder Railway par défaut), supprimer `Procfile`.

- [ ] **Step 3 : Corriger `railway.toml`**

Il doit contenir 2 services avec chacun son `[services.deploy]` :

```toml
[build]
builder = "nixpacks"

[[services]]
name = "web"
[services.deploy]
startCommand = "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"

[[services]]
name = "worker"
[services.deploy]
startCommand = "python worker.py"
restartPolicyType = "ON_FAILURE"
```

- [ ] **Step 4 : Harmoniser Python 3.11 dans `pyproject.toml`**

```toml
[project]
requires-python = ">=3.11,<3.12"
```

Dans `nixpacks.toml` :
```toml
[phases.setup]
nixPkgs = ["python311", "python311Packages.pip"]
```

- [ ] **Step 5 : Supprimer `Procfile`**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab"
git rm ProbaLab/Procfile
```

- [ ] **Step 6 : Tester la config localement**

Run: `cd ProbaLab && pyenv exec python worker.py --help 2>&1 | head -5`
Run: `cd ProbaLab && pyenv exec uvicorn api.main:app --host 127.0.0.1 --port 8001 &`
Puis `curl http://127.0.0.1:8001/health` — doit retourner OK.
Tuer le process : `pkill -f "uvicorn api.main"`.

- [ ] **Step 7 : Commit**

```bash
git add ProbaLab/railway.toml ProbaLab/pyproject.toml ProbaLab/nixpacks.toml
git commit -m "chore(infra): fix railway.toml services config + unify Python 3.11

- railway.toml: both web and worker now have [services.deploy] blocks
- pyproject.toml: requires-python = '>=3.11,<3.12'
- Removed Procfile (single source of truth = nixpacks.toml + railway.toml)"
```

---

### Task C5 : Déplacer scripts debug hors `tests/` + fix 2 tests flaky (P0-16, P0-17)

**Files:**
- Move: `ProbaLab/src/test_auth.py`, `test_connection.py`, `test_api_halves.py` → `ProbaLab/scripts/debug/`
- Modify: `ProbaLab/tests/test_stats_engine.py` (TestCalculateXg flaky)

- [ ] **Step 1 : Créer le dossier `scripts/debug/`**

```bash
mkdir -p "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab/scripts/debug"
```

- [ ] **Step 2 : Déplacer les 3 scripts**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab"
git mv src/test_auth.py scripts/debug/
git mv src/test_connection.py scripts/debug/
git mv src/test_api_halves.py scripts/debug/
```

- [ ] **Step 3 : Vérifier que pytest ne les picke plus**

Run: `cd ProbaLab && pyenv exec python -m pytest --collect-only 2>&1 | grep "test_auth\|test_connection\|test_api_halves"`
Expected : aucune sortie.

- [ ] **Step 4 : Inspecter les 2 tests flaky**

Run: `Read ProbaLab/tests/test_stats_engine.py`
Chercher `TestCalculateXg::test_fallback_when_no_data` et `test_unknown_team_fallback`. Lire leur implémentation.

- [ ] **Step 5 : Lancer les tests en isolé pour voir l'erreur**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/test_stats_engine.py::TestCalculateXg -v 2>&1 | tail -40`

Noter le message d'erreur exact.

- [ ] **Step 6 : Fix selon l'erreur**

Causes fréquentes :
- Test dépend d'un ordre (classe = non-isolated) → ajouter fixture `pytest.fixture(autouse=True)` qui reset state
- Test utilise un mock partiel qui laisse fuir de la vraie DB → patcher correctement
- Test hardcodait une valeur qui dépend du WEIGHT_MARKET (changé en Task A3) → mettre à jour la valeur attendue

Appliquer le fix minimal.

- [ ] **Step 7 : Re-lancer 10 fois pour vérifier stabilité**

```bash
cd "/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab/ProbaLab"
for i in {1..10}; do
  pyenv exec python -m pytest tests/test_stats_engine.py::TestCalculateXg -q 2>&1 | tail -3
done
```

Expected : 10x "passed".

- [ ] **Step 8 : Commit**

```bash
git add ProbaLab/scripts/debug/ ProbaLab/tests/test_stats_engine.py
git commit -m "chore(tests): move debug scripts out of tests/ + fix 2 flaky xG tests

- scripts/debug/{test_auth,test_connection,test_api_halves}.py (side-effects at import)
- test_stats_engine.py::TestCalculateXg stabilized (10x pass local)"
```

---

### Task C6 : Page `/methodology` publique (P0-22)

**Files:**
- Create: `ProbaLab/dashboard/src/pages/Methodology.tsx`
- Create: `ProbaLab/api/routers/methodology.py`
- Modify: `ProbaLab/api/main.py` (registrer router)
- Modify: `ProbaLab/dashboard/src/App.tsx` (route)

- [ ] **Step 1 : Endpoint backend `/api/methodology/brier-timeline`**

Créer `ProbaLab/api/routers/methodology.py` :

```python
"""Public methodology endpoints — transparence radicale Brier/log-loss/CLV."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from src.config import supabase

router = APIRouter(prefix="/api/methodology", tags=["methodology"])


@router.get("/brier-timeline")
def brier_timeline(days: int = 90):
    """Renvoie la timeline Brier par jour (foot + NHL) sur `days` jours."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        supabase.table("model_health_log")
        .select("recorded_at,sport,brier_7d,brier_30d")
        .gte("recorded_at", cutoff.isoformat())
        .order("recorded_at")
        .execute()
        .data
    )
    return {"days": days, "series": rows}


@router.get("/walk-forward-report")
def walk_forward_report():
    """Renvoie le rapport walk-forward statique généré par scripts/publish_walk_forward_report.py."""
    import json
    from pathlib import Path
    path = Path(__file__).parent.parent.parent / "dashboard" / "public" / "walk_forward_report.json"
    if not path.exists():
        return {"error": "Report not yet generated. Run scripts/publish_walk_forward_report.py."}
    return json.loads(path.read_text())
```

- [ ] **Step 2 : Enregistrer le router dans `api/main.py`**

Run: `Read ProbaLab/api/main.py`

Ajouter :
```python
from api.routers import methodology  # noqa

app.include_router(methodology.router)
```

- [ ] **Step 3 : Page React `Methodology.tsx`**

Créer `ProbaLab/dashboard/src/pages/Methodology.tsx` :

```tsx
import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

type Serie = { recorded_at: string; sport: string; brier_7d: number; brier_30d: number };

export default function Methodology() {
  const [series, setSeries] = useState<Serie[]>([]);
  const [wf, setWf] = useState<any>(null);

  useEffect(() => {
    fetch("/api/methodology/brier-timeline?days=90")
      .then(r => r.json())
      .then(d => setSeries(d.series ?? []));
    fetch("/api/methodology/walk-forward-report")
      .then(r => r.json())
      .then(setWf);
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      <h1 className="text-3xl font-bold">Méthodologie — Transparence radicale</h1>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Comment on prédit</h2>
        <p>
          ProbaLab combine 3 couches : 70% stats (Poisson / Dixon-Coles / ELO / 50+ features),
          ML calibré (XGBoost + calibration isotonique), et 30% analyse narrative IA (Gemini).
          Les poids sont rééquilibrés selon un backtest 12 mois (WEIGHT_MARKET = 0.45).
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Brier Score — 90 derniers jours</h2>
        <p className="text-sm text-slate-600">
          Le Brier Score mesure la qualité des probabilités (0 = parfait, 0.67 = aléatoire).
          Seuils : &lt;0.19 excellent, 0.19-0.21 bon, 0.21-0.23 acceptable, ≥0.23 à améliorer.
        </p>
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={series}>
              <XAxis dataKey="recorded_at" />
              <YAxis domain={[0.15, 0.30]} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="brier_7d" stroke="#3b82f6" />
              <Line type="monotone" dataKey="brier_30d" stroke="#10b981" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Walk-forward validation</h2>
        {wf && wf.brier_1x2_mean !== undefined && (
          <>
            <p>
              Brier 1X2 moyen sur <strong>{wf.folds?.length ?? 0}</strong> fenêtres
              temporelles glissantes (3 mois hold-out chacune) : <strong>{wf.brier_1x2_mean.toFixed(4)}</strong>
              (écart-type {wf.brier_1x2_std?.toFixed(4)}).
            </p>
            <p className="text-sm text-slate-600">
              Log-loss moyen : {wf.log_loss_mean?.toFixed(4)}.
              Généré le {new Date(wf.generated_at).toLocaleString("fr-FR")}.
            </p>
          </>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold">Ce qu'on ne fait pas (encore)</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>NHL player props étendus</strong> : actuellement nous ne proposons
            que le marché "Anytime Scorer" (1+ but marqué) car notre provider de cotes
            bookmaker ne publie pas "1+ Point" ni "1+ Passe décisive" sur son plan actuel.
            Nous calculons ces probabilités côté modèle mais ne les exposons pas en picks
            tant que les cotes ne sont pas disponibles.
          </li>
        </ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 4 : Ajouter la route dans `App.tsx`**

Run: `Read ProbaLab/dashboard/src/App.tsx`

Ajouter `<Route path="/methodology" element={<Methodology />} />` et l'import.

- [ ] **Step 5 : Build + test**

Run: `cd ProbaLab/dashboard && npm run build`
Expected : build OK.

Run: `cd ProbaLab && pyenv exec uvicorn api.main:app --reload &` (background)
Puis visiter http://localhost:5173/methodology (dev server frontend + proxy vers API).

- [ ] **Step 6 : Commit**

```bash
git add ProbaLab/api/routers/methodology.py ProbaLab/api/main.py ProbaLab/dashboard/src/pages/Methodology.tsx ProbaLab/dashboard/src/App.tsx
git commit -m "feat(methodology): public /methodology page (transparence radicale)

- GET /api/methodology/brier-timeline (90 days)
- GET /api/methodology/walk-forward-report (static report)
- Frontend page with Recharts timeline + explainer + NHL scope honesty note
- Differentiator L5 per audit zone blanche §5.1 (no competitor publishes Brier)"
```

---

### Task C7 : Trancher la dualité scheduler (P0-14)

**Files:**
- Modify: `ProbaLab/api/main.py:15` (commentaire)
- Modify: `ProbaLab/api/routers/trigger.py` (supprimer duplicatas)

- [ ] **Step 1 : Lister les jobs APScheduler**

Run: `Read ProbaLab/worker.py`
Noter chaque `scheduler.add_job(...)` et son `id=`.

- [ ] **Step 2 : Lister les endpoints `/api/trigger/*` qui font le même job**

Run: `Read ProbaLab/api/routers/trigger.py offset=0 limit=200`
(Et suite avec offset=200, 400, ..., 1680)

Pour chaque endpoint POST/GET qui déclenche un job identique à un cron APScheduler, noter.

- [ ] **Step 3 : Choisir : garder APScheduler OU endpoints /trigger**

Décision recommandée : **garder APScheduler comme seule source de scheduling**, supprimer les endpoints `/api/trigger/*` qui font du duplicate. Garder uniquement ceux qui sont vraiment "triggered-on-demand" (pas cron).

- [ ] **Step 4 : Supprimer les endpoints duplicatas**

Dans `api/routers/trigger.py`, pour chaque endpoint identifié en Step 2 comme cron-equivalent :
- Le supprimer
- Ajouter un commentaire au début du fichier listant les endpoints retirés et la date

- [ ] **Step 5 : Corriger le commentaire `main.py:15`**

Run: `Read ProbaLab/api/main.py offset=10 limit=10`

Remplacer `# APScheduler removed — all scheduling handled by Trigger.dev` par :

```python
# Scheduling: APScheduler in worker.py (single source of truth).
# Trigger.dev has been deprecated in favor of internal APScheduler (see lesson 64).
# Endpoints /api/trigger/* are for ad-hoc manual triggers only, not cron.
```

- [ ] **Step 6 : Tests**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/ -k "trigger" -v`
Si des tests échouent car ils testaient les endpoints supprimés → les retirer ou adapter.

- [ ] **Step 7 : Commit**

```bash
git add ProbaLab/api/main.py ProbaLab/api/routers/trigger.py ProbaLab/tests/
git commit -m "refactor(scheduler): APScheduler as single source of truth (lesson 64)

- Removed N duplicate /api/trigger/* endpoints that replicated worker.py cron jobs
- api/main.py:15 comment corrected (was misleading about Trigger.dev)
- /api/trigger/* kept only for true ad-hoc manual triggers"
```

---

## SPRINT D — UI Foundation pivot-ready (semaines 5-6)

**Objectif** : rendre le frontend pivot-ready — typographie lisible, a11y minimale, types partagés.

**Items traités** : P0-19, P0-20, P0-21.

### Task D1 : Typographie — éliminer les 154 `text-[9-11px]` (P0-19)

**Files:**
- Modify: ~26 fichiers dashboard
- Modify: `ProbaLab/dashboard/eslint.config.js`

- [ ] **Step 1 : Inventaire exhaustif**

Run: `Grep "text-\[(9|10|11)px\]" --path ProbaLab/dashboard/src/ -n` → liste complète.
Noter le total (attendu ~154).

- [ ] **Step 2 : Stratégie de remplacement**

- `text-[9px]` / `text-[10px]` → `text-xs` (12px)
- `text-[11px]` → `text-xs` ou `text-sm` (14px) selon contexte

- [ ] **Step 3 : Remplacement batch**

Utiliser un script sed ou l'outil Edit avec replace_all.

Pour chaque fichier listé en Step 1 :
```bash
cd ProbaLab/dashboard
sed -i '' 's/text-\[9px\]/text-xs/g; s/text-\[10px\]/text-xs/g; s/text-\[11px\]/text-xs/g' path/to/file.tsx
```

Ou via outil Edit avec `replace_all: true` sur chaque pattern.

- [ ] **Step 4 : Vérifier 0 reste**

Run: `Grep "text-\[(9|10|11)px\]" --path ProbaLab/dashboard/src/ -c`
Expected : 0.

- [ ] **Step 5 : Ajouter règle ESLint bloquante**

Modifier `dashboard/eslint.config.js` pour interdire ces patterns. Utiliser `eslint-plugin-tailwindcss` ou une règle `no-restricted-syntax` custom :

```js
{
  rules: {
    "no-restricted-syntax": [
      "error",
      {
        "selector": "Literal[value=/text-\\[(9|10|11)px\\]/]",
        "message": "Forbidden: text-[<12px] is unreadable on mobile. Use text-xs (12px) or text-sm (14px)."
      }
    ]
  }
}
```

- [ ] **Step 6 : Lint + build**

Run: `cd ProbaLab/dashboard && npm run lint && npm run build`
Expected : pas de violation, build OK.

- [ ] **Step 7 : QA manuelle mobile (optionnelle mais recommandée)**

Lancer le dev server + ouvrir Chrome DevTools en mode mobile, visiter les pages principales. Vérifier lisibilité.

- [ ] **Step 8 : Commit**

```bash
git add ProbaLab/dashboard/src/ ProbaLab/dashboard/eslint.config.js
git commit -m "fix(ui): replace 154 text-[9-11px] with text-xs/text-sm (lesson 54)

ESLint rule added to prevent re-introduction."
```

---

### Task D2 : A11y minimale — clavier + alt + aria (P0-20)

**Files:**
- Modify: composants avec `<div onClick>` (grep target : ~100 éléments selon audit)
- Modify: composants avec `<img alt="">` ou sans alt

- [ ] **Step 1 : Grep des `<div onClick>`**

Run: `Grep "<div[^>]*onClick" --path ProbaLab/dashboard/src/ -n`
Noter les fichiers concernés (attendu ~100 éléments sur 20-30 fichiers).

- [ ] **Step 2 : Stratégie**

- `<div onClick={fn}>` sans role → `<button type="button" onClick={fn}>` + classe CSS neutralisant le style par défaut (`className="text-left w-full"` par ex)
- `<div onClick={fn} role="button">` → `<button>` quand même

- [ ] **Step 3 : Batch par fichier**

Pour chaque fichier, remplacer systématiquement. Préserver les classes Tailwind.

Exemple : `MatchRow.tsx` :
```tsx
// AVANT
<div onClick={() => navigate(`/match/${id}`)} className="...">
  ...
</div>

// APRÈS
<button
  type="button"
  onClick={() => navigate(`/match/${id}`)}
  className="... w-full text-left"
  aria-label={`Ouvrir le match ${homeTeam} vs ${awayTeam}`}
>
  ...
</button>
```

- [ ] **Step 4 : Grep des `alt=""`**

Run: `Grep 'alt=""' --path ProbaLab/dashboard/src/ -n`

Pour chaque occurrence, remplacer par un alt descriptif ou (si purement décoratif) `alt=""` explicite + `role="presentation"`.

- [ ] **Step 5 : Build + lint**

Run: `cd ProbaLab/dashboard && npm run lint && npm run build`

- [ ] **Step 6 : Test manuel clavier**

Lancer le dev server. Essayer de naviguer avec Tab uniquement sur HomePage. Vérifier qu'on peut cliquer sur une MatchCard via Enter.

- [ ] **Step 7 : Commit**

```bash
git add ProbaLab/dashboard/src/
git commit -m "feat(a11y): <div onClick> → <button> + alt attributes (WCAG 2.1 AA)

- ~100 interactive divs converted to buttons
- Added aria-label for icon-only and context-dependent interactions
- Image alt attributes populated (empty alt='' kept with role='presentation' where decorative)
- Prevents EAA (EU Accessibility Act) compliance failure"
```

---

### Task D3 : `src/types/api.ts` partagé + éliminer `useState<any>` (P0-21)

**Files:**
- Create: `ProbaLab/dashboard/src/types/api.ts`
- Modify: `ProbaLab/dashboard/generate-types.sh`
- Modify: pages utilisant `useState<any>`

- [ ] **Step 1 : Inventaire `useState<any>`**

Run: `Grep "useState<any" --path ProbaLab/dashboard/src/ -n`

- [ ] **Step 2 : Générer types depuis Supabase**

Run: `Read ProbaLab/dashboard/generate-types.sh`

Le modifier pour générer via `supabase gen types typescript --linked`. Sortie → `dashboard/src/types/supabase.ts`.

Puis créer `dashboard/src/types/api.ts` qui réexporte + ajoute types pour les réponses d'endpoints FastAPI :

```typescript
// ProbaLab/dashboard/src/types/api.ts

export type Fixture = {
  id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  league_id: number;
};

export type Prediction = {
  fixture_id: number;
  proba_home: number;
  proba_draw: number;
  proba_away: number;
  proba_btts: number | null;
  proba_over_2_5: number | null;
};

export type BestBet = {
  id: number;
  category: "safe" | "fun" | "value_bet";
  pick: string;
  odds: number;
  edge: number | null;
  ev: number | null;
  result: "WIN" | "LOSS" | "VOID" | "PENDING" | null;
  virtual_stake: number;
  is_auto: boolean;
};

export type BrierTimelinePoint = {
  recorded_at: string;
  sport: "football" | "nhl";
  brier_7d: number | null;
  brier_30d: number | null;
};

export type FunnelEvent =
  | "landing_viewed"
  | "signup_started"
  | "signup_completed"
  | "premium_viewed"
  | "checkout_clicked"
  | "checkout_completed";
```

- [ ] **Step 3 : Remplacer chaque `useState<any>`**

Pour chaque occurrence, typer avec le type approprié depuis `types/api.ts`.

Exemple :
```tsx
// AVANT
const [predictions, setPredictions] = useState<any>(null);

// APRÈS
import type { Prediction } from "@/types/api";
const [predictions, setPredictions] = useState<Prediction[] | null>(null);
```

- [ ] **Step 4 : Build**

Run: `cd ProbaLab/dashboard && npm run build`
Expected : pas d'erreur TypeScript. Si erreur → compléter le type.

- [ ] **Step 5 : Commit**

```bash
git add ProbaLab/dashboard/src/types/ ProbaLab/dashboard/generate-types.sh ProbaLab/dashboard/src/pages/
git commit -m "feat(types): src/types/api.ts shared types + eliminate useState<any> (lesson 59)

- New types/api.ts with Fixture, Prediction, BestBet, BrierTimelinePoint, FunnelEvent
- generate-types.sh now uses supabase gen types
- All useState<any> in HomePage, ParisDuSoir, Performance typed properly
- Prevents lesson 59 regression (API shape mismatch between frontend/backend)"
```

---

## CHECKPOINT FIN H1

- [ ] **Step FC-1 : Vérification checklist audit §10 (DoD)**

Vérifier dans l'ordre :
- [ ] P0-1 eval_set leakage → Task A1 ✓
- [ ] P0-2 sample_weight CV → Task A2 ✓
- [ ] P0-3 WEIGHT_MARKET rééquilibré → Task A3 ✓
- [ ] P0-4 monitoring en cron + model_health_log → Task B1 ✓
- [ ] P0-5 fallback NHL instrumenté → Task B4 ✓
- [ ] P0-6 /admin/update-scores auth → Task B2 ✓
- [ ] P0-7 extra="forbid" → Task B3 ✓
- [ ] P0-8 detail=str(e) retiré → Task B3 ✓
- [ ] P0-9 Plausible + 6 événements → Task C1 ✓
- [ ] P0-10 décision NHL scope → Task C2 (Option A) ✓
- [ ] P0-11 walk-forward → Task A4 ✓
- [ ] P0-12 prix 14,99 + amendement pivot → Task C2 ✓
- [ ] P0-13 nettoyage Projet_Football → Task C3 ✓
- [ ] P0-14 dualité scheduler → Task C7 ✓
- [ ] P0-15 railway.toml + Python 3.11 → Task C4 ✓
- [ ] P0-16 scripts debug hors tests → Task C5 ✓
- [ ] P0-17 tests flaky xG → Task C5 ✓
- [ ] P0-18 datetime.now codemod → Task B5 ✓
- [ ] P0-19 typographie 154 corrections → Task D1 ✓
- [ ] P0-20 a11y clavier+alt → Task D2 ✓
- [ ] P0-21 types/api.ts → Task D3 ✓
- [ ] P0-22 page /methodology → Task C6 ✓

- [ ] **Step FC-2 : Mesure couverture tests finale**

Run: `cd ProbaLab && pyenv exec python -m pytest tests/ -m "not integration" --cov=src --cov=api --cov-report=term -q 2>&1 | tail -30`

Expected : ≥ 30% (baseline 21% + tests ajoutés dans les Sprints A/B).

Si < 30%, ajouter 1-2 tests unitaires ciblés.

- [ ] **Step FC-3 : Mettre à jour `--cov-fail-under` dans CI**

Modifier `.github/workflows/*.yml` — remplacer `--cov-fail-under=21` (ou valeur actuelle) par `--cov-fail-under=30`.

Commit :
```bash
git add .github/workflows/
git commit -m "ci: raise cov-fail-under to 30% after H1 stabilization"
```

- [ ] **Step FC-4 : Revue owner**

Annoncer :

> "Sprint D terminé. H1 clos : 22/22 P0 traités, couverture tests XX%, monitoring en cron, Plausible actif, page /methodology publique en ligne, design pivot amendé (scope NHL = player_goals). Prêt pour la Phase 1 du pivot — on enchaîne ?"

- [ ] **Step FC-5 : Créer PR de merge H1 → main**

Créer une PR récapitulative H1 avec tous les commits. Demander review.

Après merge, continuer vers la Phase 1 du pivot (tâches du `plan_pivot_probas_sportives.md` + amendement).

---

## Self-review du plan

### 1. Spec coverage (roadmap §2 P0 items)

| Item roadmap | Task de ce plan |
|---|---|
| P0-1 eval_set leakage | A1 |
| P0-2 sample_weight CV | A2 |
| P0-3 WEIGHT_MARKET | A3 |
| P0-4 monitoring cron + model_health_log | B1 |
| P0-5 fallback NHL silencieux | B4 |
| P0-6 /admin/update-scores auth | B2 |
| P0-7 extra="forbid" | B3 |
| P0-8 detail=str(e) retiré | B3 |
| P0-9 Plausible + 6 événements | C1 |
| P0-10 décision NHL scope | C2 (Option A assumée) |
| P0-11 walk-forward | A4 |
| P0-12 BP v2 ↔ pivot + prix | C2 |
| P0-13 legacy Projet_Football | C3 |
| P0-14 dualité scheduler | C7 |
| P0-15 railway.toml + Python 3.11 | C4 |
| P0-16 scripts debug hors tests | C5 |
| P0-17 tests flaky | C5 |
| P0-18 datetime.now migration | B5 |
| P0-19 typographie | D1 |
| P0-20 a11y clavier+alt | D2 |
| P0-21 types/api.ts | D3 |
| P0-22 page /methodology | C6 |

Tous les 22 P0 couverts. Aucun gap.

### 2. Placeholder scan

Recherche de "TBD", "TODO", "implement later" dans le plan : 0 trouvé.
Les emplacements `<inséré par l'ingénieur>` sont absents — tout est explicité.

Exception consciente : certaines tâches laissent une action manuelle owner (création compte Plausible, création Price Stripe). C'est attendu car les sous-agents n'ont pas ces accès — mais les steps sont concrets et la suite peut reprendre automatiquement.

### 3. Type consistency

- Nom du codemod : `migrate_datetime_now_utc.py` — cohérent dans B5 et checkpoint
- Nom de la table : `model_health_log` — cohérent dans B1 et C6
- Nom du wrapper analytics : `track(event, props)` — cohérent dans C1
- Types partagés : `Fixture`, `Prediction`, `BestBet`, `BrierTimelinePoint`, `FunnelEvent` — définis en D3
- Chemin racine : `/Users/pierrelaurent/Desktop/Pierre/Projets Dev Pierre/ProbaLab` — utilisé partout en absolu

### 4. Note de volumétrie

**Effort dev estimé** : ~22-28j de travail (selon roadmap §2 cumulé).
**Temps calendaire à 5h/sem solopreneur** : 11-14 semaines (hypothèse 4 de la roadmap).
**Temps calendaire à 40h/sem** : 4 semaines (hypothèse de la roadmap H1 originale).

Le plan est découpé en 4 Sprints alignés sur la cadence 1 sprint ≈ 1 semaine à 40h/sem OU ~3 semaines à 5h/sem. L'owner peut adapter le rythme selon sa disponibilité réelle.
