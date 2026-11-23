# 0.5.0 — optional Chroma research index

Apply this source patch over 0.4.2. It adds three commands without changing scanning, campaign settings, handoff rendering, MCP transport, Kumu validation or completion menus. No existing database is adopted. No dependency is automatically installed, model downloaded, cloud API called or scan started.

## What is indexed

`research-index` reads one existing runner report, reconciles its saved summary against the native report and manifest, and checks source hashes. It writes one current record per Garak run ID to the dedicated `garak_research_runs_v1` collection in a **new, separate** embedded database. A Chroma server is not required.

The record preserves the run ID, model, probe, execution status, exact per-detector counts, distinct evaluated/flagged response counts, complete saved summary and coverage gaps. Counts across detectors are not added as distinct responses. Every linked original file has an absolute path and SHA-256 hash. The optional ATLAS submission is tied to the same original run; its text remains **unreviewed analysis**. Extracted IDs are labeled mentions, which may include rejected/background IDs. Graph-selected IDs remain **candidates pending analyst review**.

An optional Kumu reference requires the selected ATLAS submission, graph archive and existing passing offline validation file. The index checks their identity, hashes and URL against the expected target recorded in that validation. It does not rerun the graph request or silently reread/change the private Kumu configuration. Prior browser rendering and internal ATLAS execution are not established by indexing. Optional `--screenshot PATH` references are hashed and linked; no image analysis occurs.

Original reports, transcripts, configurations, ATLAS replies and graph files remain at their original locations. Chroma is a searchable index, not their replacement. No attack corpus is inserted. The new research collection is separate from any reviewed-findings or demonstration collections; collection separation and metadata filters do not establish authorization enforcement.

## Embedding and revision policy

The search text is the existing concise handoff representation plus the first context for each of the first five ATLAS-mentioned IDs, bounded to 240 characters per context. The stored document labels those excerpts untrusted, incomplete and unreviewed. This is a sampled search representation, not a full-transcript index. Full records are available through evidence references.

Embeddings are generated explicitly through loopback Ollama `/api/embed`, using `embeddinggemma:latest`, raw document/query text, `truncate: false`, default model dimensions and no generation-setting overrides. Chroma receives vectors directly with `embedding_function=None` and cosine distance. No automatic embedding download or cloud fallback is enabled. Overlong input fails instead of silently truncating it. The installed model digest is checked and pinned to the collection; a digest/policy change requires a different store, with no automatic migration. Receipts record Ollama, Python and Chroma versions, digest, endpoint, local request types, embedding dimensions when generated, and returned input-token counts where available.

An unchanged reindex keeps one current record and skips the embedding request. A changed set of source references or derived research content creates a new immutable JSON revision under `records/`, then updates the same Chroma record ID. Prior revisions are retained. Exact document and metadata read-back is required. Analyst review/disposition editing is not implemented in this release: every current research record remains unreviewed. Do not manually mark Chroma metadata as a confirmed finding.

Successful index and search operations write receipts under the configured research root. Some failures exit before a receipt is created; research-open also has no durable receipt. This is open release item R-01, not a claim of complete operation auditing. Original run files are not modified. Use one research operation at a time; an exclusive lock prevents concurrent runner operations. If a process is forcibly killed, `.research.lock` may remain. Verify that no research process is running before removing only that stale lock. Do not delete the database to resolve a lock.

## Public Windows setup (new installation only)

Prerequisites: Windows, Python 3.11, the existing Garak runner source and a saved run, and Ollama with `embeddinggemma:latest` installed locally. The public default uses `%LOCALAPPDATA%\GarakPlaybook`. Lab operators may use an absolute path on another disk. Configuration must stay outside the source directory.

For a **new user without a Chroma environment**, in Windows PowerShell:

```powershell
$publicRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
py -3.11 -m venv (Join-Path $publicRoot 'research-env')
& (Join-Path $publicRoot 'research-env\Scripts\python.exe') -m pip install 'chromadb==1.5.9'
```

If Chroma 1.5.9 already works in a dedicated environment, reuse that Python executable instead. Do not install or upgrade anything into the working Garak environment for this extension. Copy `examples/research.config.example.json` to a private path and set `python` and `storage_root` for that machine. The runner expands environment variables. A nonexistent or empty research root is required on first use; a nonempty unowned directory is rejected, protecting existing databases.

The configured interpreter must contain Chroma 1.5.9. The main runner delegates research commands to that interpreter. On disk:

```text
research-store.json — store ownership marker
chroma/ — dedicated embedded database
records/<run-key>/<content-hash>.json — retained immutable research revisions
receipts/<timestamp>-<id>.json — operation results and provenance
```

## Index one saved run

All commands below belong in **Windows PowerShell**. Supply existing paths; these are generic examples, not personal configuration:

```powershell
$labPython = 'C:\AI-Lab\garak-env\Scripts\python.exe'
$runner = 'D:\AI-Lab\projects\garak-playbook\playbook.py'
$researchConfig = 'D:\AI-Lab\private\research.private.json'
$savedRun = 'D:\AI-Lab\evaluations\existing-run'

# Run-only index (ATLAS and Kumu are optional).
& $labPython $runner research-index --research-config $researchConfig --run-dir $savedRun

# To include existing ATLAS and Kumu records, explicitly choose their saved paths.
$indexArgs = @(
  'research-index', '--research-config', $researchConfig, '--run-dir', $savedRun,
  '--atlas-submission', "$savedRun\atlas-submissions\existing-analysis",
  '--graph-dir', "$savedRun\kumu-submissions\existing-graph",
  '--graph-validation', "$savedRun\kumu-validations\existing-validation\validation.json"
)
& $labPython $runner @indexArgs
```

Do not run both examples expecting two independent runs: they refer to the same run ID. Adding the optional references updates that run's current research revision. Repeat the **same** chosen command to test idempotence. Expect `indexed` initially (or `updated_revision` when adding references), then `unchanged`, with the collection count unchanged on the repeat. An error is not successful indexing.

## Search and open original evidence

```powershell
# Plain-English vector query.
& $labPython $runner research-search --research-config $researchConfig `
  --query 'roleplay jailbreak attempts with incomplete responses'

# Exact metadata filters, separately or together; use the stored model/probe values.
& $labPython $runner research-search --research-config $researchConfig `
  --query 'roleplay jailbreak attempts' --model 'YOUR_SCANNED_MODEL'
& $labPython $runner research-search --research-config $researchConfig `
  --query 'roleplay jailbreak attempts' --probe 'dan.DanInTheWild'

# Explicitly open a hash-checked original text file in detached Notepad.
& $labPython $runner research-open --research-config $researchConfig `
  --run-id 'YOUR_GARAK_RUN_ID' --evidence summary
```

`research-open` choices: `summary`, `report`, `atlas`, `kumu-url`. It opens the selected original text file, not a browser link or executable. It requires a matching recorded hash. Search prints original evidence paths, review status and current hash availability. Missing/changed evidence is shown as such. Query/result receipts are private research data too.

Search uses cosine distance; lower is closer, not more vulnerable or more authoritative. Finding the only indexed run proves operation, not search quality. Broader relevance evaluation requires multiple distinct real runs and prespecified queries/expected matches. Synthetic distractors test filters and routing, not EmbeddingGemma quality.

## Validation and release boundaries

Implemented tests use real embedded Chroma 1.5.9 on Linux, synthetic run/ATLAS/Kumu records and deterministic fake vectors. They cover duplicate-free repeat indexing, exact read-back, retained revisions, source preservation, graph/ATLAS reference binding, model/probe filters, stale evidence, model-digest changes, existing-store refusal, and actual parent/worker CLI routing against a local fake Ollama HTTP server. HTTP tests verify `truncate: false` and reject invalid vectors. Notepad invocation is mocked; actual Windows editor behavior is not claimed.

The operator's original native run and graph archive have not been copied into the build environment. Their local reconciliation happens when the Windows index command runs. Windows acceptance remains **unfinished** until two index calls, a real local EmbeddingGemma query, metadata filtering and original evidence opening succeed. No new Garak scan or paid call is needed.

The public source includes no personal paths, credentials, original evidence or database. Private configuration, evidence, embedding downloads and database files are excluded. A sanitized GitHub release is still a separate deliverable: it requires complete source packaging, dependency/license review and a clean Windows checkout test. This patch is not a claim that that release is already deployment-validated.

Implementation references: [Chroma 1.5.9 client API](https://github.com/chroma-core/chroma/blob/1.5.9/chromadb/api/client.py), [collection API](https://github.com/chroma-core/chroma/blob/1.5.9/chromadb/api/models/Collection.py), [Ollama embeddings API](https://docs.ollama.com/api/embed), [Ollama version/tags API](https://github.com/ollama/ollama/blob/main/docs/api.md). No internal Chroma API attributes are used.
