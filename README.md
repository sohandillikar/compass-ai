# Compass AI

## Product Vision

**Compass AI** is a conversational web agent that helps UC Davis students make informed decisions about professor selection during course planning. Students can chat to discover, compare, and get personalized recommendations for professors based on Rate My Professor data.

## CLI (local)

This repo also includes a simple CLI agent (LangChain + OpenAI) that queries the Supabase database and uses fuzzy matching for professor / department / course names.

### Setup

1. Install dependencies:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Create a `.env` file in `backend/` with:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (or `SUPABASE_SERVICE_KEY` / `SUPABASE_KEY`)
- `OPENAI_API_KEY`
- Optional: `OPENAI_MODEL` (defaults to `gpt-4.1-mini`)

### Run

Interactive mode:

```bash
cd backend
python -m compass_cli.cli
```

Single question:

```bash
cd backend
python -m compass_cli.cli --once "Who's the best professor for ECS 36C?"
```

## Web App (FastAPI + Next.js)

The backend exposes a FastAPI chat API, and the frontend provides a chat interface.

### Backend (FastAPI)

1. From `backend/`, install dependencies and ensure `.env` is configured (same as CLI).
2. Run the server:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)

1. From `frontend/`, install dependencies and optionally copy `.env.local.example` to `.env.local`:

```bash
cd frontend
pnpm install
cp .env.local.example .env.local  # optional; defaults to http://localhost:8000
```

2. Run the dev server:

```bash
pnpm dev
```

3. Open http://localhost:3000 to use the chat interface.

### Example Requests

The following is a list of example requests that Compass can handle:

- "Who's the best professor for ECS 36C?"
- "I need to take a computer science elective, who should I take it with?"
- "I want an easy A for my GE requirement"
- "Who are the top-rated biology professors?"
- "I learn best from professors who use lots of real-world examples"
- "Which math professor has the lightest workload?"
- "Tell me about Professor Alexander Aue"
- "I want a challenging upper-division course, who should I look for?"
- "Are there any really engaging lecturers in the psychology department?"
- "Who teaches MAT 21A and how are they rated?"
- "I need a professor who's good at explaining complex topics clearly"

## Branching strategy

1. Create an issue describing what you are gonna do (if I haven't already).
2. Create a new branch called `name/brief-description-[ISSUE#]`.
   - Example: `sohan/define-end-product-13`
3. Make your changes with detailed commit messages
4. Create a PR with a descriptive title and description
5. Apply and respond to feedback
