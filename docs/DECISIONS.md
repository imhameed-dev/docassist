# Engineering decisions

Short records of why things are the way they are. Add new entries at the bottom.

## 1. FastAPI + React/TypeScript (Vite)
Python has the strongest PDF and AI ecosystem; FastAPI gives typed request/response models and
automatic OpenAPI docs with little code. Vite is light enough for a 4 GB machine.

## 2. SQLite by default, PostgreSQL optional
A single-user portfolio app on a low-memory laptop gains nothing from a database server idling
in RAM. The database is configured by one URL (`DOCASSIST_DATABASE_URL`) and will be accessed
through SQLAlchemy, so switching to PostgreSQL later is a configuration change. SQLite's
built-in FTS5 full-text search also lets Stage 3 retrieval work with no extra infrastructure.
The default database file lives in the data directory, resolved from the repository root
rather than the working directory.

## 3. Typed settings via pydantic-settings
Configuration comes from `DOCASSIST_*` environment variables or a root `.env`, validated at
startup (an invalid `environment` fails fast). The `.env` path is resolved from the source file,
not the working directory. A test checks `.env.example` stays in sync with the real settings.

## 4. Dev-server proxy instead of CORS
In development Vite proxies `/api` to FastAPI, so the browser sees one origin and no CORS
rules are needed. Avoiding permissive CORS now means there is nothing to tighten later.

## 5. Health endpoint exposes no internals
`/api/health` returns only status, app name, environment and version. A test asserts that the
database URL is not leaked, because connection strings can contain credentials.

## 6. pypdf for text extraction
Pure Python (no native build, light on a 4 GB machine) and permissively licensed. PyMuPDF
extracts better and faster, but is heavier and AGPL-licensed, which would complicate a public
portfolio project. Revisit only if the Stage 7 evaluation shows extraction quality is the
bottleneck.

## 7. Store page text and keep the original PDF
Page-by-page text in the database is what makes page-number citations possible later. The
original file is kept (status `needs_ocr` and `ready` only) so OCR or re-extraction can be added
without asking the user to upload again. Files that cannot be processed are deleted immediately.

## 8. Server-generated ids; client filenames are display-only
Each document gets a random 32-hex id that is also its on-disk name. The uploaded filename is
cleaned and stored for display but never used to build a path, which closes off path traversal
by construction. Path parameters are validated against the id format, and the storage layer
re-checks it. Uploads are checked by their `%PDF-` signature, not by extension or the
client-declared content type.

## 9. Process synchronously inside the upload request
With a page cap this is simple and reliable. A `status` column already exists, so moving to
background processing later is a contained change. The cost: a large PDF makes the upload
request wait.

## 10. Alembic migrations, with a test tying them to the models
The schema is created by `alembic upgrade head`. A test builds a database from the migrations
and fails if it differs from the SQLAlchemy models, so the two cannot drift silently.

## 11. No authentication yet
Stage 2 is single-user and local. This is recorded as a limitation in the README; access
control and a request-size limit belong to Stage 6.
