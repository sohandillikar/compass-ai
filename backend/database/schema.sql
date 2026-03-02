CREATE TABLE public.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE
);

CREATE TABLE public.professors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name TEXT NOT NULL,
    department_id UUID REFERENCES public.departments(id) ON DELETE SET NULL,
    overall_rating NUMERIC(2,1),
    difficulty_rating NUMERIC(2,1),
    would_take_again_percentage INTEGER,
    profile_url TEXT
);

CREATE TABLE public.reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    professor_id UUID NOT NULL REFERENCES public.professors(id) ON DELETE CASCADE,
    rating INTEGER,
    difficulty INTEGER,
    comment TEXT,
    review_date DATE,
    course TEXT,
    tags TEXT[]
);
