#!/bin/bash
# ==============================================================================
# Script de génération des types TypeScript Supabase (Phase 3)
# ==============================================================================

# Assurez-vous d'avoir installé le CLI Supabase globalement ou via npx
# npm install -g supabase

PROJECT_REF="yskpqdnidxojoclmqcxn"

echo "Génération des types pour le projet $PROJECT_REF..."

npx supabase gen types typescript --project-id "$PROJECT_REF" > src/types/supabase.ts

if [ $? -eq 0 ]; then
    echo "✅ Types générés avec succès dans src/types/supabase.ts"
else
    echo "❌ Erreur lors de la génération. Avez-vous exécuté 'npx supabase login' avec votre Access Token ?"
fi
