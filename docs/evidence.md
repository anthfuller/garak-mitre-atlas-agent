# Evidence and research records

## Per-run outputs

| File | Purpose |
| --- | --- |
| `manifest.json` | Runner/run IDs, command argv, requested configuration, timings, process status, model/source check references and limitations; browser runs also retain selected catalog metadata, inventory hash/count, detector selection mode and workload validation basis |
| `garak-config.json` | The exact generated run configuration supplied to Garak |
| `installation.json` | Python/package versions and audited installed-file hashes; no environment dump |
| `ollama-model.json` | Selected model digest, Ollama version, model system/template and declared parameters |
| `scan.report.jsonl` | Native evidence as written by Garak: setup, attempt lifecycle, logical conversations, evaluations and completion marker |
| `scan.hitlog.jsonl` | Native flagged outputs when Garak produces a hit log; absence alone does not establish success or failure |
| `scan.report.html` | Native report if Garak succeeds in generating it |
| `console.log` | This scanner subprocess's stdout/stderr |
| `garak-diagnostic-window.log` | New bytes from the shared diagnostic log during the run window; concurrent manual runs may interleave |
| `summary.json` and `summary.md` | Independently counted observations and execution-quality gaps |
| `observations.jsonl` | One record per response slot, preserving full logical prompt/output/conversation data and native line/attempt references |
| `atlas_handoff.md` | One ready-to-paste ATLAS mapping request, run facts, and up to five one-line evidence records with IDs, scores/dispositions, response availability, unassessed behavior, and bounded untrusted input excerpts. First five flagged responses, otherwise first five observations; selection and limits are explicit |
| `research_records.jsonl` | Structured run-catalog export; optional research commands build a checked searchable record from the saved run |
| `openai-session.json` | OpenAI model-access check, requested/returned model, request count, limits and scan status; compatibility and probe execution remain distinct |
| `openai-transport.jsonl` | OpenAI request/response records, stage and sequence, HTTP status, request ID, client elapsed time, reported usage and finish reasons where returned; credential handling is described below |
| `openai-cost.json` | Derived usage/cost estimates, rate provenance, missing-usage tracking and optional spending-alert choices |
| `ollama-session.json` and `ollama-transport.jsonl` | Ollama session status and supplemental HTTP records for runs using the runner's audited transport; these supplement the native report |
| `checksums.json` | SHA-256 values of retained files; no signature or immutable-storage claim |
| `handoff-revisions/<unique-revision>/` | Created only by explicit handoff regeneration: previous handoff/checksum bytes and a revision record linking input/output hashes |

On preflight failure, only the available records exist. On interruption or a scan failure, the runner attempts to produce summaries and a handoff reflecting the missing evidence. Native errors, null/empty outputs, missing detector scores, invalid JSON, absent completion and accounting mismatches become coverage gaps. They are not passes.

Execution status requires separate evidence of report completion and process outcome:

| Status | Required evidence |
| --- | --- |
| `completed` | A unique completion marker matching the native run ID, recorded process state `exited`, integer exit code 0, and no detected gaps |
| `complete_with_gaps` | The same valid completion and successful process outcome, but other evidence/accounting gaps |
| `incomplete` | Absent/mismatched/ambiguous completion, failed/interrupted/timed-out process, known nonzero exit, or a process still recorded as running/preflight |
| `process_outcome_unknown` | Native completion matches, but a successful process outcome is not recorded |

The runner invokes cleanup in a `finally` block for every launched scanner before final artifact writing. Cleanup failures are reported explicitly. No Python `finally` block can run if the runner itself is forcibly killed by the operating system or the computer loses power.

Workload validation distinguishes an upper limit from an expected count. New browser runs record `workload.attempt_cap`, `expected_attempts` (nullable), the enforcement mechanism and its source-review basis. An upper-limit breach is a coverage gap. A shortfall is classified only when an exact expected count is justified. Native completion/process checks and missing-response checks always apply. The two existing 32-prompt profiles retain their known expectations; older saved 32-prompt manifests remain readable without rewriting them. HTTP retries can exceed logical-attempt counts; the prompt cap is not a network-request budget.

Lifecycle snapshots are deduplicated by attempt UUID. Each detector has separate counters. A response flagged by several detectors counts once in the unique flagged-response count. All flags start as `unreviewed`; `attack_success` and `legitimate_task_completion` start as `not_assessed`.

The native Garak JSONL is the primary scan evidence. It preserves logical prompts, outputs and detector evaluations, but it is not a complete HTTP or provider-usage record. The provider-specific files listed above supplement it. For OpenAI, response rows in `openai-transport.jsonl` contain `body.usage` and `body.choices[*].finish_reason` when the provider returns them, plus `elapsed_seconds` measured by the client. `openai-cost.json` contains derived estimates; `openai-session.json` describes access and execution status. These files do not reveal hidden provider instructions, every server-side default, or actual GPU execution time. Missing usage is reported as missing, not zero. Historical runs without these supplemental records cannot acquire that evidence retroactively.

The handoff omits full configuration/manifest JSON, installation paths, commands, proxy/preflight details, duplicated conversations, empty transport metadata and instructions for the operator. They remain in their original records. Full evidence text, roles, and detector comparison targets remain in the native report and extracted observations. The handoff includes only a bounded input excerpt: the first nonempty line of the last user turn (plain-string input for legacy records), limited to 120 characters and marked `[cut]` when that first line is longer. Quoted excerpts escape control characters. This does not sanitize secrets that may occur inside an excerpt. Response availability is recorded, but behavior is explicitly not assessed; the renderer does not manufacture analyst conclusions from model output.

`handoff --run-dir <folder>` opens the same result menu used after an interactive scan:

| Action | Effect |
| --- | --- |
| 1 | Copy the saved ATLAS prompt and return to PowerShell |
| 2 | Open the saved ATLAS prompt in Notepad and return to PowerShell |
| 3 or Enter | Return to PowerShell |
| 4 | Review and confirm `SEND` to request ATLAS analysis and a Kumu URL |
| 5 | Review selected IDs and confirm `GRAPH` for an optional separate Kumu view from saved analysis |

Copy reads only the finished prompt file. Notepad opens with isolated standard streams and no wait for editor closure. `handoff --yes` disables prompts and desktop actions; it sends nothing to ATLAS. EOF or Ctrl+C returns to the shell. Copy/open errors do not alter evidence or the scan outcome. Follow the [operator guide](operator-guide.md#start-in-windows-powershell) for separate copyable commands.

Adding `--regenerate` re-reads the native report and retained manifest and requires their analysis to match the saved summary. It preserves the previous derived handoff and checksum bytes in a unique revision directory before replacing the handoff and updating the checksum index. The native report, manifest, summary, observations, other scan records and settings are not rewritten. This is a derived-artifact revision, not a new scan, replay, or changed experiment.

## Optional local indexing and search

Optional search is implemented. `research-index` reads and reconciles a saved run, checks evidence hashes, and writes a current record to the dedicated embedded Chroma collection `garak_research_runs_v1`. Ollama generates local `embeddinggemma:latest` vectors explicitly. No Chroma server or cloud embedding fallback is required. Original evidence stays in place; indexing does not create an analyst-confirmed finding.

`research-search` accepts a plain-English query and optional exact model/probe filters. `research-open` opens a hash-checked original text record. An unchanged repeat index keeps one record and skips another embedding request; a changed research record retains the previous JSON revision. The stored run model is separate from the embedding model and pinned embedding digest.

Follow [Optional: index and search locally](install-and-verify.md#optional-index-and-search-locally) for setup and commands. Its sample finish line is a search result for `synthetic-example` and opening that run's hash-checked summary. Real local EmbeddingGemma indexing, repeated indexing, filtering, search and evidence opening were observed on Windows for one saved run. Broader retrieval quality remains unverified. Some failures exit before a durable receipt is written, and `research-open` has no durable receipt; this remains R-01 in the [release checklist](release-checklist.md).

## Research features still deferred

| Feature | Current limit |
| --- | --- |
| Managed findings and analyst dispositions | Research records remain unreviewed; no finding-approval workflow is implemented |
| Research notes and separate test-corpus management | Not implemented as managed record types |
| Automatic indexing after scans | Indexing requires an explicit command |
| General baseline/retest relationships | Only the documented paired encoding diagnostic is implemented |
| Search-quality evaluation | One successful saved-run example does not establish relevance across a research collection |

Collection separation and metadata filtering are organizational features, not demonstrated authorization controls. Similarity is not a security score. Exact model comparisons require compatible tests, settings and denominators.

## Supplemental OpenAI records

OpenAI scan results use the same native report, manifest, summary and handoff format. Supplemental records are `openai-session.json` (model-access check separately from probe execution), `openai-transport.jsonl` (sequenced request/response bodies, status, request ID, usage and finish reasons), and `openai-cost.json` (rate provenance, running estimates, missing usage and optional spending-alert choices). Request-cap changes are transport records. The compatibility generation is labeled separately and is never included in probe evaluated-response counts.

Authentication headers are never persisted. Credential echoes are removed before logging or native report construction; the session records whether response redaction occurred. Provider error-message bodies are omitted because they can include fragments of keys; HTTP status, request ID and reported usage remain. This is an intentional evidence limitation, not exact raw-wire preservation. Historical evidence is never rewritten.

A truncated or empty compatibility answer stops before the probe. A truncated probe response remains a coverage gap even if Garak emits a completion marker and detector scores. Failed/unfinished transport and mismatched response/attempt counts also create gaps. Model access confirmed by the compatibility request does not imply probe compatibility or adversarial resistance.
