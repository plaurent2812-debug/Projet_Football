-- ═══════════════════════════════════════════════════════════════════
--  018 — Gemini Embedding 2 / pgvector setup
--  ALREADY EXECUTED on 2026-03-11.
--  Safe to re-run (all operations are idempotent).
-- ═══════════════════════════════════════════════════════════════════

-- 0. Create ai_learnings table if not present
CREATE TABLE IF NOT EXISTS public.ai_learnings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sport TEXT NOT NULL,
    context_tags JSONB DEFAULT '[]'::jsonb,
    learning_text TEXT NOT NULL,
    confidence INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    source_match_id BIGINT
);

ALTER TABLE public.ai_learnings ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'ai_learnings' AND policyname = 'Allow public read access to active learnings'
    ) THEN
        CREATE POLICY "Allow public read access to active learnings"
        ON public.ai_learnings FOR SELECT USING (is_active = TRUE);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_ai_learnings_sport ON public.ai_learnings(sport, is_active);

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add embedding columns (768-dim Matryoshka)
ALTER TABLE public.ai_learnings
  ADD COLUMN IF NOT EXISTS embedding vector(768);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'predictions') THEN
        EXECUTE 'ALTER TABLE public.predictions ADD COLUMN IF NOT EXISTS embedding vector(768)';
    ELSE
        RAISE NOTICE 'Table predictions does not exist — skipping embedding column.';
    END IF;
END $$;

-- 3. Indexes for fast similarity search
CREATE INDEX IF NOT EXISTS idx_ai_learnings_embedding
  ON public.ai_learnings
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 10);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'predictions') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_predictions_embedding') THEN
            EXECUTE 'CREATE INDEX idx_predictions_embedding ON public.predictions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)';
        END IF;
    END IF;
END $$;

-- 4. RPC: Semantic search on ai_learnings
CREATE OR REPLACE FUNCTION match_learnings(
  query_embedding vector(768),
  match_sport text,
  match_limit int DEFAULT 5,
  match_threshold float DEFAULT 0.3
)
RETURNS TABLE (id uuid, learning_text text, context_tags jsonb, similarity float)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT al.id, al.learning_text, al.context_tags,
    (1 - (al.embedding <=> query_embedding))::float AS similarity
  FROM public.ai_learnings al
  WHERE al.is_active = TRUE AND al.sport = match_sport AND al.embedding IS NOT NULL
    AND (1 - (al.embedding <=> query_embedding)) >= match_threshold
  ORDER BY al.embedding <=> query_embedding
  LIMIT match_limit;
END;
$$;

-- 5. RPC: Semantic search on predictions
CREATE OR REPLACE FUNCTION match_predictions(
  query_embedding vector(768),
  match_limit int DEFAULT 10,
  match_threshold float DEFAULT 0.3
)
RETURNS TABLE (id uuid, fixture_id uuid, analysis_text text, proba_home float, proba_draw float, proba_away float, similarity float)
LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'predictions') THEN
    RETURN;
  END IF;
  RETURN QUERY
  SELECT p.id, p.fixture_id, p.analysis_text, p.proba_home::float, p.proba_draw::float, p.proba_away::float,
    (1 - (p.embedding <=> query_embedding))::float AS similarity
  FROM public.predictions p
  WHERE p.embedding IS NOT NULL
    AND (1 - (p.embedding <=> query_embedding)) >= match_threshold
  ORDER BY p.embedding <=> query_embedding
  LIMIT match_limit;
END;
$$;