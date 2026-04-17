# 06 — Sécurité

## 1. Périmètre audité

### Fichiers inspectés
- `ProbaLab/api/auth.py` (55 LOC) — helpers d'auth centralisés (CRON, JWT admin)
- `ProbaLab/api/rate_limit.py` (49 LOC) — wrapper slowapi
- `ProbaLab/api/schemas.py` (77 LOC) — modèles Pydantic requêtes
- `ProbaLab/api/main.py` (225 LOC) — middlewares, CORS, security headers
- `ProbaLab/api/routers/*.py` (16 routeurs, ~5000 LOC) incluant `stripe_webhook.py`, `telegram.py`, `admin.py`, `trigger.py`, `expert_picks.py`, `best_bets.py`, `players.py`, `nhl.py`, `push.py`
- `ProbaLab/src/config.py` — client Supabase (service_role)
- `ProbaLab/src/models/ml_predictor.py`, `src/nhl/ml_models.py`, `api/routers/nhl.py` — RestrictedUnpickler
- `ProbaLab/migrations/010_security_fixes.sql`, `019_atomic_place_bet.sql`, `020_enable_rls_all_tables.sql`
- `ProbaLab/src/prompts.py` — sanitisation prompts Gemini
- `ProbaLab/src/notifications.py`, `src/monitoring/alerting.py` — échappement HTML Telegram

### Périmètre exclu
- Front-end (annexe 07)
- CI/CD et secrets GitHub Actions (annexe 08)
- Tests de sécurité automatisés hors-scope (aucun `bandit`/`pip-audit` dans la CI observée)

---

## 2. État actuel

### 2.1 Ce qui fonctionne bien

1. **`hmac.compare_digest` appliqué partout sur les secrets** (leçon 20 résolue)
   - `api/auth.py:27` — `verify_cron_auth` compare `"Bearer {CRON_SECRET}"` en constant-time
   - `api/auth.py:37`, `api/routers/trigger.py:44`, `api/routers/nhl.py:111`, `api/routers/telegram.py:508` — tous alignés
   - Plus aucun `==` sur un secret dans le code de routage

2. **Stripe webhook idempotent et atomique** (leçon 36 résolue)
   - `api/routers/stripe_webhook.py:35-51` — `INSERT into processed_events` puis catch unique violation (`23505` / `duplicate key`)
   - Plus de SELECT-then-INSERT : la course est réglée par la contrainte unique
   - `construct_event` vérifie la signature Stripe avant toute lecture du payload

3. **Telegram webhook fail-closed** (leçon 37 résolue)
   - `api/routers/telegram.py:499-500` — rejette 503 si `TELEGRAM_WEBHOOK_SECRET` absent
   - Vérification du header `X-Telegram-Bot-Api-Secret-Token` en constant-time (ligne 508)
   - Rate limit in-memory (30 req/min/IP) dédié en plus du slowapi global

4. **SecurityHeadersMiddleware présent** (leçon 42 résolue)
   - `api/main.py:147-158` — X-Content-Type-Options, X-Frame-Options: DENY, X-XSS-Protection, Referrer-Policy, HSTS (https only)
   - Middleware ordonné correctement (LIFO Starlette) : headers appliqués sur toutes les réponses, y compris les erreurs

5. **Rate limiting fail-loud** (leçon 41 résolue)
   - `api/rate_limit.py:24` — `logging.critical("SECURITY: slowapi is NOT installed — rate limiting is DISABLED")` au démarrage si module absent
   - Warning répété à la première route touchée si no-op (ligne 42)

6. **Désérialisation binaire restreinte partout** (leçons 11, 18 résolues)
   - 5 implémentations de `RestrictedUnpickler` (ml_predictor.py, ensemble.py, train.py, nhl.py, ml_models.py, nhl_ml_predictor.py) avec whitelist de préfixes stricts (`sklearn.linear_model`, `sklearn.calibration`, etc. — plus de `startswith("sklearn")` générique)
   - `api/routers/nhl.py:53` utilise bien `safe_pickle_load` au lieu de l'API de désérialisation brute

7. **RLS activée sur toutes les tables publiques** (leçon 58 résolue)
   - `migrations/020_enable_rls_all_tables.sql` — `ENABLE ROW LEVEL SECURITY` sur 40+ tables
   - Policy `users_read_own_profile` sur `profiles` (auth.uid() = id)
   - Backend utilise `SUPABASE_SERVICE_ROLE_KEY` (`src/config.py:45,53`) → bypasse RLS
   - Frontend uses anon key avec policies explicites

8. **Trigger profiles anti-escalade** (`migrations/010_security_fixes.sql:9-28`)
   - `protect_profile_escalation()` force la réinitialisation de `role`, `stripe_customer_id`, `subscription_status` si la mise à jour ne vient pas du `service_role`
   - Protection forte contre IDOR sur la promotion premium/admin

9. **place_bet atomique via RPC PostgreSQL** (leçon 23 résolue)
   - `migrations/019_atomic_place_bet.sql` — `SELECT ... FOR UPDATE` + `INSERT` dans une fonction plpgsql
   - Élimine la race condition read-then-write sur `bankroll_tracking`

10. **Retry Gemini + HTML-escape Telegram** (leçons 15, 17 résolues)
    - `src/ai_service.py:118,155` — 1 retry + sleep(2) sur `ask_gemini`
    - `src/notifications.py:144-216`, `src/monitoring/alerting.py:102-104`, `src/monitoring/drift_detector.py:79-82` — `html.escape()` systématique avant injection HTML

11. **Exception handler global masque les détails internes** (leçon 19 partiellement résolue)
    - `api/main.py:179-186` — retourne `{"detail": "Internal server error"}` générique, logge la stack côté serveur

12. **CORS restreint avec validation d'URL** (`api/main.py:117-140`)
    - Parsing `urlparse` pour rejeter les origines malformées
    - Fallback localhost en dev, jamais `*`

### 2.2 Dette technique / bugs latents

1. **`extra="forbid"` absent sur TOUS les modèles de requête** (Phase 3.2 todo.md non démarrée)
   - `api/schemas.py` — `EmailPayload`, `SaveBetRequest`, `DateRequest`, `ResolveBetsRequest`, etc. : aucun `model_config = ConfigDict(extra="forbid")`
   - `api/response_models.py` utilise `extra="allow"` (29 occurrences) — OK pour les réponses, mais les requêtes héritent implicitement de `extra="ignore"` (défaut Pydantic)
   - **Conséquence** : un client peut envoyer `{"date": "2026-04-17", "sport": "football", "admin": true}` → le champ `admin` est silencieusement ignoré, pas d'erreur 422. Attaque par mass assignment possible si une future refacto lit le `body.dict()` brut
   - Impact actuel = faible mais c'est un couteau suisse à poser avant la prochaine refacto

2. **`detail=str(e)` résiduel** (leçon 19 partiellement contournée)
   - `api/routers/players.py:162` — `raise HTTPException(status_code=500, detail=str(e))` dans `get_player_profile`
   - Route publique `/api/players/{player_id}` → une erreur Supabase ou httpx exposera potentiellement schema DB / URL interne
   - Seul endroit restant dans l'API — correction triviale

3. **Auth log admin incomplet** (leçon 43 partiellement résolue)
   - `api/auth.py:38,49,53` — logs `ADMIN_AUTH_OK` / `FAIL` **uniquement** dans `verify_internal_auth`
   - `api/routers/admin.py:_require_admin` (admin.py:43-62) : aucun log audit
   - `api/routers/trigger.py:verify_trigger_auth` (ligne 37) : pas de `ADMIN_AUTH_OK` ni d'identification user_id
   - Les actions les plus sensibles (run-pipeline, stop-pipeline, delete-user, update-role, update-scores) ne sont **pas tracées** avec qui
   - Impossible en cas d'incident de répondre "quel admin a supprimé tel user"

4. **`/api/admin/update-scores` auth-optionnelle** (risque moyen)
   - `api/routers/admin.py:234-269` — commentaire explicite : *"No auth required when called internally (Railway CRON)"*
   - Si `authorization` absent → exécute `fetch_and_update_results(date)` sans aucune vérif
   - Détourné : n'importe qui peut déclencher un re-fetch des scores → DoS potentiel sur API-Football (quota payant), pollution de la table fixtures si l'API retourne mal
   - **Contournement recommandé** : Railway a un header `X-Railway-Internal` ou restreindre par header `X-Cron-Internal: {secret}` plutôt que l'absence d'auth comme pass

5. **`datetime.utcnow()` / `datetime.now()` sans tz résiduels** (leçon 22 partiellement résolue)
   - `api/routers/trigger.py:132,133,448`, `api/routers/telegram.py:138,187`, `api/routers/best_bets.py:1306`, `api/routers/monitoring.py:99`
   - Pas un risque de sécurité direct, mais comparaisons naive vs aware peuvent créer des bugs d'auth (ex: expiration JWT mal comparée — pas observé ici, mais le pattern est dangereux)

6. **Rate limiting non différencié par tier** (Phase 3.3 todo.md non démarrée)
   - `api/rate_limit.py` — `key_func=get_remote_address`, default `RATE_LIMIT_DEFAULT` unique
   - Pas de distinction free/premium/admin ; un abonné premium est soumis aux mêmes limites qu'un scraper anonyme
   - Couverture très inégale : sur ~40 POST/PUT/DELETE, seuls **6 endpoints** ont un `@_rate_limit` explicite (best_bets.py:52,763,785,849,1108 + predictions.py:33)
   - `/api/webhook/stripe`, `/api/cron/run-pipeline`, `/api/telegram/webhook`, tous les `/api/trigger/*`, tous les `/api/admin/*` : **aucun rate limit** au niveau slowapi (seul Telegram a son propre rate limit in-memory)

7. **CORS `allow_credentials=True` avec liste d'origines configurable**
   - `api/main.py:139` — OK si `ALLOWED_ORIGINS` est proprement configuré en prod
   - Aucune vérif que `ALLOWED_ORIGINS` **ne contient pas** `*` ou `null` : un env mal rempli ouvrirait CORS largement
   - Pas bloquant mais mérite une assertion fail-loud au démarrage

### 2.3 Code smells repérés

1. **5 classes `RestrictedUnpickler` dupliquées** (`ml_predictor.py`, `ensemble.py`, `train.py`, `nhl.py`, `nhl_ml_predictor.py`, `ml_models.py`) — divergence des whitelists inévitable à moyen terme. Un seul module `src/security/safe_pickle.py` unifierait ça.

2. **Stockage in-memory des pending picks Telegram** (`api/routers/telegram.py:62,66`)
   - `_pending_picks: dict[int, dict]` perdus au redémarrage Railway
   - Si Railway scale à 2 instances, la confirmation `👍` peut tomber sur l'instance qui n'a pas le pending → perte
   - Pas un trou de sécurité mais un bug silencieux qui pourrait masquer une attaque (replay)

3. **`verify_trigger_auth` duplique `verify_internal_auth`** (`api/routers/trigger.py:37-64` vs `api/auth.py:31-54`)
   - Même logique, deux codepaths. Celui de trigger.py ne log pas la source → dette

4. **Health check fuit la dispo des dépendances** (`api/main.py:192-225`)
   - `{"checks": {"supabase": "degraded", "gemini": "unavailable"}}` public
   - Utile pour le monitoring mais donne des infos à un attaquant (quelles dépendances sont down, timing)
   - Recommandation : endpoint `/health/detailed` authentifié + `/health` binaire public

### 2.4 Gaps vs. OWASP Top 10 / best practices

| OWASP 2021 | Statut | Preuves |
|---|---|---|
| A01 Broken Access Control | **Moyen** | `_require_admin` OK (admin.py), policies RLS posées (020), trigger profiles anti-escalade OK. **Mais** `/api/admin/update-scores` accepte no-auth + DELETE expert-pick passe par `verify_internal_auth` (OK, leçon 34 résolue) |
| A02 Cryptographic Failures | **OK** | `hmac.compare_digest` partout, pas de secret en dur, Stripe signature vérifiée |
| A03 Injection | **OK** | Supabase client paramétré (pas de SQL brut). Gemini : `_sanitize_team_name` en place (prompts.py:17). Telegram HTML échappé. Pas de `eval`/`exec` trouvés |
| A04 Insecure Design | **Moyen** | Pas de threat modeling formel. Webhooks n'ont pas de replay protection (Stripe oui via idempotence, Telegram non — repose sur `_pending_picks` en RAM) |
| A05 Security Misconfiguration | **Moyen** | Security headers OK, CORS OK, **mais** pas de CSP, pas de COOP/COEP. Admin JWT vérifié via `supabase.auth.get_user` (appel externe par requête — cacheable mais non caché) |
| A06 Vulnerable Components | **Inconnu** | Pas de `pip-audit` dans la CI observée. `requirements.txt` à auditer (hors scope annexe 08) |
| A07 Auth Failures | **OK** | CRON_SECRET + JWT double gate, constant-time compare, fail-closed sur webhook secrets |
| A08 Software/Data Integrity | **OK** | Désérialisation binaire restreinte généralisée (leçon 11+18), pas de deserialization sauvage |
| A09 Logging & Monitoring | **Faible** | Logs de base, pas de centralisation (ELK/Datadog non observé). `ADMIN_AUTH_OK` seulement dans 1 endpoint sur les ~20 admin. Pas de rate d'auth failures trackable |
| A10 SSRF | **OK** | Pas d'endpoint qui fetch une URL utilisateur arbitraire. `_download_telegram_file` est scopé à `api.telegram.org` |

---

## 3. Niveau de maturité : **L3-** / L5

- **L1 (MVP fragile)** : dépassé — les fondamentaux sont en place (RLS, webhooks signés, secrets en env var, désérialisation restreinte)
- **L2 (fonctionnel)** : dépassé — audit sécurité mars 2026 a fermé 60+ trous, lessons 11/17/18/19/20/27/36/37/41/42/43/58 toutes adressées en grande partie
- **L3 (solide, commercial)** : atteint à ~85%
  - Ce qui manque pour L3 plein : `extra="forbid"` Pydantic, dernier `detail=str(e)`, audit log cohérent sur tous les endpoints admin, rate limit sur les 34 endpoints sans décorateur
- **L4 (best-in-class)** : non — pas de CSP, pas de MFA admin, pas de secrets rotation automatisée, pas de `pip-audit`/SAST dans la CI, pas de détection d'anomalie (brute-force, credential stuffing)
- **L5 (état de l'art)** : hors portée actuelle (SOC 2, bug bounty, WAF managé, pen-tests récurrents)

**Note : L3-** — une startup SaaS sérieuse en pré-certification ; prête pour des utilisateurs payants mais pas auditable Drata/Vanta sans effort.

---

## 4. Benchmark vs. standard industrie

| Critère | ProbaLab | SaaS startup Drata-level (L4) | État de l'art (L5) |
|---|---|---|---|
| Secrets rotation | Manuelle via env Railway | Vault/Doppler + rotation auto 90j | HSM + rotation continue |
| Webhooks signés | Stripe ✓, Telegram ✓ | Tous webhooks + idempotency keys DB | Mutual TLS + replay cache Redis |
| Rate limiting | Partiel, flat IP | Par utilisateur authentifié + tier | Adaptive/ML-based (WAF) |
| RLS / authz | RLS Postgres ✓ + trigger escalade | RLS + ABAC/OPA | ABAC + Zanzibar-like |
| SAST/DAST | Absent | Bandit + Snyk/Dependabot CI | + Semgrep custom rules + pen test trimestriel |
| MFA admin | **Absent** (Supabase JWT basique) | MFA obligatoire + session recording | + hardware keys (YubiKey) |
| Audit log | Partiel (1 fonction) | Structuré, immuable, 7 ans | SIEM temps réel + SOC |
| CSP / COOP / COEP | **Absent** | CSP strict nonce + COOP same-origin | CSP Level 3 + Trusted Types |
| Pen test | **Jamais** | Annuel | Trimestriel + bug bounty |
| Response headers | 5/10 | 8/10 | 10/10 (Permissions-Policy, etc.) |

ProbaLab est **au-dessus** de la moyenne d'une startup side-project (qui oublierait RLS et sign webhooks) et **en dessous** d'une SaaS série A prête pour la compliance.

---

## 5. Gaps pour passer au niveau supérieur

### P0 (bloquant L3 plein — 1 à 3 jours)

1. **Ajouter `model_config = ConfigDict(extra="forbid")` à tous les modèles de `api/schemas.py`**
   - Lancer la suite de tests → corriger les appels qui envoient des extras
   - Conforme à Phase 3.2 todo.md

2. **Supprimer le `detail=str(e)` de `api/routers/players.py:162`**
   - Remplacer par `logger.exception(...)` + `raise HTTPException(500, detail="Internal server error")`

3. **Fermer `/api/admin/update-scores` à tout appel sans auth**
   - Soit exiger CRON_SECRET en Bearer, soit header interne `X-Internal-Cron-Token`
   - Ne pas se reposer sur "réseau interne Railway" qui n'est pas une barrière de sécurité

4. **Uniformiser l'audit log admin**
   - Appeler `logger.info("ADMIN_AUTH_OK: endpoint=%s source=%s user=%s", ...)` dans `_require_admin` (admin.py) et `verify_trigger_auth` (trigger.py)
   - Créer un decorator `@audit_admin_action("run-pipeline")` qui log avant/après

### P1 (L3 → L4 — 1 à 2 semaines)

5. **Rate limiting différencié par tier** (Phase 3.3 todo.md)
   - `key_func` custom lisant le JWT → tier (free / premium / admin)
   - Appliquer `@_rate_limit_tiered()` sur tous les endpoints publics (minimum : tous les `/api/predictions`, `/api/best-bets`, `/api/performance`)

6. **Ajouter `Content-Security-Policy`** au `SecurityHeadersMiddleware`
   - Même simple : `default-src 'self'; connect-src 'self' https://*.supabase.co https://api.stripe.com`
   - Ajouter `Permissions-Policy: geolocation=(), microphone=(), camera=()`

7. **Procédure rotation CRON_SECRET** (Phase 3.4 todo.md)
   - Supporter 2 secrets simultanés (`CRON_SECRET` + `CRON_SECRET_PREV`)
   - Runbook dans `tasks/runbook_secret_rotation.md`

8. **Ajouter `pip-audit` + `bandit` dans la CI**
   - Dépendance vulnérable → CI rouge
   - `bandit -r api src` bloquant au niveau HIGH

9. **MFA admin**
   - Activer le TOTP Supabase Auth sur les comptes `role=admin`
   - Exiger `aal2` dans `_require_admin` (vérifier `user.aal` = `aal2`)

10. **Unifier les `RestrictedUnpickler`** dans `src/security/safe_pickle.py` + import partout

### P2 (L4 → L5 — refonte stratégique)

11. Vault pour secrets (Doppler / 1Password Connect)
12. Centralisation logs (Datadog / Axiom / Grafana Loki) + alertes sur pics d'auth fails
13. Pen test externe trimestriel
14. WAF (Cloudflare / Railway natif) devant FastAPI
15. Bug bounty modeste (HackerOne / Intigriti)

---

## 6. Risques identifiés

| # | Risque | Impact | Probabilité | Sévérité |
|---|---|---|---|---|
| R1 | `/api/admin/update-scores` exploité sans auth pour DoS quota API-Football | Pipeline cassé, quota bouffé | Moyenne | **High** |
| R2 | Fuite de stack trace via `detail=str(e)` sur `/api/players/{id}` | Info disclosure (schema DB) | Faible | Medium |
| R3 | Absence d'audit log sur actions admin (delete-user, update-role, run-pipeline) | Incident impossible à investiguer | Certaine (déjà le cas) | **High** |
| R4 | Rate limit absent sur 34/40 endpoints POST/DELETE/PUT | DoS applicatif, abus API | Moyenne | Medium |
| R5 | Pas de CSP → XSS via injection dans un champ utilisateur (expert-picks Telegram note) | XSS dans dashboard admin | Faible | Medium |
| R6 | Pas de MFA sur comptes admin (JWT Supabase seul) | Compromission compte admin → DB complète | Faible | **High** |
| R7 | `_pending_picks` Telegram perdu au redémarrage | UX dégradée + possible replay si attaquant timing Rails | Faible | Low |
| R8 | Pas de `pip-audit` → CVE dans dépendance non détectée | RCE potentielle via lib vulnérable | Moyenne | **High** |
| R9 | CORS `allow_credentials=True` — si `ALLOWED_ORIGINS` mal rempli avec `null` ou `*` | Bypass CORS | Faible | Medium |
| R10 | 5 RestrictedUnpickler divergents | Nouvelle whitelist oubliée un jour → désérialisation unsafe | Moyenne | Medium |

---

## 7. Recommandations stratégiques

### Court terme (2 semaines)
1. Faire les 4 fixes P0 ci-dessus — tout est scriptable en 1 à 3 jours par un dev senior
2. Poser `bandit` + `pip-audit` dans la CI — 2h de travail, bénéfice permanent
3. Rédiger un threat model léger (STRIDE sur Stripe webhook + flux admin + Telegram) — documenter dans `docs/security/threat_model.md`

### Moyen terme (1-2 mois)
4. Rate limiting tiered (Phase 3.3 todo.md) — le modèle premium a besoin de garanties différentes des free
5. CSP + Permissions-Policy (middleware existant, 20 LOC à ajouter)
6. MFA admin + audit log structuré JSON vers un stream (Axiom / Datadog / Logflare)
7. Procédure rotation des 6 secrets critiques (CRON_SECRET, TELEGRAM_WEBHOOK_SECRET, STRIPE_WEBHOOK_SECRET, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY, API_FOOTBALL_KEY) — documenter + automatiser

### Long terme (6 mois, si le pivot "Probas Sportives" réussit)
8. SOC 2 Type I préparatoire (Drata / Vanta) — RLS + audit log structuré sont déjà des pré-requis posés
9. Pen test externe avant chaque release majeure
10. Bug bounty modeste ($5-20k budget annuel) dès que >10k users payants

### Principe directeur
La sécurité de ProbaLab est **clairement au-dessus de la moyenne d'un side-project de paris sportifs** (la plupart n'ont pas RLS, pas d'idempotence webhook, pas de désérialisation restreinte). Elle est **clairement en dessous d'une SaaS série A compliance-ready**. La bascule vers L4 est économiquement pertinente **seulement si** le pivot attire un volume d'utilisateurs payants significatif — sinon, rester L3+ et fermer les P0 suffit.

---

## 8. Liens internes
- `ProbaLab/tasks/lessons.md` — 68 leçons, dont 11-20, 27, 34, 36, 37, 41, 42, 43, 58 couvrent la sécurité
- `ProbaLab/tasks/todo.md` — Phase 3 "Sécurité API" (3.1 à 3.6), actuellement non démarrée
- `ProbaLab/migrations/020_enable_rls_all_tables.sql` — fondation RLS
- `ProbaLab/migrations/010_security_fixes.sql` — trigger anti-escalade + idempotence
- `ProbaLab/migrations/019_atomic_place_bet.sql` — RPC atomique bankroll
- Annexe `05_architecture_backend.md` — middleware stack, routers organisation
- Annexe `08_tests_cicd.md` — baseline sécurité CI (SAST/dependency audit absents)
