-- Ajout d'une colonne JSONB pour stocker les features extraites par l'IA (Gemini)
-- Cela permet d'ajouter de nouveaux scores sans modifier le schéma de la table.
ALTER TABLE fixtures ADD COLUMN IF NOT EXISTS ai_features jsonb DEFAULT '{}'::jsonb;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS ai_features jsonb DEFAULT '{}'::jsonb;
