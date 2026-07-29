# Support Knowledge Miner

Support Knowledge Miner is a local-first MVP for extracting, curating, and exporting reusable support knowledge from historical paired support records. It is intended for an analyst/curator who imports CSV or JSON message-answer pairs, configures local or cloud model profiles, reviews clusters and candidates, and exports traceable CSV outputs.

The MVP is explicitly local-only. Do not connect it to production systems, production data, production credentials, or production networks.

## Implemented MVP Workflows

- Sign in with a seeded local user's email, restore a still-valid session after a
  reload in the same browser tab, sign out explicitly, and manage equal-permission
  users.
- Create, open, rename, and delete independent projects.
- Import CSV or JSON records with `ticket_id`, `message_group_id`, `message`, and `answer` fields.
- Persist dataset versions, import logs, skipped-record reasons, and audit actor identity.
- Configure global OpenAI, Ollama, and vLLM providers; OpenAI API keys are write-only after save.
- Create project analysis profiles with editable project-local `analysis-N`
  suggestions, provider-filtered configured models, and typed
  HDBSCAN/Agglomerative parameters.
- Start bounded analysis runs that split long `message` texts into provider-safe
  chunks, persist one pooled selected-provider embedding per message, and expose
  observable status, confirmed-batch progress, metadata, and safe diagnostics. The
  visible Runs view refreshes immediately and then every two seconds without
  overlapping requests.
- Generate HDBSCAN or bounded Agglomerative clusters from persisted vectors with
  outlier, membership, parameter, model, and source traceability.
- Curate clusters and candidates while preserving automatic, manual, and effective values separately.
- Export candidate CSV and source-assignment CSV files with persisted export metadata and original-text warnings.
- Use the React sidebar shell to reach sign-in, settings, project, import, profile, run, cluster, candidate, and export workflows.

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
- Runtime: local Docker Compose PostgreSQL/pgvector; optional Ollama and vLLM GPU or CPU profiles.
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

See `deployment/docker/README.md` for PostgreSQL and optional Ollama/vLLM runtime details.

## Run

Run the backend locally:

```bash
uv run --locked python -m backend.main
```

The command starts a Uvicorn server on `http://127.0.0.1:8080` and keeps running
until stopped with `Ctrl+C`. On startup it applies local database migrations and
then creates the initial user if the user table is empty and `SKM_INITIAL_*` is
configured. In another terminal, verify it with:

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

For local model serving, use the optional Ollama or vLLM Compose profiles documented in `deployment/docker/README.md`.
Ollama and vLLM configuration is restricted to reviewed local hosts:
`localhost`, `127.0.0.1`, `::1`, `ollama`, `vllm-gpu`, and `vllm-cpu`.
Provider calls use bounded batches and responses without redirects or fallback.
OpenAI analysis runs additionally require `cloud_use_confirmed: true`.
Ollama embedding calls keep the selected model warm for five minutes between
normal analysis batches; OpenAI and vLLM payloads are unchanged.
Long messages are split at Unicode-safe boundaries into chunks of at most
1,024 UTF-8 bytes. Chunks are produced incrementally, and only the current provider
batch of at most 64 is retained. A byte-weighted mean followed by L2 normalization
combines multiple chunk vectors into exactly one message vector; messages fitting
into one chunk retain the provider vector unchanged. Run metadata records the source byte and chunk
counts without storing source text in diagnostics. Provider failures expose a safe,
actionable reason such as a context-window violation without copying provider
response bodies or message text.
The local backend runs at most two analysis jobs concurrently, queues up to eight
more, and rejects overload safely. Clustering rejects an estimated working set over
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
loading is available only for completed runs, and an empty result explains that
clustering must be generated first.

## Verification

Run the full required gate:

```bash
./.ai/tools/verify.sh
```

Focused gates are also available:

```bash
./.ai/tools/format.sh --check
./.ai/tools/lint.sh
./.ai/tools/test.sh
./.ai/tools/check-dependencies.sh
./.ai/tools/security.sh
./.ai/tools/build.sh
python .ai/tools/check-docs.py
```

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
- `SKM_VLLM_BASE_URL`: optional local vLLM-compatible endpoint.
- `SKM_OLLAMA_BASE_URL`, `SKM_OLLAMA_MODELS`: optional local Ollama endpoint and comma-separated default model allow-list. The backend seeds this provider only when no Ollama provider is configured yet.
- `OLLAMA_KEEP_ALIVE`: optional local Ollama model-residency duration; the Compose
  default and example use `5m`.
- `POSTGRES_*`, `VLLM_*`, `OLLAMA_*`: local Docker Compose settings in `deployment/docker/.env.example`.

Do not commit secrets or local `.env` files.

## Architecture

See `docs/architecture/overview.md` and the ADRs in `docs/architecture/decisions/`.

## Security

See `SECURITY.md`.
