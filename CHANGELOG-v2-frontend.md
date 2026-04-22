# CHANGELOG V2 Frontend Refonte

## Release V2 — 2026-04-22

Refonte complète UX/UI frontend ProbaLab. Pitch produit pivote de "combos Safe/Fun/Jackpot" vers "probabilités calibrées + value bets ≥5% + track record CLV public".

### Nouveautés

- **Design system Fintech** : palette émeraude sur fond nuit, typographie Inter tabulaire, composants denses data-first
- **Pages refondues** : Accueil (landing visitor + dashboard connecté), Matchs (filtres avancés), Fiche match (2 colonnes sticky desktop, ordre décision rapide mobile), Premium (track record LIVE), Compte (Profil / Abonnement / Bankroll / Notifications)
- **Bankroll tracker** : KPIs 5 tiles, courbe P&L 90j, ROI par marché, table des paris avec filtres, modals Add/Settings
- **Rules builder notifications** : composable 1-3 conditions AND/OR, 6 types (edge_min, league_in, sport, confidence, kickoff_within, bankroll_drawdown), 3 canaux (Telegram, Email, Push)
- **Track record public LIVE** : CLV vs Pinnacle, ROI 90j, Brier, courbe ROI cumulée — différenciateur vs concurrence
- **Safe du jour gratuit** : pronostic quotidien curated cote 1.80-2.20
- **Service Worker push** : notifications natives navigateur

### Backend

- 10 nouveaux endpoints `/api/v2/*` (safe-pick, matches consolidé foot+NHL, odds comparison, bankroll ROI par marché, notifications rules CRUD, track-record live)
- 2 migrations SQL : `user_bankroll_settings`, `notification_rules` (RLS strict)
- Redirects 301 pour anciennes URLs (`/paris-du-soir`, `/football`, `/nhl`, `/watchlist`, `/hero-showcase`)

### Tests

- Frontend : 738 tests unitaires (Vitest + Testing Library + jest-axe)
- Backend : 823 tests pytest
- E2E : 3 specs Playwright (visitor-to-trial, browse-to-premium-cta, premium-rule-alert)

### Migration

Le cutover se fait via flag `VITE_FRONTEND_V2=true` sur Railway. Les anciennes pages legacy restent présentes en code pour permettre un rollback instantané (flag à `false`).

**Task 12 (cleanup)** : suppression définitive des pages legacy (`HomePage.tsx`, `Dashboard.tsx`, `ParisDuSoir.tsx`, `MatchDetail.tsx`, `WatchlistPage.tsx`, `HeroShowcase.tsx`, `Premium.tsx`) reportée à J+7 après stabilisation en prod, dans une PR séparée.

## Procédure de rollback

En cas de bug critique en prod sur la V2, rollback en **< 3 minutes** :

### Option A — Flag feature (instantané, pas de redeploy)

1. Aller dans Railway → Service `ProbaLab-Web` → Variables
2. Passer `VITE_FRONTEND_V2` de `true` à `false`
3. Railway redéploie automatiquement (2-3 min)
4. L'app repasse en mode legacy sans perte de données

### Option B — Redeploy previous version

1. Railway → Service `ProbaLab-Web` → Deployments
2. Click sur le déploiement précédent (V1 legacy avant merge V2)
3. Menu `...` → Redeploy
4. ~2 min

**Attention** : si les migrations SQL V2 (`054`, `056`) posent problème, ces tables peuvent être désactivées sans impact sur la V1 (elles ne sont pas référencées par le code legacy). En dernier recours : `DROP TABLE user_bankroll_settings CASCADE; DROP TABLE notification_rules CASCADE;` via Supabase Studio.

### Monitoring post-cutover

- Vérifier les logs Railway pendant les 30 premières minutes
- Vérifier le rate d'erreur 5xx sur `/api/v2/*` (doit être < 1%)
- Vérifier que les requêtes `/api/predictions`, `/api/best-bets` continuent à fonctionner (legacy utilisés en fallback par certaines pages)
- Test manuel : inscription, login, parcours matchs, fiche détail, page premium

## Smoke test checklist post-activation

- [ ] Landing `/` charge sans erreur console en mode non-connecté
- [ ] `/matchs` affiche les matchs du jour (API `/api/v2/matches` répond)
- [ ] Click sur un match → fiche détaillée rendue
- [ ] `/premium` affiche les 4 KPIs track record live
- [ ] Login fonctionne (page legacy conservée, branchée sur Supabase Auth)
- [ ] Trial banner visible pour user free connecté
- [ ] `/compte/bankroll` charge les stats (peut être vide si user new)
- [ ] `/compte/notifications` permet de créer une règle → vérifier qu'elle apparaît dans la liste
- [ ] Redirect `/paris-du-soir` → `/matchs?signal=value` (HTTP 301)
- [ ] `/admin` et `/performance` accessibles pour user admin
- [ ] Zero console error en navigation courante
