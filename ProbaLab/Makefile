# ══════════════════════════════════════════════════════════════
#  Football IA — Makefile
# ══════════════════════════════════════════════════════════════

PYTHON   := python3
PROJECT  := Projet_Football
SRC      := $(PROJECT)/models $(PROJECT)/fetchers $(PROJECT)/training $(PROJECT)/brain.py $(PROJECT)/config.py $(PROJECT)/constants.py
TESTS    := $(PROJECT)/tests

.PHONY: help install test test-cov lint format typecheck check run-data run-analyze run-full train clean

# ── Aide ──────────────────────────────────────────────────────
help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Installation ──────────────────────────────────────────────
install: ## Installe les dépendances
	$(PYTHON) -m pip install -r requirements.txt

# ── Tests ─────────────────────────────────────────────────────
test: ## Lance les tests
	cd $(PROJECT) && $(PYTHON) -m pytest tests/ -v --tb=short

test-cov: ## Lance les tests avec couverture
	cd $(PROJECT) && $(PYTHON) -m pytest tests/ \
		--cov=models --cov=training --cov=brain --cov=config --cov=constants \
		--cov-report=term-missing -v --tb=short

# ── Qualité du code ──────────────────────────────────────────
lint: ## Vérifie le code avec ruff
	ruff check $(SRC) $(TESTS)

format: ## Formate le code avec ruff
	ruff format $(SRC) $(TESTS)

typecheck: ## Vérifie les types avec mypy
	mypy $(PROJECT)/models $(PROJECT)/training $(PROJECT)/brain.py $(PROJECT)/config.py \
		--ignore-missing-imports --no-error-summary

check: lint typecheck test ## Lint + types + tests (CI complet)

# ── Pipeline ──────────────────────────────────────────────────
run-data: ## Collecte les données (API-Football → Supabase)
	cd $(PROJECT) && $(PYTHON) run_pipeline.py data

run-analyze: ## Lance l'analyse (Stats + IA → Prédictions)
	cd $(PROJECT) && $(PYTHON) run_pipeline.py analyze

run-full: ## Pipeline complet (données + analyse)
	cd $(PROJECT) && $(PYTHON) run_pipeline.py full

# ── ML ────────────────────────────────────────────────────────
train: ## Entraîne les modèles ML (fetch + build + train)
	cd $(PROJECT) && $(PYTHON) -m training.fetch_history
	cd $(PROJECT) && $(PYTHON) -m training.build_data
	cd $(PROJECT) && $(PYTHON) -m training.train

calibrate: ## Calibre les probabilités sur les résultats passés
	cd $(PROJECT) && $(PYTHON) -m models.calibrate

evaluate: ## Évalue les prédictions vs résultats réels
	cd $(PROJECT) && $(PYTHON) -m training.evaluate

# ── Nettoyage ─────────────────────────────────────────────────
clean: ## Supprime les fichiers générés
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
	rm -rf $(PROJECT)/.pytest_cache $(PROJECT)/.coverage
