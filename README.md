# Private AI Document Assistant

Upload PDFs, search them, and ask questions with verifiable citations.

**Status: Stage 2 (PDF management).** You can upload PDFs, see their processing status, list
them, and delete them. Text is extracted page by page and stored. There is no search or AI yet. See [docs/DECISIONS.md](docs/DECISIONS.md) for why
the stack looks the way it does.

## Requirements

- Python 3.11+
- Node.js 20+ and npm
- Git

On Arch Linux:

```sh
sudo pacman -S --needed git python nodejs npm
```

No database server, API key, or GPU is needed. SQLite is used by default.

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

# Create the database tables (re-run after pulling changes that add migrations)
source backend/.venv/bin/activate
cd backend && alembic upgrade head && cd ..
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

## API

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Health check |
| `POST /api/documents` | Upload a PDF (multipart field `file`) |
| `GET /api/documents` | List documents, newest first |
| `GET /api/documents/{id}` | One document |
| `DELETE /api/documents/{id}` | Delete a document, its extracted text, and its stored file |

Interactive docs: http://127.0.0.1:8000/docs while the backend is running.

Document statuses: `ready` (text extracted), `needs_ocr` (no text layer found, probably a scan;
OCR is not supported yet), `failed` (corrupted, encrypted, too many pages, or no pages; the
reason is in `error_message`).

## Configuration

Settings are read from environment variables prefixed `DOCASSIST_`, or from a `.env` file in
the repository root. See `.env.example`. Never commit `.env`. Uploaded PDFs and the SQLite
database live in `data/` (gitignored) unless `DOCASSIST_DATA_DIR` is set.

## Layout

```
backend/    FastAPI app (app/), Alembic migrations (migrations/), pytest tests (tests/)
frontend/   React + TypeScript + Vite app, Vitest tests
docs/       Design decisions
```

## Known limitations (Stage 2)

- No search or AI features yet.
- No authentication: anyone who can reach the server can see and delete every document. Run it
  locally only until access control is added (Stage 6).
- The upload size limit is enforced while saving, but the web framework has already received
  the whole request by then. A request-size limit (for example at a reverse proxy) is needed
  before exposing the app to a network.
- PDFs are processed inside the upload request, so a large PDF makes the request wait.
- A PDF counts as "needs OCR" only if *no* page has extractable text. A scan that already has a
  poor-quality text layer is accepted as `ready`; pages without text are counted but not
  OCR'd.
- Password-protected PDFs are rejected rather than decrypted.
- Duplicate uploads of the same file are not detected.
- No frontend linter (ESLint) yet; type checking is via `tsc`.
- No CI workflow yet.
- Dependency versions are lower bounds (backend) and caret ranges (frontend); lockfiles are
  generated on first install and should then be committed.
