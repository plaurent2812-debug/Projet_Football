# ⚽ Football IA — Google Sheet Setup

## Mise en place (5 minutes)

### 1. Créer le Google Sheet
- Va sur [sheets.google.com](https://sheets.google.com)
- Crée un nouveau classeur
- Nomme-le **"Football IA — Prédictions"**

### 2. Installer le script
- Dans le menu : **Extensions → Apps Script**
- Supprime tout le contenu par défaut dans l'éditeur
- Copie-colle **tout** le contenu de `Code.js`
- Clique sur **💾 Enregistrer** (ou Ctrl+S)
- Ferme l'onglet Apps Script

### 3. Recharger le Sheet
- Rafraîchis la page du Google Sheet (F5)
- Attends 2-3 secondes : un nouveau menu **⚽ Football IA** apparaît dans la barre de menu

### 4. Configurer les clés API
- Clique sur **⚽ Football IA → ⚙️ Configurer les clés API**
- (Google demandera une autorisation la première fois → accepte)
- Renseigne tes 4 clés :
  - `SUPABASE_URL` → depuis ton .env
  - `SUPABASE_KEY` → depuis ton .env
  - `API_FOOTBALL_KEY` → depuis ton .env
  - `ANTHROPIC_API_KEY` → depuis ton .env
- Clique **Sauvegarder**

### 5. C'est prêt !

## Utilisation

| Bouton | Action |
|--------|--------|
| 🚀 **Tout lancer** | Import + Analyse IA + Affichage (tout en un clic) |
| 📥 **Importer les matchs** | Récupère la prochaine journée de chaque championnat |
| 🧠 **Lancer l'analyse IA** | Analyse tous les matchs non encore prédits |
| 📊 **Rafraîchir l'affichage** | Recharge les données et reformate le tableau |
| ⚙️ **Configurer** | Modifier les clés API |
