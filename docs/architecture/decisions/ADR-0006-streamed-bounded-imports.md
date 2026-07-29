# ADR-0006: Streamed and bounded large-file imports

- Status: accepted
- Date: 2026-07-27
- Owners: User
- Related requirement: increase-import-size-limit; support-knowledge-miner-mvp1
- External reference identifiers: `https://pypi.org/project/ijson/`

## Context

The import UI currently reads a whole file into a browser string, wraps that string
in JSON, and the backend materializes the request, parsed document, valid records,
and skipped records. Raising the existing 5 MiB check to the required 512 MB would
allow one request to consume several gigabytes of memory. Standard-library CSV can
iterate rows, but standard-library JSON materializes a complete top-level array.

The supported local workflow needs CSV and JSON files through 512 MiB, atomic
project-scoped dataset creation, clear German size/format failures, and bounded
memory/error-detail behavior.

## Decision

Keep the authenticated project import endpoint path, but atomically replace its
JSON-wrapped `content` request with a raw streamed file body. Use `Content-Type` for
CSV/JSON and RFC 5987 `Content-Disposition` filename metadata rather than placing
the filename in the URL. The browser sends the selected `File` directly.

The route counts actual received bytes, stops above 512 MiB
(536,870,912 bytes), writes only to a securely created local temporary file, and
removes it on every outcome. `Content-Length`, when present, is only an early
rejection hint and never replaces streamed byte counting.

Parse CSV iteratively with the Python standard library and parse a strict top-level
JSON array iteratively with locked `ijson>=3.5,<4`. Validate/count in a first pass,
then repeat the immutable temporary input and persist valid records in bounded
batches capped by both 1,000 records and a conservative 4 MiB encoded-text estimate
inside one transaction. A late parse or database failure commits no partial dataset.
Complete valid/skipped/total counts are retained, while at most the first 100
skipped-record details are persisted and returned; the UI communicates truncation.

Admit at most two active upload/import operations per backend process and return
HTTP 503 with a retry hint when both slots are occupied. Abort and clean up an upload
when no new body chunk arrives for 30 seconds or total upload duration reaches 30
minutes. The absolute deadline remains effective even when a client periodically
sends small chunks. The slot spans spooling, both parser passes, and the database
transaction and is released on success, failure, disconnect, timeout, or
cancellation.

The UI rejects unsupported extensions and files above 512 MiB before upload. It
displays distinct actionable German messages for oversize, unsupported media/type,
invalid UTF-8, missing CSV headers, malformed CSV/JSON, non-array JSON roots, and
zero valid records. File-level parse failures retain an inspectable failed import
log; transport failures before parsing create no dataset or import log.

## Alternatives considered

- Raise only the existing constant: rejected because browser/request/parser/list
  copies make 512 MiB unsafe.
- Unlimited imports: rejected because upload, disk, memory, and database use must
  remain bounded.
- Keep both buffered and streamed API contracts: rejected because there is no
  external compatibility consumer and parallel behavior would remain unsafe.
- Multipart upload: rejected because it adds a second parser/dependency without
  removing the need for an independent total-byte guard.
- Custom incremental JSON parser: rejected because correctness/security risk is
  higher than a reviewed streaming parser dependency.
- JSON Lines only: rejected because the accepted import contract is a JSON array.

## Consequences

### Positive

- 512 MiB files no longer require whole-file browser or Python object copies.
- Actual wire bytes, parser collections, persistence batches, and error detail are
  bounded.
- Existing CSV/JSON record shape and project transaction semantics remain.
- Failure messages identify corrective action instead of hiding format errors.

### Negative

- The frontend/backend import request contract changes atomically.
- Imports perform two sequential parser passes and need temporary local disk space
  slightly above the source size.
- `ijson` becomes a direct locked dependency and may use a native YAJL wheel.
- Only the first 100 skipped-record details remain inspectable.

### Risks and mitigations

- Temporary-disk exhaustion: enforce the byte cap while receiving and always clean
  up in `finally`; cap active imports at two and document local disk headroom.
- Client disconnects and malformed late input: test cleanup and transaction
  rollback at explicit seams.
- Dependency/supply chain: lock resolved artifacts, review license/provenance and
  lock diff, and run dependency/security gates; remove if JSONL or a suitable
  standard-library iterator supersedes it.
- One pathological record can approach the total limit: parser/result collections
  must never accumulate multiple records, and review must include memory-shape
  evidence.

## Validation

- Frontend tests prove rejected files are not read/uploaded and backend messages are
  displayed.
- API tests stream chunked bodies, simulate reduced byte boundaries, and verify
  HTTP/status behavior and temporary-file cleanup.
- Parser/service/database tests cover CSV and JSON iteration, late malformed input,
  complete counts, 100-detail truncation, bounded batches, and atomic rollback.
- Dependency, security, documentation, full verification, and independent
  security-focused review must pass.
