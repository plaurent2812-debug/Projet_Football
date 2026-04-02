# PLAN D'ACTION — Correction comptabilisation performances ProbaLab

> Audit du 2026-04-02 — 4 agents spécialisés (backend, frontend, pipeline, DB)

## Diagnostic

3 circuits de comptage indépendants, chacun avec ses propres bugs :
- **Performance ML** (`/api/performance`) → table `predictions` + `fixtures`
- **Pronos/Best-Bets** (`/api/best-bets/stats`) → tables `best_bets` + `expert_picks`
- **Performance NHL** (`/nhl/performance`) → table `nhl_suivi_algo_clean`

---

## Phase 1 — Corrections critiques (impact immédiat)

### 1.1 — Inclure les matchs AET/PEN dans `/api/performance`
- **Fichier** : `api/main.py:3139`
- **Bug** : `.eq("status", "FT")` exclut les matchs terminés en prolongation (AET) et tirs au but (PEN)
- **Fix** : Remplacer par `.in_("status", ["FT", "AET", "PEN"])`
- **Impact** : +5-15% de matchs de coupe récupérés
- [ ] Corriger le filtre status

### 1.2 — Déplacer le filtre date côté SQL dans best-bets/stats
- **Fichier** : `api/main.py:1963-2036`
- **Bug** : `.limit(500)` + filtre 30j appliqué en Python après le fetch → troncature silencieuse
- **Fix** : Ajouter `.gte("date", cutoff_30d)` côté SQL, supprimer `.limit(500)`
- **Impact** : +10-40% de paris récupérés dans les stats Pronos
- [ ] Corriger requête expert_picks
- [ ] Corriger requête best_bets
- [ ] Corriger requête history (limit 300 même problème)

### 1.3 — Supprimer le cap 180j pour le filtre "Tout"
- **Fichier** : `api/main.py:3132-3134`
- **Bug** : `days=0` (bouton "Tout") converti silencieusement en 180j
- **Fix** : Si `days == 0`, ne pas appliquer de cutoff date
- [ ] Corriger le cap

### 1.4 — Ajouter pagination NHL performance
- **Fichier** : `api/routers/nhl.py:535-543`
- **Bug** : Pas de `.limit()` → Supabase retourne max 1000 lignes par défaut
- **Fix** : Ajouter `.limit(5000)` ou implémenter pagination
- [ ] Corriger la limite

### 1.5 — Élargir fetch_game_stats NHL à J-1/J-2/J-3
- **Fichier** : `api/main.py:165`
- **Bug** : Stats joueur chargées uniquement pour J-1, les bets J-2/J-3 restent PENDING à jamais
- **Fix** : Boucler `fetch_and_store_game_stats` sur les 3 derniers jours
- [ ] Élargir la fenêtre de fetch

### 1.6 — Unifier les statuts NHL terminés
- **Fichiers** : `fetch_nhl_results.py:36`, `api/main.py:1709`, `update_nhl_results.py:58`, `live.py`
- **Bug** : Chaque module utilise un sous-ensemble différent (`"FINAL"` vs `"Final"` vs `"OFF"` vs `"FT"`)
- **Fix** : Créer une constante `NHL_FINISHED_STATUSES = {"FT", "Final", "FINAL", "OFF", "Official"}` partagée
- [ ] Créer la constante dans `src/nhl/constants.py` ou `src/constants.py`
- [ ] Remplacer tous les hardcoded statuses

### 1.7 — Débloquer les matchs NHL post-LIVE
- **Fichier** : `src/fetchers/update_nhl_results.py:58`
- **Bug** : Filtre `status="NS"` uniquement → matchs passés par LIVE/CRIT jamais retraités
- **Fix** : Filtrer sur `status NOT IN (NHL_FINISHED_STATUSES)` au lieu de `status = "NS"`
- [ ] Corriger le filtre

### 1.8 — Router les expert picks NHL vers nhl_fixtures
- **Fichier** : `api/main.py:2404-2412`
- **Bug** : `/expert-picks/resolve` cherche dans `fixtures` (football) même pour `sport="nhl"`
- **Fix** : Si `sport == "nhl"`, chercher dans `nhl_fixtures`
- [ ] Ajouter le branchement par sport

---

## Phase 2 — Corrections majeures (fiabilité)

### 2.1 — Corriger le type mismatch fixture_id TEXT vs INT
- **Fichier** : `api/main.py:1633`
- **Bug** : `fixture_id` est TEXT en DB, `fixtures.id` est numérique → lookup direct échoue (`"123" != 123`)
- **Fix** : `int(fixture_id)` dans la comparaison Python
- [ ] Corriger la comparaison

### 2.2 — Normaliser proba_over_2_5 partout
- **Fichiers** : `src/brain.py:563,798`, `api/main.py:886,3256`
- **Bug** : `proba_over_25` et `proba_over_2_5` utilisés de manière incohérente → NULL dans les stats Over 2.5
- **Fix** : Tout aligner sur `proba_over_2_5` (nom de la colonne DB)
- [ ] Auditer toutes les occurrences
- [ ] Remplacer `proba_over_25` → `proba_over_2_5`

### 2.3 — Unifier les sources de données NHL
- **Tables** : `nhl_suivi_algo_clean` vs `best_bets`
- **Bug** : La page Perf NHL lit l'ancienne table, les nouveaux paris vont dans `best_bets`
- **Fix** : Soit migrer vers une source unique, soit faire lire `/nhl/performance` depuis `best_bets` aussi
- [ ] Choisir la stratégie
- [ ] Implémenter

### 2.4 — Corriger la fenêtre timezone UTC/Paris pour résolution
- **Fichier** : `src/fetchers/results.py:128-133`
- **Bug** : Fixtures en heure Paris, résolution en UTC → matchs tardifs (22h+) dans le mauvais jour
- **Fix** : Utiliser Europe/Paris dans le calcul de fenêtre OU élargir à D-1/D+1
- [ ] Corriger la fenêtre

### 2.5 — Remplacer datetime.now() naive dans nhl.py
- **Fichier** : `api/routers/nhl.py:540`
- **Fix** : `datetime.now(timezone.utc)`
- [ ] Corriger

---

## Phase 3 — Améliorations (robustesse)

### 3.1 — Résoudre les combinés LOSS dès qu'un leg est LOSS
- **Fichier** : `api/main.py:2510-2539`
- **Bug** : Un leg introuvable bloque le combiné même si un autre leg est clairement LOSS
- **Fix** : Si un leg est LOSS → résultat = LOSS immédiat, pas besoin d'attendre les autres
- [x] Corriger la logique

### 3.2 — Résoudre les paris FUN comme combinés
- **Fichier** : `api/main.py:1385-1395`
- **Bug** : Chaque leg est résolu indépendamment → 3W+1L = 3 WIN au lieu de 1 LOSS global
- **Fix** : Lier les legs FUN et résoudre comme un combiné
- [x] Implémenter

### 3.3 — Endpoint de backfill pour bets PENDING anciens
- **Bug** : Pas de mécanisme de rattrapage pour les bets PENDING > 3 jours
- **Fix** : Créer un endpoint `/api/best-bets/backfill` qui re-tente la résolution sur les 30 derniers jours
- [x] Créer l'endpoint

### 3.4 — Aligner stats frontend/backend dans ParisDuSoir
- **Fichier** : `dashboard/src/pages/ParisDuSoir.tsx:861-881`
- **Bug** : Le frontend recalcule les stats avec des cotes estimées (1.85 par défaut) qui divergent du backend
- **Fix** : Utiliser uniquement les stats du backend, supprimer le recalcul client
- [x] Refactorer

### 3.5 — Normaliser Double Chance 1N/1X
- **Fichier** : `api/main.py:1927` vs `1602`
- **Bug** : `normalize_market` mappe "Double Chance 1X" → "Double Chance 1N", mais la résolution compare à "Double Chance 1X"
- **Fix** : Aligner les noms de marché entre normalisation et résolution
- [x] Corriger

---

## Estimation

| Phase | Effort | Impact |
|-------|--------|--------|
| Phase 1 | ~1h30 | Corrige **80%+** des matchs non comptabilisés |
| Phase 2 | ~2h | Fiabilise les données et élimine les cas limites |
| Phase 3 | ~1h30 | Robustesse long terme et cohérence UI |

## Vérification post-correction

- [ ] Comparer le nombre total de bets PENDING avant/après dans `best_bets` et `expert_picks`
- [ ] Vérifier que les stats Pronos 30j matchent le volume réel de paris
- [ ] Vérifier que "Tout" affiche bien plus de matchs que "90j"
- [ ] Vérifier les stats NHL sur 90j vs le nombre réel dans `nhl_suivi_algo_clean`
- [ ] Tester un match AET récent et confirmer qu'il apparaît dans Performance
