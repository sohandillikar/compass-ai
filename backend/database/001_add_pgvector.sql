-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to reviews (1536 dims = OpenAI text-embedding-3-small)
ALTER TABLE public.reviews
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- IVFFlat index for fast cosine similarity lookups
CREATE INDEX IF NOT EXISTS reviews_embedding_idx
  ON public.reviews
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- RPC function used by the application to find semantically similar reviews
CREATE OR REPLACE FUNCTION match_reviews(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id uuid,
  professor_id uuid,
  rating int,
  difficulty int,
  comment text,
  course text,
  tags text[],
  similarity float
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    r.id, r.professor_id, r.rating, r.difficulty,
    r.comment, r.course, r.tags,
    1 - (r.embedding <=> query_embedding) AS similarity
  FROM public.reviews r
  WHERE r.embedding IS NOT NULL
    AND 1 - (r.embedding <=> query_embedding) > match_threshold
  ORDER BY r.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
