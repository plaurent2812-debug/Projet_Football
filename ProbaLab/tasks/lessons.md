# Lessons Learned

| Date | Problème | Règle |
|------|----------|-------|
| 2026-03-19 | Rho scaling discontinu : interpolation linéaire avec coefficient 0.4 au lieu de 0.6, saut de 22% à xG=3.5 | Toujours vérifier la continuité aux bornes des interpolations linéaires par morceaux |
| 2026-03-19 | poisson_grid retournait sum≠100 (99 ou 101) — arrondis indépendants de 3 probas | Pour N probas sommant à 100%, toujours forcer le dernier = 100 - somme(autres) |
| 2026-03-19 | MAX_GOALS_GRID=7 : 11% de masse Poisson perdue à xG=4.0. Grid=10 ramène à 0.8% | Dimensionner les grilles pour capturer ≥99% de la masse aux valeurs extrêmes autorisées |
| 2026-03-19 | Double comptage nuls CL : draw calibration cible déjà le taux historique, euro_boost ajoutait +4% en plus | Quand un paramètre est déjà calibré sur des données historiques, ne pas ajouter de boost ad hoc sur le même signal |
| 2026-03-19 | Ensemble sans class balancing : les 3 base learners ignoraient le déséquilibre H/D/A | Vérifier que TOUS les modèles d'un pipeline reçoivent sample_weight, pas seulement le standalone |
| 2026-03-19 | eval_set=(X_test, y_test) dans ensemble : le modèle voit le test set pendant l'entraînement | Toujours utiliser un validation set séparé pour l'early stopping, jamais le test set |
| 2026-03-19 | RestrictedUnpickler startswith("sklearn") trop large : n'importe quel sous-module sklearn autorisé | Whitelist par préfixes spécifiques, pas par un startswith global |
| 2026-03-22 | Data leakage : imputer.fit_transform(X) sur tout le dataset avant le TimeSeriesSplit — les médianes du futur fuitent dans le train | Toujours fit l'imputer sur X_train APRÈS le split, puis transform X_test séparément |
| 2026-03-22 | cross_val_score(params={"sample_weight": ...}) silencieusement ignoré — le param correct est fit_params= | Vérifier la doc sklearn pour les noms de paramètres exacts, surtout les kwargs relayés |
| 2026-03-22 | Fallback proba_map {"H": probas[0]} faux : LabelEncoder trie alphabétiquement → probas[0]=A, pas H | Sans LabelEncoder, toujours utiliser l'ordre alphabétique ['A','D','H'] pour mapper les probas sklearn |
| 2026-03-22 | Noms d'équipes injectés directement dans les prompts Gemini via f-strings — injection de prompt possible | Toujours sanitiser les inputs utilisateur/DB avant injection dans un prompt LLM |
| 2026-03-22 | Appel Gemini sans retry : un timeout ou erreur transitoire fait perdre toute l'analyse IA du match | Toujours wrapper les appels API externes avec au moins 1 retry + sleep |
| 2026-03-22 | Variables injectées dans du HTML Telegram sans échappement — risque XSS/formatting cassé | Toujours html.escape() les variables avant injection dans du HTML |
| 2026-03-22 | pickle.load non sécurisé dans nhl.py router — modèle chargé sans restriction | Toujours utiliser un RestrictedUnpickler pour charger des fichiers pickle, même pour des modèles internes |
| 2026-03-22 | HTTPException detail=str(e) expose des infos internes (stack, DB schema) | Toujours logger l'erreur côté serveur et retourner un message générique au client |
| 2026-03-22 | Comparaison CRON_SECRET via == vulnérable au timing attack | Utiliser hmac.compare_digest pour toute comparaison de secrets |
| 2026-03-22 | api_get retournait HTTP 200 avec response=[] sans retry — données perdues silencieusement | Ajouter un second niveau de retry (api_get_with_retry) pour les endpoints critiques qui retournent des réponses vides |
| 2026-03-22 | datetime.now() sans timezone dans config.py et matches.py — comparaisons naive vs aware impossibles | Toujours utiliser datetime.now(timezone.utc) — jamais datetime.now() nu |
| 2026-03-22 | place_bet read-then-write non atomique : deux paris simultanés lisent le même bankroll | Pour toute opération read-modify-write sur une ressource partagée, utiliser SELECT FOR UPDATE dans une fonction PostgreSQL (RPC) |
| 2026-03-22 | BTTS accuracy utilisait total_with_pred comme dénominateur au lieu d'un compteur dédié — les matchs sans proba_btts comptaient comme "No BTTS" | Chaque marché doit avoir son propre compteur total, comme Over/Under le faisait déjà |
| 2026-03-30 | proba_over_05/15/35 sauvés dans stats_json mais pas en colonnes DB — best-bets les lisait comme NULL, Over 1.5/3.5 jamais générés | Quand une colonne DB existe pour un champ, toujours l'inclure dans insert_data, pas seulement dans stats_json |
| 2026-03-30 | `get_val("x") or get_val("y")` — si x vaut 0 (falsy), fallback inattendu sur y | Toujours utiliser `if x is None` au lieu de `or` pour des valeurs numériques qui peuvent être 0 |
| 2026-03-30 | Combo resolve : `all_win = None` écrasait `all_win = False` — combos LOSS restaient PENDING | Séparer les flags booléens : un pour le résultat (all_win), un autre pour les données manquantes (has_unknown) |
