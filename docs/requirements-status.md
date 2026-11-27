# Requirements and scope

The planning documents contain a broader roadmap than the first saved-run checkpoint. Status reflects implementation and operator-supplied Windows evidence available through November 27, 2026. V1 covers fourteen probes; the 191-probe roadmap is not complete. The assisted Windows walkthrough passed; an independent guide-only install remains unverified.

| Requirement | Status and limit |
| --- | --- |
| Windows runner, native evidence/settings preservation, Ollama/OpenAI paths | Implemented and tested on Windows; not every model/probe/error path validated |
| Probe browser | Implemented within revised scope: supported probes only, search, 20-per-page pagination, review, RUN and Back; broader validation deferred |
| Batch execution and saved-run reconciliation | Implemented and exercised. Original batch evidence plus paired headroom retests support 27 completed pairs at documented settings; Ollama DAN remains failed/unscored. Full Windows checkpoint passed at `09e8128`; seven targeted Windows delta checks passed at `4fedd3f`. Later ATLAS/setup code changes and their checks are separately recorded in [release-v1.md](release-v1.md). |
| Concise handoff, Copy/Notepad/Exit | Implemented and exercised; bounded input-excerpt format, full responses retained in original evidence |
| Authenticated ATLAS MCP submission | Exercised in the original lab and assisted clean-laptop walkthrough; exact input/reply archival and unreviewed labeling. A Playground Dataset Sandbox lookup was traced; this does not establish internal tool execution for later MCP submissions. |
| Inline Kumu analysis/link | Implemented at `82ba06f` and passed the observed AML.T0068 saved-file/browser check after one console `SEND`. Project/map/discussed-ID checks passed; matching submission-record counters and internal agent tool execution remain unverified. Analysis is preserved if graph generation/validation fails. |
| Separate Kumu generation | Retained as optional follow-up; operator-selected candidate IDs, project/map binding and saved validation; graph neighbors are context |
| Chroma and local EmbeddingGemma | Met for one saved run: exact read-back, duplicate-free repeat, plain-English retrieval, raw filter results 1/0/0, evidence hashes and original file access |
| Automatic indexing after each scan | Not implemented; current explicit command meets the first checkpoint only |
| Separate observations, reviewed findings and research notes | Not completed; native observation export exists but is not a separate managed research-record workflow |
| Baseline/retest relationships and recorded changes | Narrow paired encoding diagnostic implemented and exercised; general managed research relationships remain deferred |
| Private setup/change log | Partial records exist; no verified consolidated historical setup/change log |
| Sanitized repo, defaults, quick start, history inspection, clean Windows checkout, publication | Scoped Windows checkpoints and the assisted walkthrough passed. Independent guide-only installation remains unverified. Final diff/link and tree/history checks identify their exact commit separately; see the [maintainer release procedure](public-v1.md). |

## Changes from earlier scope

1. Selected full prompt/response transcripts were deliberately replaced by concise input excerpts, detector results and response-availability labels to keep the handoff concise. ATLAS behavioral conclusions remain limited by omitted outputs.
2. Unavailable probes were intentionally removed from visible lists/search/page counts. The full installed inventory is still read internally. Showing unavailable entries and their reasons is superseded in the user-facing browser.
3. Earlier automatic Kumu instructions were removed from the saved handoff in favor of separate graph requests. The November 27 implementation supersedes that default: one confirmed ATLAS submission now wraps the unchanged handoff with an analysis-and-graph request and archives the complete prompt. The same reply includes the checked Kumu URL. Separate graph requests remain optional; selected-nodes-only behavior is not claimed.
4. The dedicated research database reuses the existing Chroma environment while preserving earlier demonstration/reviewed-finding collections.

These decisions should be reflected in the requirements baseline. Broader research features remain deferred requirements, not silently removed commitments. The saved-run checks establish operation, not search ranking quality or confirmed security impact.

5. Ollama DAN investigation closed for v1 on November 23, 2026 with an attempted but failed/unscored pair. This exception does not close OpenAI gaps or establish broad probe compatibility.

6. The November 26 profile change adopts the tested 20000-token profile for three OpenAI encoding probes, keeps all existing integration workflows, defers broader coverage/new research features and records one unsuccessful synthetic AVID export attempt. The closed campaign is not reopened for documentation checks.

7. The November 27 record includes the assisted Windows walkthrough and observed inline Kumu result. An independent guide-only installation remains unverified. Release checks must identify the exact source SHA and preserve this distinction.
