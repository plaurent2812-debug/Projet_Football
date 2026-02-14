# PLAN D'ACTION — PROJET FOOTBALL IA → 10/10

## Situation actuelle

| Critère                              | Note | Cible |
|--------------------------------------|------|-------|
| Utilité / pertinence du produit      | 8/10 | 10/10 |
| Qualité du code                      | 6/10 | 10/10 |
| Sophistication algorithmique         | 7.5/10 | 10/10 |
| UI / expérience utilisateur          | 7/10 | 10/10 |
| Maintenabilité                       | 5/10 | 10/10 |
| Pratiques d'ingénierie (tests, CI)   | 3/10 | 10/10 |

---

## PHASE 1 — FONDATIONS (Pratiques d'ingénierie : 3 → 8) ✅ TERMINÉE
> Priorité : CRITIQUE — Sans ça, tout le reste est fragile
> Durée estimée : 1-2 jours

### 1.1 Initialiser Git + .gitignore
```
git init
```
Créer `.gitignore` :
```
__pycache__/
*.pyc
.env
.DS_Store
*.pkl
*.model
venv/
.venv/
node_modules/
.clasp.json
```

### 1.2 Créer requirements.txt
```
supabase>=2.0.0
python-dotenv>=1.0.0
requests>=2.31.0
anthropic>=0.40.0
numpy>=1.24.0
scipy>=1.11.0
scikit-learn>=1.3.0
xgboost>=2.0.0
pytest>=7.4.0
pytest-cov>=4.1.0
```

### 1.3 Structurer le projet en package Python
Transformer la structure plate en package modulaire :
```
Projet_Football/
├── .gitignore
├── .env.example              ← NOUVEAU (template sans secrets)
├── requirements.txt          ← NOUVEAU
├── README.md                 ← NOUVEAU (setup, usage, architecture)
├── pytest.ini                ← NOUVEAU
├── run_pipeline.py           ← Point d'entrée (inchangé)
├── Lancer Analyses.command
│
├── src/                      ← NOUVEAU (package Python)
│   ├── __init__.py
│   ├── config.py             ← (déplacé)
│   │
│   ├── fetchers/             ← NOUVEAU (module data)
│   │   ├── __init__.py
│   │   ├── matches.py        ← (ex fetch_matches.py)
│   │   ├── teams.py          ← (ex fetch_teams.py)
│   │   ├── players.py        ← (ex fetch_players.py)
│   │   ├── context.py        ← (ex fetch_context.py)
│   │   └── history.py        ← (ex fetch_history.py)
│   │
│   ├── models/               ← NOUVEAU (module analyse)
│   │   ├── __init__.py
│   │   ├── stats_engine.py   ← (déplacé)
│   │   ├── scorer_engine.py  ← (déplacé)
│   │   ├── ml_predictor.py   ← (déplacé)
│   │   └── calibrate.py      ← (déplacé)
│   │
│   ├── training/             ← NOUVEAU (module ML)
│   │   ├── __init__.py
│   │   ├── fetch_history.py  ← (ex fetch_training_history.py)
│   │   ├── build_data.py     ← (ex build_training_data.py)
│   │   ├── train.py          ← (ex train_model.py)
│   │   └── evaluate.py       ← (déplacé)
│   │
│   └── brain.py              ← (déplacé)
│
├── tests/                    ← NOUVEAU
│   ├── __init__.py
│   ├── conftest.py           ← Fixtures pytest partagées
│   ├── test_stats_engine.py
│   ├── test_scorer_engine.py
│   ├── test_ml_predictor.py
│   ├── test_brain.py
│   ├── test_calibrate.py
│   └── test_evaluate.py
│
├── migrations/               ← (inchangé)
│   ├── 001_stats_tables.sql
│   ├── 002_value_columns.sql
│   ├── 003_performance_tracking.sql
│   └── 004_ml_training.sql
│
└── google_apps_script/       ← (inchangé, mais découpé — voir Phase 4)
    ├── Code.js
    ├── .clasp.json
    └── appsscript.json
```

### 1.4 Ajouter le logging structuré
Remplacer TOUS les `print()` par un logger configurable.

Fichier `src/config.py` — ajouter :
```python
import logging

def setup_logger(name="football_ia", level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

logger = setup_logger()
```

Puis dans chaque fichier : `from src.config import logger` et remplacer
`print("message")` → `logger.info("message")`

### 1.5 Créer .env.example
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
API_FOOTBALL_KEY=your_key_here
ANTHROPIC_API_KEY=sk-ant-...
```

---

## PHASE 2 — QUALITÉ DU CODE (6 → 9) ✅ TERMINÉE
> Durée estimée : 2-3 jours

### 2.1 Ajouter les type hints partout
Exemple — `stats_engine.py` avant :
```python
def poisson_grid(xg_home, xg_away, max_goals=7):
```
Après :
```python
def poisson_grid(
    xg_home: float,
    xg_away: float,
    max_goals: int = 7
) -> dict[str, int | float | str]:
```

Faire ça pour TOUS les fichiers Python (17 fichiers).

### 2.2 Extraire les constantes magiques
Créer `src/constants.py` :
```python
"""Constantes globales du projet."""

# Poisson
MAX_GOALS_GRID = 7

# ELO
K_FACTOR = 32
HOME_ELO_ADVANTAGE = 65
DEFAULT_ELO = 1500

# Forme
FORM_DECAY = 0.82
FORM_LOOKBACK = 6

# Repos
REST_FATIGUE_THRESHOLD = 3      # jours
REST_SLIGHT_THRESHOLD = 5       # jours
REST_OPTIMAL_THRESHOLD = 7      # jours
CONGESTION_HIGH = 8             # matchs/30j
CONGESTION_MEDIUM = 6

# Enjeu
STAKES_TITLE_FACTOR = 1.08
STAKES_CL_FACTOR = 1.05
STAKES_RELEGATION_FACTOR = 1.06
STAKES_MIDTABLE_FACTOR = 0.97

# Home advantage
HOME_BONUS = 1.12

# Penalty
BASE_PENALTY_RATE = 0.30
AVG_DEFENDER_FOULS_PER_90 = 1.2
AVG_ATTACKER_FOULS_DRAWN_PER_90 = 1.5

# Combinaison
WEIGHT_POISSON = 0.55
WEIGHT_ELO = 0.25
WEIGHT_MARKET = 0.20
WEIGHT_STATS = 0.70
WEIGHT_AI = 0.30
WEIGHT_ML = 0.40
WEIGHT_STATS_VS_ML = 0.60

# Calibration
MIN_CALIBRATION_SAMPLES = 20
```

### 2.3 Dédupliquer FEATURE_COLS
Le tableau est défini identiquement dans `train_model.py` et `ml_predictor.py`.
→ Le déplacer dans `src/constants.py` et l'importer des deux côtés.

### 2.4 Remplacer les bare except
Trouver et corriger tous les `except Exception` trop larges :
```python
# AVANT (mauvais)
except Exception:
    pass

# APRÈS (bon)
except (ValueError, KeyError) as e:
    logger.warning(f"Erreur calcul penalty: {e}")
```

### 2.5 Ajouter des docstrings Google-style
Standardiser la documentation de toutes les fonctions :
```python
def calculate_xg(
    home_team_id: int,
    away_team_id: int,
    league_data: dict | None,
    adjustments: dict | None = None,
) -> tuple[float, float]:
    """Calcule les expected goals pour un match.

    Args:
        home_team_id: ID API de l'équipe à domicile.
        away_team_id: ID API de l'équipe à l'extérieur.
        league_data: Données de force de la ligue (ou None pour fallback).
        adjustments: Facteurs d'ajustement optionnels (forme, repos, etc.).

    Returns:
        Tuple (xg_home, xg_away) bornés entre 0.3 et 4.0.

    Example:
        >>> xg_h, xg_a = calculate_xg(85, 33, league_data)
        >>> print(f"xG: {xg_h:.2f} - {xg_a:.2f}")
    """
```

### 2.6 Utiliser des dataclasses / Pydantic
Remplacer les dicts anonymes par des structures typées :
```python
from dataclasses import dataclass

@dataclass
class MatchPrediction:
    proba_home: int
    proba_draw: int
    proba_away: int
    proba_btts: int
    proba_over_25: int
    xg_home: float
    xg_away: float
    correct_score: str
    confidence_score: int
    recommended_bet: str
    analysis_text: str
    model_version: str

@dataclass
class PlayerInjuryImpact:
    player_name: str
    position: str
    reason: str
    impact: str  # "CRITIQUE", "majeur", "significatif", "modéré", "mineur", "minimal"
    impact_attack: float
    impact_defense: float
    goals: int = 0
    assists: int = 0
    rating: float = 6.0
    minutes: int = 0
    is_starter: bool = False

@dataclass
class ScorerPrediction:
    player_id: int
    name: str
    team: str
    position: str
    proba: int
    player_xg: float
    goals_per_90: float
    total_goals: int
    analysis: str
```

---

## PHASE 3 — TESTS (Pratiques d'ingénierie : 8 → 10) ✅ TERMINÉE
> Durée estimée : 2-3 jours

### 3.1 Tests unitaires — stats_engine.py
```python
# tests/test_stats_engine.py
import pytest
import numpy as np
from src.models.stats_engine import (
    poisson_grid, elo_expected, elo_update, get_elo_probs,
    regress_to_mean, get_weather_impact, calculate_xg
)

class TestPoissonGrid:
    def test_probabilities_sum_to_100(self):
        result = poisson_grid(1.5, 1.2)
        total = result["proba_home"] + result["proba_draw"] + result["proba_away"]
        assert 98 <= total <= 102  # Tolérance arrondi

    def test_high_xg_home_favors_home(self):
        result = poisson_grid(3.0, 0.5)
        assert result["proba_home"] > result["proba_away"]
        assert result["proba_home"] > 60

    def test_equal_xg_balanced(self):
        result = poisson_grid(1.3, 1.3)
        assert abs(result["proba_home"] - result["proba_away"]) < 5

    def test_over_25_increases_with_xg(self):
        low = poisson_grid(0.8, 0.7)
        high = poisson_grid(2.0, 1.8)
        assert high["proba_over_25"] > low["proba_over_25"]

    def test_btts_increases_with_both_xg_high(self):
        low = poisson_grid(0.5, 0.5)
        high = poisson_grid(2.0, 2.0)
        assert high["proba_btts"] > low["proba_btts"]

    def test_correct_score_is_valid(self):
        result = poisson_grid(1.5, 1.0)
        h, a = result["correct_score"].split("-")
        assert int(h) >= 0 and int(a) >= 0

class TestElo:
    def test_expected_equal_elos(self):
        assert abs(elo_expected(1500, 1500) - 0.5) < 0.01

    def test_higher_elo_wins(self):
        assert elo_expected(1700, 1500) > 0.5
        assert elo_expected(1500, 1700) < 0.5

    def test_elo_update_win(self):
        new_elo = elo_update(1500, 0.5, 1.0)
        assert new_elo > 1500

    def test_elo_update_loss(self):
        new_elo = elo_update(1500, 0.5, 0.0)
        assert new_elo < 1500

    def test_elo_probs_sum_to_100(self):
        result = get_elo_probs(1500, 1500)
        total = result["elo_home"] + result["elo_draw"] + result["elo_away"]
        assert 98 <= total <= 102

class TestRegressionToMean:
    def test_small_sample_pulls_to_mean(self):
        result = regress_to_mean(2.0, 3, 1.25)
        assert result < 2.0
        assert result > 1.25

    def test_large_sample_stays_near_observed(self):
        result = regress_to_mean(2.0, 100, 1.25)
        assert abs(result - 2.0) < 0.1

class TestWeatherImpact:
    def test_no_weather_returns_1(self):
        assert get_weather_impact(None) == 1.0

    def test_heavy_rain_reduces(self):
        factor = get_weather_impact({"rain_mm": 10, "wind_speed": 0, "temp": 15})
        assert factor < 1.0

    def test_normal_weather_no_change(self):
        factor = get_weather_impact({"rain_mm": 0, "wind_speed": 3, "temp": 18})
        assert factor == 1.0
```

### 3.2 Tests unitaires — scorer_engine.py
```python
# tests/test_scorer_engine.py
import pytest
from src.models.scorer_engine import get_anomaly_boost

class TestAnomalyBoost:
    def test_low_shots_no_boost(self):
        rate = {"total_shots_on": 5, "shots_on_per_90": 0.5, "conversion_rate": 0.10}
        form = {"matches_played": 3, "goals": 0}
        assert get_anomaly_boost(rate, form) == 1.0

    def test_high_shots_low_conversion_boost(self):
        rate = {"total_shots_on": 30, "shots_on_per_90": 1.5, "conversion_rate": 0.10}
        form = {"matches_played": 5, "goals": 1}
        assert get_anomaly_boost(rate, form) > 1.0

    def test_no_rate_returns_1(self):
        assert get_anomaly_boost(None, {"matches_played": 0, "goals": 0}) == 1.0
```

### 3.3 Tests d'intégration — brain.py
```python
# tests/test_brain.py
import pytest
from src.brain import extract_json, blend_predictions

class TestExtractJson:
    def test_pure_json(self):
        text = '{"proba_home": 55, "proba_draw": 25, "proba_away": 20}'
        result = extract_json(text)
        assert result["proba_home"] == 55

    def test_json_in_markdown(self):
        text = '```json\n{"proba_home": 55}\n```'
        result = extract_json(text)
        assert result["proba_home"] == 55

    def test_json_with_surrounding_text(self):
        text = 'Voici mon analyse: {"proba_home": 55} fin'
        result = extract_json(text)
        assert result["proba_home"] == 55

    def test_invalid_returns_none(self):
        assert extract_json("pas du json") is None

class TestBlendPredictions:
    def test_normalizes_to_100(self):
        stats = {"proba_home": 50, "proba_draw": 30, "proba_away": 20,
                 "proba_btts": 55, "proba_over_25": 60}
        ai = {"proba_home": 60, "proba_draw": 20, "proba_away": 20,
              "proba_btts": 50, "proba_over_2_5": 55}
        result = blend_predictions(stats, ai)
        total = result["proba_home"] + result["proba_draw"] + result["proba_away"]
        assert total == 100

    def test_without_ai_uses_stats(self):
        stats = {"proba_home": 60, "proba_draw": 25, "proba_away": 15,
                 "proba_btts": 50, "proba_over_25": 45,
                 "xg_home": 1.5, "xg_away": 0.9,
                 "recommended_bet": "Victoire Domicile",
                 "confidence_score": 7}
        result = blend_predictions(stats, None)
        assert result["proba_home"] == 60
```

### 3.4 Tests ML — calibrate.py
```python
# tests/test_calibrate.py
import numpy as np
from src.models.calibrate import fit_platt_scaling, compute_bias

class TestPlattScaling:
    def test_insufficient_samples(self):
        X = np.array([[0.5], [0.6]])
        y = np.array([1, 0])
        a, b, _, _ = fit_platt_scaling(X, y)
        assert a == 1.0 and b == 0.0  # Pas assez de données

    def test_calibration_improves_brier(self):
        np.random.seed(42)
        X = np.random.uniform(0.2, 0.8, size=(100, 1))
        y = (X.ravel() + np.random.normal(0, 0.15, 100) > 0.5).astype(float)
        _, _, brier_before, brier_after = fit_platt_scaling(X, y)
        if brier_after is not None:
            assert brier_after <= brier_before + 0.01

class TestBias:
    def test_overestimation(self):
        X = np.array([[0.8], [0.7], [0.9]])
        y = np.array([0, 0, 1])
        bias = compute_bias(X, y)
        assert bias > 0  # On surestime

    def test_no_bias(self):
        X = np.array([[0.5]])
        y = np.array([0.5])
        assert compute_bias(X, y) == 0.0
```

### 3.5 Créer conftest.py avec fixtures partagées
```python
# tests/conftest.py
import pytest

@pytest.fixture
def sample_fixture():
    return {
        "id": 1,
        "api_fixture_id": 12345,
        "home_team": "Paris Saint Germain",
        "away_team": "Olympique De Marseille",
        "league_id": 61,
        "date": "2026-02-15T21:00:00+00:00",
        "status": "NS",
        "referee_name": "François Letexier",
        "weather_json": {"temp": 8, "wind_speed": 12, "rain_mm": 0},
    }

@pytest.fixture
def sample_prediction():
    return {
        "proba_home": 55, "proba_draw": 25, "proba_away": 20,
        "proba_btts": 52, "proba_over_25": 58,
        "proba_over_05": 95, "proba_over_15": 78, "proba_over_35": 30,
        "xg_home": 1.65, "xg_away": 1.10,
        "correct_score": "2-1", "proba_correct_score": 11,
        "recommended_bet": "Victoire Domicile",
        "confidence_score": 7,
        "model_version": "hybrid_v3_ml",
    }

@pytest.fixture
def sample_league_data():
    return {
        "strengths": {
            85: {"home_attack": 1.4, "home_defense": 0.7,
                 "away_attack": 1.2, "away_defense": 0.8},
            33: {"home_attack": 0.9, "home_defense": 1.3,
                 "away_attack": 0.8, "away_defense": 1.1},
        },
        "league_avg_home": 1.45,
        "league_avg_away": 1.10,
    }
```

### 3.6 Configurer pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short --cov=src --cov-report=term-missing
```

### 3.7 Objectif couverture
- Phase 1 : > 60% (fonctions pures mathématiques)
- Phase 2 : > 80% (avec mocks Supabase)
- Phase 3 : > 90% (intégration)

---

## PHASE 4 — MAINTENABILITÉ (5 → 10) ✅ TERMINÉE
> Durée estimée : 2-3 jours

### 4.1 Découper Code.js en modules
Le fichier monolithique de 2141 lignes doit être découpé :
```
google_apps_script/
├── Code.js           ← Menu + orchestration (200 lignes)
├── Config.js         ← Helpers config, dialog HTML (150 lignes)
├── Supabase.js       ← Helpers REST Supabase (100 lignes)
├── ApiFootball.js    ← Helpers API-Football (50 lignes)
├── Anthropic.js      ← Appel Claude + extraction JSON (200 lignes)
├── Import.js         ← importMatches() (100 lignes)
├── Analysis.js       ← runAnalysis(), forceReanalysis (300 lignes)
├── Display.js        ← refreshDisplay() + helpers couleurs (400 lignes)
├── Performance.js    ← refreshPerformance() + évaluation inline (400 lignes)
├── Pronos.js         ← refreshPronos() + tickets combinés (500 lignes)
└── Helpers.js        ← Fonctions utilitaires partagées (100 lignes)
```

### 4.2 Créer un Makefile / script de commandes
```makefile
.PHONY: install test lint run-data run-analyze run-full train

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=src

lint:
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

run-data:
	python run_pipeline.py data

run-analyze:
	python run_pipeline.py analyze

run-full:
	python run_pipeline.py full

train:
	python -m src.training.fetch_history
	python -m src.training.build_data
	python -m src.training.train
```

### 4.3 Ajouter ruff (linter + formatter)
Créer `ruff.toml` :
```toml
target-version = "py310"
line-length = 100

[lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "C4"]
ignore = ["E501"]  # line too long (géré par formatter)

[format]
quote-style = "double"
indent-style = "space"
```

### 4.4 Ajouter mypy (type checking)
Créer `mypy.ini` :
```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
check_untyped_defs = True
```

### 4.5 Documenter l'architecture (README.md)
```markdown
# Football IA — Système de Prédiction

## Architecture
[Diagramme pipeline : API-Football → Supabase → Stats + ML + Claude → Google Sheets]

## Setup
1. `cp .env.example .env` et remplir les clés
2. `pip install -r requirements.txt`
3. `python run_pipeline.py full`

## Structure du projet
[Arbre des dossiers expliqué]

## Modèle statistique
[Explication des 12 facteurs avec formules]

## Pipeline ML
[Description du workflow d'entraînement]

## API Reference
[Liste des fonctions principales avec signatures]
```

---

## PHASE 5 — SOPHISTICATION ALGORITHMIQUE (7.5 → 10) ✅ TERMINÉE
> Durée estimée : 3-5 jours | **Réalisé : ~30 min avec Cursor**

### 5.1 Ajouter un modèle Dixon-Coles
Le Poisson indépendant surestime les 0-0 et 1-1.
Dixon-Coles corrige ça avec un paramètre de corrélation ρ :

```python
def dixon_coles_correction(h: int, a: int, lambda_h: float,
                           lambda_a: float, rho: float) -> float:
    """Correction Dixon-Coles pour les faibles scores."""
    if h == 0 and a == 0:
        return 1 - lambda_h * lambda_a * rho
    elif h == 0 and a == 1:
        return 1 + lambda_h * rho
    elif h == 1 and a == 0:
        return 1 + lambda_a * rho
    elif h == 1 and a == 1:
        return 1 - rho
    return 1.0
```

### 5.2 Implémenter un ELO temporel (decay)
L'ELO actuel ne décroit pas avec le temps. Ajouter un decay :
```python
def elo_with_decay(elo: float, days_since_last: int,
                   decay_rate: float = 0.001) -> float:
    """Tire le ELO vers 1500 si l'équipe n'a pas joué récemment."""
    regression = (elo - 1500) * math.exp(-decay_rate * days_since_last)
    return 1500 + regression
```

### 5.3 Feature engineering avancé pour XGBoost
Ajouter dans `build_training_data.py` :
```python
# Momentum (tendance des 3 vs 6 derniers matchs)
features["home_momentum"] = form_3_last - form_6_last
features["away_momentum"] = ...

# Fatigue cumulative (pondérée par importance des matchs)
features["home_fatigue_index"] = ...

# Goal difference running average
features["home_goal_diff_avg"] = ...

# Variance des résultats (équipe imprévisible)
features["home_result_variance"] = ...

# Distance parcourue (proxy via matchs extérieurs récents)
features["away_travel_burden"] = ...

# Clean sheet ratio
features["home_clean_sheet_rate"] = ...
features["away_clean_sheet_rate"] = ...
```

### 5.4 Ensemble de modèles
Remplacer le XGBoost unique par un ensemble :
```python
from sklearn.ensemble import VotingClassifier, StackingClassifier
import lightgbm as lgb

# Stacking : XGBoost + LightGBM + Random Forest
# Méta-learner : LogisticRegression
estimators = [
    ("xgb", xgb.XGBClassifier(**xgb_params)),
    ("lgbm", lgb.LGBMClassifier(**lgbm_params)),
    ("rf", RandomForestClassifier(n_estimators=200)),
]
stacking = StackingClassifier(
    estimators=estimators,
    final_estimator=LogisticRegression(),
    cv=5
)
```

### 5.5 Backtesting temporel (Time Series Split)
Remplacer le train_test_split aléatoire par un split temporel :
```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
```

### 5.6 Ajouter la prédiction de mi-temps
Nouveau marché : score à la mi-temps (HT result).
Facteurs : stats 1ère mi-temps historiques de chaque équipe, tendance
"marqueur précoce" vs "finisseur tardif".

### 5.7 Ajouter le calcul du ROI (Return on Investment)
```python
def calculate_roi(prediction_prob: float, bookmaker_odds: float) -> float:
    """Calcule le ROI espéré d'un pari.

    ROI = (prob * odds) - 1
    > 0 = value bet, < 0 = mauvais pari
    """
    return (prediction_prob / 100) * bookmaker_odds - 1

def kelly_criterion(prob: float, odds: float, bankroll: float,
                    fraction: float = 0.25) -> float:
    """Calcule la mise optimale selon le critère de Kelly.

    Args:
        fraction: Kelly fractionnaire (0.25 = quart-Kelly, plus conservateur)
    """
    edge = (prob / 100) * odds - 1
    if edge <= 0:
        return 0
    kelly = edge / (odds - 1)
    return bankroll * kelly * fraction
```

---

## PHASE 6 — UI / EXPÉRIENCE UTILISATEUR (7 → 10) ✅ TERMINÉE
> Durée estimée : 2-3 jours | **Réalisé : ~20 min avec Cursor**

### 6.1 Dashboard web (remplacer / compléter Google Sheets)
Créer une web app légère avec **Streamlit** ou **FastAPI + HTMX** :
```python
# dashboard/app.py
import streamlit as st
from src.config import supabase

st.set_page_config(page_title="Football IA", layout="wide")

# Sidebar : filtres
leagues = st.sidebar.multiselect("Ligues", [...])
date_range = st.sidebar.date_input("Période", [...])

# Onglet 1 : Prédictions
tab1, tab2, tab3 = st.tabs(["Prédictions", "Performance", "Pronos"])

with tab1:
    st.header("Prédictions du jour")
    # Tableau interactif avec couleurs conditionnelles
    # Graphiques radar par match
    # Détail au clic

with tab2:
    st.header("Performance historique")
    # Courbes de Brier score dans le temps
    # Calibration plot (probas prédites vs fréquences réelles)
    # Performance par ligue, par confiance

with tab3:
    st.header("Pronos combinés")
    # 3 tickets visuels
    # Simulation de gains
```

### 6.2 Graphiques de calibration dans Google Sheets
Ajouter dans le Performance sheet un calibration plot :
- Axe X : probabilité prédite (bins de 10%)
- Axe Y : fréquence réelle d'occurrence
- La diagonale = calibration parfaite

### 6.3 Notifications (Telegram / Discord)
```python
# src/notifications.py
import requests

def send_telegram(message: str, chat_id: str, token: str) -> None:
    """Envoie une notification Telegram."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

def notify_value_bets(predictions: list) -> None:
    """Notifie les paris à valeur détectés."""
    value_bets = [p for p in predictions if p.get("is_value")]
    if value_bets:
        msg = "🔥 <b>VALUE BETS DÉTECTÉS</b>\n\n"
        for bet in value_bets:
            msg += f"⚽ {bet['match']}\n"
            msg += f"   {bet['bet']} @ {bet['odds']} (modèle: {bet['proba']}%)\n\n"
        send_telegram(msg, CHAT_ID, BOT_TOKEN)
```

### 6.4 Améliorer l'onglet Pronos
- Ajouter un résumé visuel du bankroll management (Kelly criterion)
- Ajouter l'historique des tickets passés (P&L cumulé)
- Ajouter un graphique de ROI par stratégie (Safe vs Fun vs Jackpot)

---

## PHASE 7 — UTILITÉ / PERTINENCE (8 → 10) ✅ TERMINÉE
> Durée estimée : 2-3 jours | **Réalisé : ~20 min avec Cursor**

### 7.1 Automatisation complète (CRON)
```bash
# Crontab : exécuter le pipeline chaque jour à 8h
0 8 * * * cd /path/to/project && python run_pipeline.py full >> logs/pipeline.log 2>&1
```

Ou via GitHub Actions :
```yaml
name: Daily Pipeline
on:
  schedule:
    - cron: '0 8 * * *'
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python run_pipeline.py full
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          API_FOOTBALL_KEY: ${{ secrets.API_FOOTBALL_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### 7.2 Suivi du bankroll en temps réel
Table Supabase `bankroll_tracking` :
```sql
CREATE TABLE bankroll_tracking (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticket_type TEXT,         -- 'safe', 'fun', 'jackpot'
    stake NUMERIC(10,2),
    potential_gain NUMERIC(10,2),
    actual_gain NUMERIC(10,2),
    roi NUMERIC(6,4),
    bankroll_after NUMERIC(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 7.3 A/B testing des modèles
Pouvoir comparer 2 versions du modèle en parallèle :
- `hybrid_v3_ml` (actuel)
- `hybrid_v4_ensemble` (nouveau avec stacking)

Enregistrer les 2 prédictions, évaluer sur les mêmes matchs,
comparer les métriques automatiquement.

### 7.4 Support des marchés asiatiques
Ajouter les handicaps asiatiques (-0.5, -1.0, -1.5) et
les marchés de corners / cartons si API-Football les fournit.

---

## RÉSUMÉ DES PHASES

| Phase | Focus | Impact | Durée | Priorité |
|-------|-------|--------|-------|----------|
| 1 | Fondations (git, requirements, structure, logging) | Ingénierie 3→8 | 1-2j | 🔴 CRITIQUE |
| 2 | Qualité code (types, constantes, dataclasses) | Code 6→9 | 2-3j | 🟠 HAUTE |
| 3 | Tests (unitaires, intégration, couverture) | Ingénierie 8→10 | 2-3j | 🟠 HAUTE |
| 4 | Maintenabilité (modules, linter, docs) | Maintenabilité 5→10 | 2-3j | 🟡 MOYENNE |
| 5 | Algorithmes (Dixon-Coles, stacking, features) | Algo 7.5→10 | 3-5j | 🟡 MOYENNE |
| 6 | UI (dashboard, notifications, graphiques) | UI 7→10 | 2-3j | 🟢 NORMALE |
| 7 | Utilité (CRON, bankroll, A/B, marchés) | Utilité 8→10 | 2-3j | 🟢 NORMALE |

**Total estimé : 15-22 jours de travail**

---

## ORDRE D'EXÉCUTION RECOMMANDÉ

```
Phase 1 (Fondations)
    ↓
Phase 2 (Qualité code) + Phase 3 (Tests) en parallèle
    ↓
Phase 4 (Maintenabilité)
    ↓
Phase 5 (Algorithmes) + Phase 6 (UI) en parallèle
    ↓
Phase 7 (Utilité avancée)
```

---

## CRITÈRES DE VALIDATION 10/10

Pour considérer chaque critère à 10/10 :

### Ingénierie : 10/10 ✓ quand
- [ ] Git initialisé avec historique propre
- [ ] > 90% couverture de tests
- [ ] CI/CD fonctionnel (GitHub Actions)
- [ ] Linter + type checker passent sans erreur
- [ ] Zero secret dans le repo

### Code : 10/10 ✓ quand
- [ ] 100% des fonctions ont des type hints
- [ ] 100% des fonctions publiques ont des docstrings
- [ ] Zero bare except
- [ ] Dataclasses pour toutes les structures de données
- [ ] Constantes extraites et documentées
- [ ] Aucune duplication de code

### Maintenabilité : 10/10 ✓ quand
- [ ] Structure en package avec imports propres
- [ ] Code.js découpé en modules
- [ ] README complet avec setup et architecture
- [ ] Makefile / scripts de commandes
- [ ] ruff + mypy configurés

### Algorithmes : 10/10 ✓ quand
- [ ] Dixon-Coles implémenté
- [ ] Ensemble (stacking XGB + LGBM + RF)
- [ ] Backtesting temporel
- [ ] Features avancées (momentum, fatigue, variance)
- [ ] Kelly criterion pour le sizing
- [ ] Calibration isotonique

### UI : 10/10 ✓ quand
- [ ] Dashboard web (Streamlit ou équivalent)
- [ ] Calibration plots
- [ ] Notifications (Telegram/Discord)
- [ ] Historique P&L visuel

### Utilité : 10/10 ✓ quand
- [ ] Pipeline automatisé (CRON / GitHub Actions)
- [ ] Bankroll tracking
- [ ] A/B testing des modèles
- [ ] Support handicap asiatique
- [ ] ROI positif documenté sur > 100 matchs
