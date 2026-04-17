#!/bin/bash
# ⚽ Football IA — Lancement complet (Import + Analyse)
# Double-cliquez sur ce fichier pour lancer le pipeline

clear
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ⚽ FOOTBALL IA — Lancement complet             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "${BASH_SOURCE[0]}")"

# Activer l'environnement virtuel si présent
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Lancer le pipeline complet
python3 run_pipeline.py full

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  ✅ Terminé ! Tu peux rafraîchir l'affichage dans Sheets"
echo "     (menu ⚽ Football IA → ③ Rafraîchir l'affichage)"
echo "══════════════════════════════════════════════════════════"
echo ""
read -p "Appuie sur Entrée pour fermer..."
