# Football IA — Prédictions de matchs par modèle hybride

Système complet de prédiction de matchs de football combinant **statistiques avancées** (Dixon-Coles, ELO temporel, xG), **Machine Learning** (XGBoost + backtesting temporel) et **IA générative** (Claude Sonnet 4). Les résultats sont accessibles via **Google Sheet** interactif et **notifications Telegram/Discord** avec value betting intégré (Kelly criterion).

---

## Architecture

```
Projet_Football/
├── Projet_Football/              # Code source Python
│   ├── config.py                 # Configuration centralisée (Supabase, API keys, logging)
│   ├── constants.py              # Constantes et hyperparamètres (~60 paramètres)
│   ├── run_pipeline.py           # Point d'entrée CLI (data / analyze / full)
│   ├── brain.py                  # Orchestrateur IA (Claude + blend stats/IA)
│   ├── backfill_value.py         # Calcul du value betting
│   │
│   ├── fetchers/                 # Collecte de données
│   │   ├── matches.py            # Matchs (API-Football → Supabase)
│   │   ├── teams.py              # Équipes et effectifs
│   │   ├── players.py            # Joueurs et stats saison
│   │   ├── context.py            # Blessures, arbitres, cotes, météo
│   │   └── history.py            # Historique (events, lineups, stats)
│   │
│   ├── models/                   # Moteurs de calcul
│   │   ├── stats_engine.py       # Moteur statistique (Dixon-Coles, ELO, form, H2H…)
│   │   ├── scorer_engine.py      # Prédiction buteurs (scoring rate, position)
│   │   ├── ml_predictor.py       # Prédictions ML (XGBoost, 6 modèles)
│   │   ├── calibrate.py          # Calibration Platt + Isotonique + bias tracking
│   │   ├── ab_testing.py         # A/B testing de modèles (comparaison Brier/accuracy)
│   │   └── dataclasses.py        # Structures de données (MatchPrediction, etc.)
│   │
│   ├── training/                 # Pipeline ML
│   │   ├── fetch_history.py      # Collecte données historiques
│   │   ├── build_data.py         # Construction features ML
│   │   ├── train.py              # Entraînement XGBoost (1X2, BTTS, O/U)
│   │   └── evaluate.py           # Évaluation post-match
│   │
│   │
│   ├── notifications.py          # Alertes Telegram & Discord
│   ├── bankroll.py               # Gestion bankroll + P&L tracking
│   │
│   ├── tests/                    # Tests (381 tests)
│   │   ├── conftest.py           # Fixtures partagées + MockSupabase
│   │   ├── test_stats_engine.py  # Dixon-Coles, ELO decay, Kelly criterion
│   │   ├── test_brain.py
│   │   ├── test_scorer_engine.py
│   │   ├── test_calibrate.py     # Platt + Isotonic calibration
│   │   ├── test_ml_predictor.py
│   │   ├── test_evaluate.py
│   │   ├── test_build_data.py    # Advanced features (momentum, fatigue…)
│   │   ├── test_notifications.py # Telegram & Discord (mocked HTTP)
│   │   ├── test_bankroll.py      # Bankroll tracking (mocked Supabase)
│   │   ├── test_ab_testing.py    # A/B testing des modèles
│   │   ├── test_dataclasses.py
│   │   └── test_*_integration.py # Tests d'intégration (mock Supabase)
│   │
│   └── google_apps_script/       # Interface Google Sheet
│       ├── Config.js             # Constantes, menu, dialog
│       ├── ApiHelpers.js         # Supabase REST, API-Football, Claude
│       ├── ImportMatches.js      # Import des matchs
│       ├── Analysis.js           # Analyse IA + reanalyse
│       ├── Display.js            # Affichage prédictions
│       ├── Performance.js        # Évaluation post-match
│       ├── Pronos.js             # Tickets combinés (Bet Builder)
│       └── appsscript.json       # Manifest GAS
│
├── Makefile                      # Commandes projet (make help)
├── requirements.txt              # Dépendances Python
├── ruff.toml                     # Config linter/formatter
├── mypy.ini                      # Config type checker
├── pytest.ini                    # Config tests
└── .gitignore
```

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| **Langage** | Python 3.10+, JavaScript (Google Apps Script) |
| **Base de données** | Supabase (PostgreSQL hébergé) |
| **API données** | API-Football v3 (8 ligues européennes) |
| **IA générative** | Anthropic Claude Sonnet 4 |
| **ML** | XGBoost, scikit-learn (Isotonic, Platt, TimeSeriesSplit) |
| **Stats** | Dixon-Coles, ELO temporel, Decay exponentiel, Kelly criterion |
| **Interface** | Google Sheets + Telegram/Discord |
| **Qualité** | ruff (lint+format), mypy (types), pytest (381 tests), GitHub Actions CI |

---

## Installation

### Prérequis

- Python 3.10+
- Compte Supabase (gratuit)
- Clé API-Football (api-sports.io)
- Clé API Anthropic (Claude)

### Setup

```bash
# 1. Cloner le projet
git clone <repo-url> && cd Projet_Football

# 2. Installer les dépendances
make install
# ou : pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp Projet_Football/.env.example Projet_Football/.env
# Éditer .env avec vos clés

# 4. Vérifier l'installation
make check   # lint + types + tests
```

---

## Utilisation

### Pipeline principal (CLI)

```bash
# Collecter les données (matchs, joueurs, blessures, cotes, météo)
make run-data

# Lancer l'analyse (stats + ML + IA → prédictions)
make run-analyze

# Pipeline complet
make run-full
```

### Machine Learning

```bash
# Entraîner les modèles (fetch historique → features → XGBoost)
make train

# Calibrer les probabilités (Platt scaling sur résultats passés)
make calibrate

# Évaluer les performances
make evaluate
```


### Notifications

Les value bets sont envoyés automatiquement par Telegram et/ou Discord. Configurer les variables dans `.env` :
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
DISCORD_WEBHOOK_URL=...  (optionnel)
```

### Google Sheet

1. Ouvrir le Google Sheet lié
2. Menu **⚽ Football IA** :
   - **① Importer les matchs** — récupère les prochaines journées
   - **② Lancer l'analyse IA** — génère les prédictions
   - **③ Rafraîchir l'affichage** — met à jour le tableau + value betting
   - **④ Générer les Pronos** — 3 tickets combinés (Safe, Fun, Jackpot)
   - **📈 Performance** — évaluation post-match automatique

---

## Qualité du code

```bash
make lint       # Vérification ruff (0 erreur)
make format     # Formatage automatique
make typecheck  # Vérification mypy (0 erreur)
make test       # 381 tests
make test-cov   # Tests avec rapport de couverture
make check      # Tout d'un coup (CI)

make clean      # Nettoyage __pycache__, .pyc, etc.
```

---

## Modèle de prédiction

Le système utilise un **modèle hybride à 3 couches** :

1. **Couche statistique** (70%) — Poisson + ELO + 10 facteurs contextuels
2. **Couche ML** (calibrée) — XGBoost entraîné sur l'historique
3. **Couche IA** (30%) — Claude analyse le contexte qualitatif

### Facteurs pris en compte

- Force attaque/défense par équipe (Dixon-Coles, correction Poisson)
- Classement ELO temporel (K=32, avantage domicile=65, decay)
- Forme récente (décroissance exponentielle) + Momentum (3 vs 6 matchs)
- Jours de repos / congestion calendaire / Fatigue index (14 jours)
- Enjeu du match (titre, relégation, mid-table)
- Head-to-Head historique
- Blessures joueurs clés (impact par poste)
- Impact arbitre (cartons/90, penaltys/match)
- Météo (pluie, vent, températures extrêmes)
- Variance des résultats (imprévisibilité)
- Taux de clean sheets
- Calibration via cotes bookmakers (overround supprimé)
- Calibration isotonique + Platt Scaling des probabilités

### Marchés couverts

1X2, Double Chance, BTTS, Over/Under (0.5–3.5), **Handicaps asiatiques** (-0.5, -1.0, -1.5), Score exact, Penalty, Buteur probable, Value Betting (ROI + Kelly criterion), Tickets combinés (Bet Builder), Bankroll tracking.

---

## CI/CD & Automatisation

- **GitHub Actions CI** — Lint + types + tests sur chaque push/PR (Python 3.10/3.11/3.12)
- **Pipeline quotidien** — Collecte + analyse automatique via `cron: '0 8 * * *'` (GitHub Actions)
- **Bankroll tracking** — Suivi P&L en temps réel, résolution automatique des paris
- **A/B testing** — Comparaison de modèles en parallèle (Brier score, accuracy, intervalle de confiance)

---

## Ligues suivies

| Ligue | Pays |
|-------|------|
| Ligue 1 | France |
| Ligue 2 | France |
| Premier League | Angleterre |
| La Liga | Espagne |
| Serie A | Italie |
| Bundesliga | Allemagne |
| Champions League | Europe |
| Europa League | Europe |

---

## Licence

Projet personnel — usage privé.
