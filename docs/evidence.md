# Evidence and research records

## Per-run outputs

| File | Purpose |
| --- | --- |
| `manifest.json` | Runner/run IDs, command argv, requested configuration, timings, process status, model/source check references and limitations; browser runs also retain selected catalog metadata, inventory hash/count, detector selection mode and workload validation basis |
| `garak-config.json` | The exact generated run configuration supplied to Garak |
| `installation.json` | Python/package versions and audited installed-file hashes; no environment dump |
| `ollama-model.json` | Selected model digest, Ollama version, model system/template and declared parameters |
| `scan.report.jsonl` | Unmodified native evidence including setup, attempt lifecycle, logical conversations, evaluations and completion marker |
| `scan.hitlog.jsonl` | Native flagged outputs when Garak produces a hit log; absence alone does not establish success or failure |
| `scan.report.html` | Native report if Garak succeeds in generating it |
| `console.log` | This scanner subprocess's stdout/stderr |
| `garak-diagnostic-window.log` | New bytes from the shared diagnostic log during the run window; concurrent manual runs may interleave |
| `summary.json` and `summary.md` | Independently counted observations and execution-quality gaps |
| `observations.jsonl` | One record per response slot, preserving full logical prompt/output/conversation data and native line/attempt references |
| `atlas_handoff.md` | One ready-to-paste ATLAS mapping request, run facts, and up to five one-line evidence records with IDs, scores/dispositions, response availability, unassessed behavior, and bounded untrusted input excerpts. First five flagged responses, otherwise first five observations; selection and limits are explicit |
| `research_records.jsonl` | One structured run-catalog record for later Chroma integration |
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

Native JSONL is the original evidence, not the generated narrative. The runner captures full native logical prompt and output records, but **does not capture HTTP wire requests, provider-side hidden instructions, all effective runtime defaults, transport retry bodies, model timing/token usage or stop reasons**. The requested settings and inspected source make the experiment traceable; they are not independent proof of every server-side generation setting. Additional transport capture, if needed later, must be an explicit change with its experimental effect documented.

The handoff omits full configuration/manifest JSON, installation paths, commands, proxy/preflight details, duplicated conversations, empty transport metadata and instructions for the operator. They remain in their original records. Full evidence text, roles, and detector comparison targets remain in the native report and extracted observations. The handoff includes only a bounded input excerpt: the first nonempty line of the last user turn (plain-string input for legacy records), limited to 120 characters and marked `[cut]` when that first line is longer. Quoted excerpts escape control characters. This does not sanitize secrets that may occur inside an excerpt. Response availability is recorded, but behavior is explicitly not assessed; the renderer does not manufacture analyst conclusions from model output.

`handoff --run-dir <folder>` reads the saved summary and offers one copy/open/return selection. Copy or open exits after one confirmation; Enter, 3, EOF or Ctrl+C exits without a desktop action. Open launches Notepad explicitly, with isolated standard streams and no wait for the editor to close. Copy reads only the finished prompt file; terminal status and menu text are never included. `--yes` disables prompts and desktop actions. Copy/open errors do not alter evidence or the scan outcome.

Adding `--regenerate` re-reads the native report and retained manifest and requires their analysis to match the saved summary. It preserves the previous derived handoff and checksum bytes in a unique revision directory before replacing the handoff and updating the checksum index. The native report, manifest, summary, observations, other scan records and settings are not rewritten. This is a derived-artifact revision, not a new scan, replay, or changed experiment.

## Research catalog design

This release exports data but does not open, change or create any Chroma collection. The planned optional integration will use the existing separate Chroma environment and explicitly generated Ollama `embeddinggemma` vectors.

| Record type | Planned contents | Review state |
| --- | --- | --- |
| Model test run | Model/provider/digest, campaign/configuration identity, versions, counts, completion status, evidence references | Automatic run record |
| Observation | Prompt/response evidence, detector result and source references | Initially unreviewed |
| Finding revision | Confirmed or rejected interpretation, limitations, reproduction evidence, source citations, mapping status, prior revision ID | Analyst approved |
| Research note | Hypothesis, experiment, publication reference, research date and conclusions | Explicit note/source status |
| Test corpus item | Test input, origin, allowed use and revision | Stored separately from findings |

Organize by record type and filter by model metadata; do not create a database per tested model by default. Store `target_model` separately from `embedding_model` and its digest. Re-embedding is a separate indexed-version change. Preserve original evidence, approved revisions and exact structured counts independently of similarity search. Collection separation and metadata filtering are organizational features, not demonstrated authorization controls.

Potential searches include similar false positives, past encoded-input experiments, and reviewed observations for a selected model. Exact model comparisons require compatible test definitions, settings and denominators; vector similarity is not a performance or security ranking.

## OpenAI evidence (0.3.0)

OpenAI keeps the same native report, manifest, summary and ATLAS flow. Supplemental records are `openai-session.json` (model-access check separately from probe execution), `openai-transport.jsonl` (sequenced request/response bodies, status, request ID, usage and finish reasons), and `openai-cost.json` (rate provenance, running estimates, missing usage and optional spending-alert choices). Request-cap changes are transport records. The compatibility generation is labeled separately and is never included in probe evaluated-response counts.

Authentication headers are never persisted. Credential echoes are removed before logging or native report construction; the session records whether response redaction occurred. Provider error-message bodies are omitted because they can include fragments of keys; HTTP status, request ID and reported usage remain. This is an intentional evidence limitation, not exact raw-wire preservation. Historical evidence is never rewritten.

A truncated or empty compatibility answer stops before the probe. A truncated probe response remains a coverage gap even if Garak emits a completion marker and detector scores. Failed/unfinished transport and mismatched response/attempt counts also create gaps. Model access confirmed by the compatibility request does not imply probe compatibility or adversarial resistance.
