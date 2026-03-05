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

-- Active RLS and allow read access
ALTER TABLE public.ai_learnings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access to active learnings"
ON public.ai_learnings
FOR SELECT
USING (is_active = TRUE);

-- Create index for faster filtering by sport
CREATE INDEX idx_ai_learnings_sport ON public.ai_learnings(sport, is_active);
