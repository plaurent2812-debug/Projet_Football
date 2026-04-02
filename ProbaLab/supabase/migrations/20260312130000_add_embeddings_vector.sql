-- ================================================================
-- Migration: Embeddings vector support
-- - Enable pgvector extension
-- - Add embedding vector(768) to predictions and ai_learnings
-- - Create match_predictions and match_learnings RPC functions
-- ================================================================

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to predictions
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Add embedding column to ai_learnings
ALTER TABLE ai_learnings ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Index for fast similarity search on predictions
CREATE INDEX IF NOT EXISTS predictions_embedding_idx
    ON predictions USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index for fast similarity search on ai_learnings
CREATE INDEX IF NOT EXISTS ai_learnings_embedding_idx
    ON ai_learnings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- RPC: match_predictions — semantic search over predictions
CREATE OR REPLACE FUNCTION match_predictions(
    query_embedding vector(768),
    match_limit int DEFAULT 10,
    match_threshold float DEFAULT 0.3
)
RETURNS TABLE (
    id uuid,
    fixture_id bigint,
    analysis_text text,
    proba_home int,
    proba_draw int,
    proba_away int,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.fixture_id,
        p.analysis_text,
        p.proba_home,
        p.proba_draw,
        p.proba_away,
        1 - (p.embedding <=> query_embedding) AS similarity
    FROM predictions p
    WHERE p.embedding IS NOT NULL
      AND 1 - (p.embedding <=> query_embedding) > match_threshold
    ORDER BY p.embedding <=> query_embedding
    LIMIT match_limit;
END;
$$;

-- RPC: match_learnings — semantic search over ai_learnings
CREATE OR REPLACE FUNCTION match_learnings(
    query_embedding vector(768),
    match_sport text DEFAULT 'football',
    match_limit int DEFAULT 10,
    match_threshold float DEFAULT 0.3
)
RETURNS TABLE (
    id uuid,
    learning_text text,
    context_tags text[],
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id,
        l.learning_text,
        l.context_tags,
        1 - (l.embedding <=> query_embedding) AS similarity
    FROM ai_learnings l
    WHERE l.embedding IS NOT NULL
      AND l.sport = match_sport
      AND 1 - (l.embedding <=> query_embedding) > match_threshold
    ORDER BY l.embedding <=> query_embedding
    LIMIT match_limit;
END;
$$;
