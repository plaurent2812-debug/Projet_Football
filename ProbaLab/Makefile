# ══════════════════════════════════════════════════════════════
#  ProbaLab — Makefile
# ══════════════════════════════════════════════════════════════

PYTHON   := python3
SRC      := src api
TESTS    := tests

.PHONY: help install test test-cov lint format typecheck check run-data run-analyze run-full train calibrate evaluate clean

# ── Aide ──────────────────────────────────────────────────────
help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Installation ──────────────────────────────────────────────
install: ## Installe les dépendances
	$(PYTHON) -m pip install -r requirements.txt

# ── Tests ─────────────────────────────────────────────────────
test: ## Lance les tests
	$(PYTHON) -m pytest $(TESTS)/ -v --tb=short

test-cov: ## Lance les tests avec couverture
	$(PYTHON) -m pytest $(TESTS)/ \
		--cov=src --cov=api \
		--cov-report=term-missing -v --tb=short

# ── Qualité du code ──────────────────────────────────────────
lint: ## Vérifie le code avec ruff
	ruff check $(SRC) $(TESTS)

format: ## Formate le code avec ruff
	ruff format $(SRC) $(TESTS)

typecheck: ## Vérifie les types avec mypy
	mypy src/ --ignore-missing-imports --no-error-summary

check: lint typecheck test ## Lint + types + tests (CI complet)

# ── Pipeline ──────────────────────────────────────────────────
run-data: ## Collecte les données (API-Football → Supabase)
	$(PYTHON) run_pipeline.py data

run-analyze: ## Lance l'analyse (Stats + IA → Prédictions)
	$(PYTHON) run_pipeline.py analyze

run-full: ## Pipeline complet (données + analyse)
	$(PYTHON) run_pipeline.py full

# ── ML ────────────────────────────────────────────────────────
train: ## Entraîne les modèles ML (fetch + build + train)
	$(PYTHON) -m src.training.fetch_history
	$(PYTHON) -m src.training.build_data
	$(PYTHON) -m src.training.train

calibrate: ## Calibre les probabilités sur les résultats passés
	$(PYTHON) -m src.models.calibrate

evaluate: ## Évalue les prédictions vs résultats réels
	$(PYTHON) -m src.training.evaluate

# ── Nettoyage ─────────────────────────────────────────────────
clean: ## Supprime les fichiers générés
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
