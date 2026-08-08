# Support Knowledge Miner

Support Knowledge Miner is a local-first MVP for extracting, curating, and exporting reusable support knowledge from historical paired support records. It is intended for an analyst/curator who imports CSV or JSON message-answer pairs, configures local or cloud model providers, creates indexing runs and Cluster-Sets, reviews themes in the Explorer, and exports the filtered Explorer view.

The MVP is explicitly local-only. Do not connect it to production systems, production data, production credentials, or production networks.

## Implemented MVP Workflows

- Sign in with a seeded local user's email, restore a still-valid session after a
  reload in the same browser tab, sign out explicitly, and manage equal-permission
  users.
- Create, open, configure, rename, and delete independent projects.
- Import CSV or JSON records with `ticket_id`, `message_group_id`, `message`, and `answer` fields.
- Persist dataset versions, import logs, skipped-record reasons, and audit actor identity.
- Configure global OpenAI and Ollama provider instances for Embedding and/or LLM
  use; OpenAI API keys are write-only after save.
- Start bounded indexing runs that split long `message` and `answer` texts into
  provider-safe chunks, persist selected-provider embeddings per text variant, and
  expose observable status, progress, metadata, cancellation and safe diagnostics.
- Generate saved Cluster-Sets with HDBSCAN or bounded Agglomerative clustering
  from persisted vectors, including vector basis, lineage, outlier, membership,
  parameter, model, optional LLM summary and source traceability.
- Review Cluster-Sets in a table-first Explorer with search/filter, category
  grouping, deterministic tri-state sorting, source dialog with optional safe
  ticket links, exclude/include controls, mismatch hints and refinement from
  included rows.
- Export the current filtered Explorer table state as CSV or JSON with persisted
  export metadata; raw source-dialog texts are not implicitly exported.
- Use the top-right app menu and project tabs to reach sign-in, global settings,
  project import, indexing, Cluster-Set, Explorer and project-settings workflows.

The durable product behavior is specified in `docs/specifications/support-knowledge-miner-mvp1.md`.

## Import File Formats

The import accepts an uncompressed UTF-8 `.csv` or `.json` file through and
including 512 MiB (536,870,912 bytes). The browser sends the selected file directly;
the backend independently counts the received bytes, stores them temporarily on the
local filesystem, parses the file in two bounded passes, and removes the temporary
file after every outcome. Every record represents one
already-paired customer message and support answer and requires these fields:
`ticket_id`, `message_group_id`, `message`, and `answer`.

At most two upload/import operations run concurrently in one backend process.
Additional attempts receive HTTP 503 with a retry hint. An upload that provides no
new chunk for 30 seconds or exceeds 30 minutes total upload time is aborted and
cleaned up. Database writes are bounded by both record count and a conservative
4 MiB text budget per batch; one individual record may still approach the complete
file limit.

For JSON, the file root must be an array of objects:

```json
[
  {
    "ticket_id": "TICKET-1001",
    "message_group_id": "GROUP-1",
    "message": "Wie kann ich meine Lieferadresse ändern?",
    "answer": "Die Lieferadresse kann vor dem Versand im Kundenkonto geändert werden."
  },
  {
    "ticket_id": "TICKET-1002",
    "message_group_id": "GROUP-2",
    "message": "Wann wird meine Bestellung versendet?",
    "answer": "Der Versand erfolgt üblicherweise innerhalb von zwei Werktagen."
  }
]
```

The equivalent CSV starts with the four required headers:

```csv
ticket_id,message_group_id,message,answer
TICKET-1001,GROUP-1,Wie kann ich meine Lieferadresse ändern?,Die Lieferadresse kann vor dem Versand im Kundenkonto geändert werden.
TICKET-1002,GROUP-2,Wann wird meine Bestellung versendet?,Der Versand erfolgt üblicherweise innerhalb von zwei Werktagen.
```

Field values are trimmed and must not be empty. Invalid individual records are
skipped and recorded in the import log; the import succeeds when at least one
record is valid. A malformed JSON document, a JSON root other than an array, or
missing CSV headers fails the complete import before a dataset version is created.
Duplicate `ticket_id` and `message_group_id` combinations are allowed.
Legacy `ticketid` and `messagegroupid` field names are not accepted.
Complete record counts remain in the import log, but only the first 100 skipped-row
details are persisted and returned. The UI explicitly identifies a truncated detail
list.

The authenticated HTTP contract uses the raw file as the request body, the media
type `text/csv` or `application/json`, and an RFC 5987 filename. It does not use a
JSON wrapper around the file:

```bash
curl --request POST \
  --header "Authorization: Bearer LOCAL_SESSION_TOKEN" \
  --header "Content-Type: application/json" \
  --header "Content-Disposition: attachment; filename*=UTF-8''support.json" \
  --data-binary @support.json \
  http://127.0.0.1:8080/api/projects/PROJECT_ID/imports
```

Unsupported media or filename extensions, oversize input, invalid UTF-8, malformed
CSV/JSON, missing CSV headers, a non-array JSON root, and an import without any
valid records produce distinct German messages.

## Technology

- Backend: Python 3.13, FastAPI, ijson, psycopg, scikit-learn, PostgreSQL with pgvector.
- Frontend: React 19, TypeScript, Vite, Vitest, Testing Library, Oxlint, Prettier.
- Runtime: local Docker Compose PostgreSQL/pgvector; optional Ollama profile.
- Optional GPU clustering acceleration: RAPIDS/cuML via the `gpu-cu12` or
  `gpu-cu13` Python extra.
- Security-sensitive libraries: Argon2id via `argon2-cffi` for passwords and `cryptography` for provider secret encryption.

## Setup

Install dependencies with the repository setup gate:

```bash
./.ai/tools/ci-setup.sh
```

Start the local database when exercising the backend against PostgreSQL:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml up -d postgres
```

The backend uses `SKM_DATABASE_URL` when set. Otherwise, it derives a local
PostgreSQL URL from `POSTGRES_*` values in the process environment or
`deployment/docker/.env` / `.env.example`, matching the Compose database settings.
Set `SKM_DATABASE_URL` only when you need an explicit override:

```bash
export SKM_DATABASE_URL=postgresql://support_knowledge_miner:replace-with-local-dev-password@localhost:5432/support_knowledge_miner
```

Before saving OpenAI keys locally, provide a provider encryption key outside source control:

```bash
export SKM_PROVIDER_ENCRYPTION_KEY="$(uv run --locked python -c 'from backend.providers.secrets import generate_provider_secret_key; print(generate_provider_secret_key())')"
```

Before the first backend start on an empty database, configure the initial local
user. There are no built-in default login credentials:

```bash
export SKM_INITIAL_PASSWORD='replace-with-local-password'
export SKM_INITIAL_EMAIL=owner@example.test
export SKM_INITIAL_FIRST_NAME=Local
export SKM_INITIAL_LAST_NAME=Owner
```

The initial user is created only when the user table is empty. After that, signed-in
users manage further local users in the application. Email is the only stored login
identity and the only public request/response identity field.

See `deployment/docker/README.md` for PostgreSQL and optional Ollama runtime details.

Optional RAPIDS/cuML GPU acceleration is not installed by the default setup,
because the correct package must match the local CUDA major version. Install one
GPU extra only:

```bash
# CUDA 13 runtime/toolkit
uv sync --locked --extra gpu-cu13

# CUDA 12 runtime/toolkit
uv sync --locked --extra gpu-cu12
```

Use `nvidia-smi` and, when available, `nvcc --version` to check the CUDA major
version. For example, when both commands report a CUDA 13 runtime/toolkit, choose
the `gpu-cu13` extra.

## Run

Run the backend locally:

```bash
uv run --locked python -m backend.main
```

The command starts a Uvicorn server on `http://127.0.0.1:8080` and keeps running
until stopped with `Ctrl+C`. On startup it applies local database migrations and
then creates the initial user if the user table is empty and `SKM_INITIAL_*` is
configured.

To ensure the RAPIDS/cuML extra is installed before starting, include the
matching extra in the run command:

```bash
uv run --locked --extra gpu-cu13 python -m backend.main
```

If the Cluster-Set form uses Backend `auto`, the service attempts cuML when it is
importable and falls back to CPU otherwise. Backend `GPU/cuML erzwingen` fails
with a safe accelerator-unavailable error when RAPIDS/cuML is not usable.

For a small, coarse initial Cluster-Set, prefer Agglomerative when you need an exact target count and set `n_clusters` to roughly 8-20.
HDBSCAN cannot guarantee an exact cluster count; for a coarse first pass use Backend `auto`, optional PCA reduction with about 10 dimensions, `min_cluster_size` around 5% of the dataset, `min_samples` around 20, and `cluster_selection_epsilon` around 0.1.
If HDBSCAN still creates too many clusters, double `min_cluster_size` first and then try `cluster_selection_epsilon` around 0.2.

In another terminal, verify the backend with:

```bash
curl http://127.0.0.1:8080/api/health
```

If the command exits during startup, read the Uvicorn traceback in the terminal.
Database password authentication errors usually mean the existing local PostgreSQL
volume was initialized with different `POSTGRES_*` credentials than the current
`.env`; see `deployment/docker/README.md` before deleting any local data.

Run the frontend locally:

```bash
cd frontend
npm run dev
```

The Vite dev server proxies `/api/*` requests to the backend at
`http://127.0.0.1:8080` by default. Start the backend before signing in through
the frontend.

For local model serving, use the optional Ollama Compose profile documented in `deployment/docker/README.md`.
Ollama configuration is restricted to reviewed local hosts:
`localhost`, `127.0.0.1`, `::1`, and `ollama`.
Provider calls use bounded batches and responses without redirects or fallback.
OpenAI indexing and LLM-backed Cluster-Set actions additionally require
`cloud_use_confirmed: true`.
Ollama embedding calls keep the selected model warm for five minutes between
normal analysis batches; OpenAI payloads are unchanged.
Long messages are split at Unicode-safe boundaries into chunks of at most
1,024 UTF-8 bytes. Chunks are produced incrementally, and only the current provider
batch of at most 64 is retained. A byte-weighted mean followed by L2 normalization
combines multiple chunk vectors into exactly one message vector; messages fitting
into one chunk retain the provider vector unchanged. Run metadata records the source byte and chunk
counts without storing source text in diagnostics. Provider failures expose a safe,
actionable reason such as a context-window violation without copying provider
response bodies or message text.
The local backend runs indexing and Cluster-Set work through bounded background
queues. Additional starts are admitted while earlier jobs are queued/running as
long as the local worker queues accept them; cancellation remains available per
active job. Clustering rejects an estimated working set over
512 MiB before loading vectors or writing clusters. Pgvector values are decoded
natively in bounded server-cursor batches into one preallocated contiguous matrix;
the estimate includes the native matrix, estimator matrices, bounded fetch batch,
bounded nearest-neighbor workspace, linkage-specific graph/intermediate structures,
results, mappings, and conservative per-record overhead. Agglomerative rejects a
disconnected neighbor graph before scikit-learn can complete it with unbudgeted
cross-component distances.
Frontend actions preserve server-sanitized API details and otherwise show
action-specific safe fallbacks. Errors are explicitly labeled and announced as
alerts; success, informational, and warning feedback remain distinct. Cluster
Explorer loading is available only for completed Cluster-Sets, and an empty result
explains that clustering must be generated first.

## Verification

Run the full required gate:

```bash
./.ai/tools/verify.sh
```

Focused gates are also available:

```bash
./.ai/tools/format.sh --check && ./.ai/tools/lint.sh && ./.ai/tools/test.sh
./.ai/tools/check-dependencies.sh && ./.ai/tools/security.sh && ./.ai/tools/build.sh
python .ai/tools/check-docs.py
```

UI browser evidence, accessibility checks, and visual regression run against a
tool-managed local Vite instance with synthetic signed-out data:

```bash
./.ai/tools/ui-quality.sh browser
./.ai/tools/ui-quality.sh accessibility
./.ai/tools/ui-quality.sh visual-regression
```

Commands need an active `.ai/work/<change-id>/` directory for evidence. For an
accepted UI change, refresh references with
`npm --prefix frontend run visual:update-baselines` and review the changed PNGs.

To execute fresh and stopped-at-0009 migrations against an isolated local
PostgreSQL container:

```bash
./deployment/docker/scripts/smoke-migrations.sh
```

## Configuration

- `SKM_DATABASE_URL`: optional explicit local PostgreSQL URL. When unset, the backend derives the URL from local `POSTGRES_*` settings. The backend rejects non-local database hosts.
- `SKM_PROVIDER_ENCRYPTION_KEY`: required before saving OpenAI provider API keys.
- `SKM_INITIAL_PASSWORD`, `SKM_INITIAL_EMAIL`: required together to seed the first local user on an empty database. The email address is the login name.
- `SKM_INITIAL_FIRST_NAME`, `SKM_INITIAL_LAST_NAME`: optional initial-user display names.
- `SKM_OLLAMA_BASE_URL`, `SKM_OLLAMA_MODELS`: optional local Ollama endpoint and comma-separated default model allow-list. The backend seeds this provider only when no Ollama provider is configured yet.
- `OLLAMA_KEEP_ALIVE`: optional local Ollama model-residency duration; the Compose
  default and example use `5m`.
- `POSTGRES_*`, `OLLAMA_*`: local Docker Compose settings in `deployment/docker/.env.example`.

Do not commit secrets or local `.env` files.

## Architecture

See `docs/architecture/overview.md` and the ADRs in `docs/architecture/decisions/`.

## Security

See `SECURITY.md`.
