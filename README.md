# AI Codebase Intelligence

Explore a repository with architecture graphs, code search, dependency analysis,
code health reports, and AI explanations. The app uses a React frontend, FastAPI,
PostgreSQL, and Qdrant.

## Existing Render backend and Vercel frontend

Configure the deployed backend through its Render Environment settings. Local
`.env` files are ignored by Git and are not uploaded by a Git-based deploy.
Keep the existing hosted `DATABASE_URL`, `QDRANT_URL`, `QDRANT_API_KEY`, and
`OPENAI_API_KEY` values.

Leave `REPOS_DIR` unset to use temporary checkout storage (`/tmp/aci-repos` on
Render). This directory holds imported repositories, not the deployed app source.
Without a persistent disk, checkouts are lost on restart or redeploy; import the
repository again when source files are needed. If you attach a persistent disk,
set `REPOS_DIR` to a directory under that disk's mount path.

For a native Python backend, use root directory `backend`, build command
`pip install -r requirements.txt`, and start command
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
The backend Dockerfile also respects Render's `PORT` environment variable.

Set these values in the corresponding hosting dashboard, then redeploy:

| Service | Environment variable | Value |
| --- | --- | --- |
| Render backend | `CORS_ALLOWED_ORIGINS` | `https://ai-codebase-intelligence.vercel.app` |
| Vercel frontend | `VITE_API_BASE_URL` | `https://ai-codebase-intelligence-t90m.onrender.com` |

Use origins without a trailing slash. The frontend API URL is included at build
time, so changing it requires a new frontend build. The checked-in `.env.example`
files use these deployment URLs; actual `.env` files remain untracked.
For local development, set `VITE_API_BASE_URL=http://localhost:8000` and
`CORS_ALLOWED_ORIGINS=http://localhost:5173`. The Compose frontend uses its `/api`
proxy and does not require the deployed frontend's origin.

See [Render environment settings](https://render.com/docs/configure-environment-variables)
and [persistent disk behavior](https://render.com/docs/disks).

## Run with Docker locally

1. Start Docker Desktop (Linux containers) or Docker Engine with Compose.
2. Copy the root `.env.example` to `.env` and set `OPENAI_API_KEY` for indexing,
   embeddings, and AI explanations. The Docker setup reads the root `.env`.
3. From this directory run:

   ```sh
   docker compose up --build -d
   ```

4. Open http://localhost:8080. API documentation is available at
   http://localhost:8080/api/docs (the OpenAPI schema is at `/api/openapi.json`).

The frontend proxies API requests and WebSockets to the backend. PostgreSQL,
Qdrant, and repository checkouts use persistent Docker volumes. The database
credentials in Compose are for local development; only the frontend is published,
on the loopback interface. To stop the stack while keeping data, run
`docker compose down`. Inspect startup with `docker compose logs -f backend`.

Validate the configuration without starting containers:

```sh
docker compose config --quiet
```

## Run locally without Docker

Backend (Python 3.11 or later):

```sh
cd backend
python -m venv .venv
# Activate .venv using your shell's activation command.
pip install -r requirements.txt
# Copy .env.example to .env and configure PostgreSQL, Qdrant, and the API key.
uvicorn app.main:app --reload --port 8000
```

Frontend:

```sh
cd frontend
npm ci
# Optionally copy .env.example to .env to change the API URL.
npm run dev
```

## Docker configuration analysis

The indexer recognizes `Dockerfile`, `Dockerfile.*`, `*.dockerfile`, and matching
`Containerfile` names, plus `compose.yaml`, `compose.yml`, `docker-compose.yml`,
and variants such as `compose.override.yaml` or `docker-compose.prod.yml`.

- Dockerfiles produce instruction chunks with source line numbers, build stages,
  base-image dependencies, and external `COPY --from` image references. Continuations,
  comments, escape directives, and heredoc bodies retain their source spans.
- Compose files produce service chunks, images, build settings, ports, and
  `depends_on` relationships. YAML anchors and merge keys are supported.
- Configuration source is retained for search context. Docker files appear in
  architecture graphs and file details, with Docker/YAML syntax highlighting.

Analysis is static: it does not execute instructions, substitute build arguments
or environment variables, merge separate Compose files, or inspect image contents.
Architecture graphs include Docker files as nodes; service dependencies are
available in parsed metadata. Invalid YAML falls back to searchable source text.

Syntax references: [Dockerfile](https://docs.docker.com/reference/dockerfile/) and
[Compose services](https://docs.docker.com/reference/compose-file/services/).

## Checks

```sh
cd backend
python -m unittest discover -s tests -v
```

The existing backend tests load `backend/.env`; configure it as described above.
Tests mock remote operations and do not require a running database.
Frontend checks are `npm run build` and `npm run lint` from `frontend`.
