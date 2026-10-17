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
(Not yet used in Stage 1.)

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
