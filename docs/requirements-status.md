# Requirements and approved scope changes

The planning documents contain a broader roadmap than the first saved-run checkpoint. Status reflects implementation and operator-supplied Windows evidence available through November 27, 2026. The current release-preparation direction confirms a 14-probe public-v1 scope, not completion of the 191-probe roadmap. The assisted Windows walkthrough passed; an independent guide-only install remains unverified.

| Requirement | Status and limit |
| --- | --- |
| Windows runner, native evidence/settings preservation, Ollama/OpenAI paths | Implemented and operator-exercised; not every model/probe/error path validated |
| Probe browser | Implemented within revised scope: supported probes only, search, 20-per-page pagination, review, RUN and Back; broader validation deferred |
| Batch execution and saved-run reconciliation | Implemented and exercised. Original batch evidence plus paired headroom retests support 27 completed pairs at documented settings; Ollama DAN remains failed/unscored. Full Windows checkpoint passed at `09e8128`; seven targeted Windows delta checks passed at `4fedd3f`. Later ATLAS/setup code changes and their checks are separately recorded in [release-v1.md](release-v1.md). |
| Concise handoff, Copy/Notepad/Exit | Implemented and exercised; approved input-excerpt format, full responses retained in original evidence |
| Authenticated ATLAS MCP submission | Exercised in the original lab and assisted clean-laptop walkthrough; exact input/reply archival and unreviewed labeling. A Playground Dataset Sandbox lookup was traced; this does not establish internal tool execution for later MCP submissions. |
| Inline Kumu analysis/link | Implemented at `82ba06f` and passed the observed AML.T0068 saved-file/browser check after one console `SEND`. Project/map/discussed-ID checks passed; matching submission-record counters and internal agent tool execution remain unverified. Analysis is preserved if graph generation/validation fails. |
| Separate Kumu generation | Retained as optional follow-up; operator-selected candidate IDs, project/map binding and saved validation; graph neighbors are context |
| Chroma and local EmbeddingGemma | Met for one saved run: exact read-back, duplicate-free repeat, plain-English retrieval, raw filter results 1/0/0, evidence hashes and original file access |
| Automatic indexing after each scan | Not implemented; current explicit command meets the first checkpoint only |
| Separate observations, reviewed findings and research notes | Not completed; native observation export exists but is not a separate managed research-record workflow |
| Baseline/retest relationships and recorded changes | Narrow paired encoding diagnostic implemented and exercised; general managed research relationships remain deferred |
| Private setup/change log | Partial records exist; no verified consolidated historical setup/change log |
| Sanitized repo, defaults, quick start, history inspection, clean Windows checkout, publication | Candidate prepared on private `main`; scoped Windows checkpoints and assisted walkthrough passed. Independent guide-only installation remains unverified. Final diff/link and tree/history checks identify the exact candidate separately. Public visibility and tagging remain pending owner approval. |

## Approved changes from older wording

1. Selected full prompt/response transcripts were deliberately replaced by concise input excerpts, detector results and response-availability labels at the user's request. This is an approved change, not an accidentally omitted field. ATLAS behavioral conclusions remain limited by omitted outputs.
2. Unavailable probes were intentionally removed from visible lists/search/page counts. The full installed inventory is still read internally. Showing unavailable entries and their reasons is superseded in the user-facing browser.
3. Earlier automatic Kumu instructions were removed from the saved handoff in favor of separate graph requests. The November 27 direction supersedes that default: one confirmed ATLAS submission now wraps the unchanged handoff with an analysis-and-graph request and archives the complete prompt. The same reply includes the checked Kumu URL. Separate graph requests remain optional; selected-nodes-only behavior is not claimed.
4. A dedicated research database was approved, reusing the existing Chroma environment while preserving earlier demonstration/reviewed-finding collections.

These decisions should be reflected in the requirements baseline. Broader research features remain deferred requirements, not silently removed commitments. The saved-run checks establish operation, not search ranking quality or confirmed security impact.

5. On November 23, 2026 the operator directed closing Ollama DAN investigation for v1 as an attempted but failed/unscored pair and proceeding to clean Windows validation. This exception does not close OpenAI gaps or establish broad probe compatibility.

6. The November 26 release direction adopts the tested 20000-token profile for three OpenAI encoding probes, keeps all existing integration workflows, defers broader coverage/new research features and permits one synthetic AVID smoke. It does not require further live scans for documentation.

7. The November 27 preparation direction records the assisted Windows walkthrough and observed inline Kumu result, retains the independent guide-only installation gap, and requests an exact-SHA candidate and final tree/history check on private `main`. It does not authorize public visibility, tagging, or reopening the closed probe campaign.
