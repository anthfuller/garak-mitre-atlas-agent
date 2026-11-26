# Release preparation checklist

Completed saved-run checks need not be repeated solely because a new reviewer joins.

| ID | Item | Status and acceptance |
| --- | --- | --- |
| R-01 | Research failure receipts | OPEN. Preparation, embedding, database and read-back errors may exit before receipt creation; research-open has no durable receipt. Preserve terminal logs. This does not block preparation or invalidate successful checks. Do not claim complete auditing. |
| R-02 | Clean Windows checkout | EARNED at `09e8128`: supplied November 26 Windows receipt passed. It reused recorded environments from prior fresh installations. Later deltas are separately documented in release-v1.md. |
| R-03 | Fresh scanner installation | EARNED through the recorded prior fresh scanner installation and passed `09e8128` validation with unchanged requirements/package inventories. No reinstall is required for this unchanged dependency set. |
| R-04 | Packaging/history review | Final tracked tree, all reachable historical paths/blobs and commit metadata checked against the allowlist and privacy rules. Private results stay outside Git and release attachments. Recheck if the release branch changes. Synthetic dummy credentials are labeled. |
| R-05 | License and attribution | MIT and third-party notices retained. Owner directed keeping `Copyright (c) 2026 Garak Playbook contributors`; no external components or datasets are bundled. |
| R-06 | Public repository | Destination approved: `anthfuller/garak-mitre-atlas-agent`. Start private; upload, public visibility and tagging require the applicable owner authorization. No publication or tag approval yet. |
| R-07 | Private setup/change log | PARTIAL. Reconstruct supported facts from existing records; mark unknown history rather than inventing it. |
| R-08 | Broader research workflow | DEFERRED, NOT COMPLETE. Automatic indexing; observations/findings/notes; analyst dispositions; general baseline/retest relationships. Narrow encoding comparison is implemented. |
| R-09 | Requirements reconciliation | Recorded in requirements-status.md; preserve explicit approvals for handoff, probe visibility, graph scope and dedicated research storage. |
| R-10 | Search quality | DEFERRED. Multiple distinct runs and prespecified queries/expected matches are required. |
| R-11 | Public v1 probe coverage | MET FOR AGREED v1 SCOPE: 27 completed pairs at documented settings, one Ollama DAN failed/unscored exception. The three 1500-token OpenAI baselines remain gaps; separate 20000-token retests were 96/96 scorable. Broader 177-probe coverage deferred. See [compatibility](compatibility.md). |
| R-12 | Batch Windows execution | EXERCISED on the existing Windows lab from supplied batch records and console output. Fresh checkout/scanner installation remain R-02/R-03; this does not validate every error path. |
| R-13 | Candidate delta validation | EARNED at `4fedd3f`: all seven targeted Windows checks passed; exact candidate, bundle and prior-receipt hashes matched. Full Windows pass at `09e8128` remains distinct. Final documentation-only changes receive diff/link and final tree/history checks. |
| R-14 | AVID smoke | DEFERRED after one synthetic export attempt: `avidtools` missing. No dependency added, troubleshooting or live integration. |

Publication still requires owner acceptance of the candidate and disclosed limitations. This checklist does not imply completed broader research features.
