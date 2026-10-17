# Private AI Document Assistant

Upload PDFs, search them, and ask questions with verifiable citations.

**Status: Stage 1 (foundation) only.** The app currently has a FastAPI backend with a health
endpoint, a React + TypeScript frontend that displays backend status, configuration, and tests.
There is no PDF handling, search, or AI yet. See [docs/DECISIONS.md](docs/DECISIONS.md) for why
the stack looks the way it does.

## Requirements

- Python 3.11+
- Node.js 20+ and npm
- Git

On Arch Linux:

```sh
sudo pacman -S --needed git python nodejs npm
```

No database server, API key, or GPU is needed at this stage.

## Setup

From the repository root:

```sh
# Backend
python -m venv backend/.venv
source backend/.venv/bin/activate
pip install -e "backend[dev]"

# Frontend
cd frontend && npm install && cd ..

# Optional: local configuration (defaults work without it)
cp .env.example .env
```

## Run (two terminals)

```sh
# Terminal 1: backend on http://127.0.0.1:8000
source backend/.venv/bin/activate
cd backend && uvicorn app.main:app --reload

# Terminal 2: frontend on http://localhost:5173 (proxies /api to the backend)
cd frontend && npm run dev
```

Check the backend directly: `curl http://127.0.0.1:8000/api/health`

## Test and check

```sh
# Backend (virtualenv active)
cd backend
pytest
ruff check .
ruff format --check .
mypy

# Frontend
cd frontend
npm test
npm run typecheck
npm run build
```

## Configuration

Settings are read from environment variables prefixed `DOCASSIST_`, or from a `.env` file in
the repository root. See `.env.example`. Never commit `.env`.

## Layout

```
backend/    FastAPI app (app/) and pytest tests (tests/)
frontend/   React + TypeScript + Vite app, Vitest tests
docs/       Design decisions
```

## Known limitations (Stage 1)

- No PDF upload, search, or AI features yet.
- No frontend linter (ESLint) yet; type checking is via `tsc`.
- No CI workflow yet.
- Dependency versions are lower bounds (backend) and caret ranges (frontend); lockfiles are
  generated on first install and should then be committed.
