# Requirements and approved scope changes

The planning documents contain a broader roadmap than the first saved-run checkpoint. Status reflects implementation and operator-supplied Windows evidence available through November 26, 2026. The current release-preparation direction confirms a 14-probe public-v1 scope, not completion of the 191-probe roadmap.

| Requirement | Status and limit |
| --- | --- |
| Windows runner, native evidence/settings preservation, Ollama/OpenAI paths | Implemented and operator-exercised; not every model/probe/error path validated |
| Probe browser | Implemented within revised scope: supported probes only, search, 20-per-page pagination, review, RUN and Back; broader validation deferred |
| Batch execution and saved-run reconciliation | Implemented and exercised. Original batch evidence plus paired headroom retests support 27 completed pairs at documented settings; Ollama DAN remains failed/unscored. Windows checkpoint passed at `09e8128`; later deltas are separately documented. |
| Concise handoff, Copy/Notepad/Exit | Implemented and exercised; approved input-excerpt format, full responses retained in original evidence |
| Authenticated ATLAS MCP submission | Met for one saved run; exact input/reply archival and unreviewed labeling; internal flow execution not independently traced |
| Separate Kumu generation | Added and exercised; operator-selected candidate IDs, project/map binding and saved validation; graph neighbors are context |
| Chroma and local EmbeddingGemma | Met for one saved run: exact read-back, duplicate-free repeat, plain-English retrieval, raw filter results 1/0/0, evidence hashes and original file access |
| Automatic indexing after each scan | Not implemented; current explicit command meets the first checkpoint only |
| Separate observations, reviewed findings and research notes | Not completed; native observation export exists but is not a separate managed research-record workflow |
| Baseline/retest relationships and recorded changes | Narrow paired encoding diagnostic implemented and exercised; general managed research relationships remain deferred |
| Private setup/change log | Partial records exist; no verified consolidated historical setup/change log |
| Sanitized repo, defaults, quick start, history inspection, clean Windows checkout, publication | Candidate preparation and carried Windows checkpoint documented; exact commit/delta checks supplied with candidate. Publication remains pending owner approval |

## Approved changes from older wording

1. Selected full prompt/response transcripts were deliberately replaced by concise input excerpts, detector results and response-availability labels at the user's request. This is an approved change, not an accidentally omitted field. ATLAS behavioral conclusions remain limited by omitted outputs.
2. Unavailable probes were intentionally removed from visible lists/search/page counts. The full installed inventory is still read internally. Showing unavailable entries and their reasons is superseded in the user-facing browser.
3. Automatic Kumu instructions were removed from the handoff. Separate graph requests use selected IDs plus one-hop research context; selected-nodes-only behavior is not claimed.
4. A dedicated research database was approved, reusing the existing Chroma environment while preserving earlier demonstration/reviewed-finding collections.

These decisions should be reflected in the requirements baseline. Broader research features remain deferred requirements, not silently removed commitments. The saved-run checks establish operation, not search ranking quality or confirmed security impact.

5. On November 23, 2026 the operator directed closing Ollama DAN investigation for v1 as an attempted but failed/unscored pair and proceeding to clean Windows validation. This exception does not close OpenAI gaps or establish broad probe compatibility.

6. The November 26 release direction adopts the tested 20000-token profile for three OpenAI encoding probes, keeps all existing integration workflows, defers broader coverage/new research features and permits one synthetic AVID smoke. It does not require further live scans for documentation.
