# ProbaLab — Instructions projet

## Stack
- **Backend** : FastAPI (Python) + Uvicorn
- **Frontend** : React 19 + Vite + Tailwind CSS 4 + Radix UI (shadcn pattern)
- **Base de données** : Supabase (PostgreSQL + RLS strict)
- **ML** : XGBoost, LightGBM, scikit-learn, Optuna, Pandas, NumPy
- **IA générative** : Google Gemini (analyses narratives)
- **Jobs** : APScheduler (cron) + Trigger.dev (remote jobs)
- **Messagerie** : Telegram bot, Discord webhooks, Resend
- **Paiements** : Stripe (abonnements premium)
- **Déploiement** : Railway (nixpacks) + GitHub Actions CI

## Périmètre métier
Plateforme de prédictions sportives avec value betting
- **Football** : 8 ligues (L1, L2, PL, La Liga, Serie A, Bundesliga, UCL, UEL)
- **NHL** : secondaire
- Marchés : 1X2, Double Chance, BTTS, O/U, Handicaps, Score Exact, Buteurs
- Value betting : ROI + Kelly Criterion
- Combo tickets : Safe / Fun / Jackpot
- Suivi bankroll, P&L, évaluation post-match

## Architecture prédictions (3 couches)
1. **70% stats** : Dixon-Coles, ELO, 50+ features
2. **ML calibré** : XGBoost ensemble
3. **30% IA** : analyse narrative Gemini

## Conventions
- Supabase RLS strict — vérifier les policies avant toute requête
- Timezones : tout en UTC sans exception
- fixture_id : typage strict (pas de mélange int/str)
- Nommage probabilités : respecter la convention établie (voir lessons.md)
- Double Chance : respecter le naming spécifique (voir lessons.md)
- 381 tests — ne jamais merger sans tests verts

## Outils MCP
- **Context7** : consulter avant toute implémentation touchant une API ou librairie
- **Supabase MCP** : inspecter schéma, requêter DB, gérer RLS directement

## État actuel
- En production, stabilisation active
- Phases 1-3 terminées (troncature, types, combos, timezones, Double Chance)
- Audit sécurité mars 2026 (60+ fixes appliqués)
- 30 leçons documentées dans `tasks/lessons.md` — **lire en priorité**

## Pièges documentés (voir tasks/lessons.md pour le détail)
- Timezones : toujours UTC, jamais de conversion implicite
- fixture_id : typage strict partout
- Combos : logique de résolution spécifique, ne pas simplifier
- RLS Supabase : tester les policies après chaque migration
- Gemini : quota et latence — ne pas bloquer le pipeline ML dessus

## Déploiement
- Railway avec nixpacks — vérifier le Procfile avant tout push
- GitHub Actions CI — les tests doivent passer en local avant push

## Workflow vélocité (priorité qualité + sécurité + dette tech, zéro waste)

### Dimensionner le process à la tâche
- **Fix trivial** (1 fichier, ≤ 30 lignes, pas de logique métier — typo, import, valeur par défaut) : edit direct, pas de subagent, pas de plan.
- **Fix ciblé** (1-5 fichiers, logique claire) : 1 subagent implementer + **1 seule review combinée** (spec + qualité). Plan ≤ 50 lignes, pas de pseudo-code verbatim.
- **Feature / architecture** : workflow complet avec plan détaillé + 2 reviews séparées.

### Reviews : sévérité explicite obligatoire
Tout reviewer doit classer chaque issue :
- **BLOCKING** : bug de correctness, faille de sécurité, régression de test, contrat API cassé, RLS absente → rework immédiat.
- **IMPORTANT** : duplication notable, perf hot-path, contrat OpenAPI malhonnête, dette tech tangible → rework immédiat.
- **NITPICK** : naming subjectif, `Number()`/`String()` redondant sur type déjà narrowed, docstring imprécise, magic numbers évidents dans leur contexte → **loggé en follow-up, jamais fixé dans le même commit**.

### Ne pas reworker pour
- Docstrings cosmétiques (« pure function » au lieu de « synchronous »)
- Wrappers de coercion redondants (`Number(x)` quand `typeof x === 'number'` est déjà prouvé)
- Renommage de variable locale sans impact (`leg` vs `pick`)
- Placement d'imports (function-scope vs module-scope) sans problème de side-effect

Ces éléments vont dans un commit refactor séparé si utile.

### Garde-fous non négociables (priment sur la vitesse)
- **TDD** : tout fix de bug commence par un test rouge qui reproduit le bug.
- **Tests verts obligatoires avant push** — pas de régression tolérée.
- **Sécurité** : aucun secret en clair, aucun endpoint admin sans `Depends(verify_internal_auth)`, RLS vérifiées sur toute nouvelle table.
- **Shape API ↔ Frontend** : tout endpoint doit avoir un contract test qui épingle la shape attendue par le frontend (leçon 77).
- **ErrorBoundary** : toute app React de prod DOIT avoir un ErrorBoundary à la racine (leçon 79).
- **Pas de rework silencieux** : si un fix révèle une dette tech ou un anti-pattern qui dépasse le scope, créer une issue/todo dédiée — ne pas mélanger dans le commit courant.

### Choix du modèle subagent
- `haiku` : vérifications, renommages, fixtures, alignements de mocks.
- `sonnet` : implémentation d'un fichier, refactor local, tests de composant.
- `opus` : logique backend complexe, endpoints avec calculs métier, architecture.

### Leçons : apprendre à chaque fois
Après tout fix non trivial, ajouter une ligne à `ProbaLab/tasks/lessons.md` avec format `| date | problème | règle |` — relire au démarrage de toute nouvelle session.
