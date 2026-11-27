# Release preparation checklist

Checks apply to the commits and scopes recorded below. Later changes need relevant checks, not a relabeling of earlier results.

| ID | Item | Status and acceptance |
| --- | --- | --- |
| R-01 | Research failure receipts | OPEN. Preparation, embedding, database and read-back errors may exit before receipt creation; research-open has no durable receipt. Preserve terminal logs. This does not block preparation or invalidate successful checks. Do not claim complete auditing. |
| R-02 | Clean Windows checkout | PASSED at `09e8128`: supplied November 26 Windows receipt passed. It reused recorded environments from prior fresh installations. Later deltas are separately documented in release-v1.md. |
| R-03 | Fresh scanner installation | PASSED through the recorded prior fresh scanner installation and passed `09e8128` validation with unchanged requirements/package inventories. No reinstall is required for this unchanged dependency set. |
| R-04 | Packaging/history review | Final tracked tree, all reachable historical paths/blobs and commit metadata checked against the allowlist and privacy rules. Private results stay outside Git and release attachments. Recheck if the release branch changes. Synthetic dummy credentials are labeled. |
| R-05 | License and attribution | MIT and third-party notices retained. Retains `Copyright (c) 2026 Garak Playbook contributors`; no external components or datasets are bundled. |
| R-06 | Public repository | Source destination: `anthfuller/garak-mitre-atlas-agent`. Follow the [maintainer release procedure](public-v1.md) for decisions and exact-commit checks. |
| R-07 | Private setup/change log | PARTIAL. Reconstruct supported facts from existing records; mark unknown history rather than inventing it. |
| R-08 | Broader research workflow | DEFERRED, NOT COMPLETE. Automatic indexing; observations/findings/notes; analyst dispositions; general baseline/retest relationships. Narrow encoding comparison is implemented. |
| R-09 | Requirements reconciliation | Recorded in requirements-status.md; preserve the documented scope of the handoff, probe visibility, graph behavior and dedicated research storage. |
| R-10 | Search quality | DEFERRED. Multiple distinct runs and prespecified queries/expected matches are required. |
| R-11 | Public v1 probe coverage | MET FOR AGREED v1 SCOPE: 27 completed pairs at documented settings, one Ollama DAN failed/unscored exception. The three 1500-token OpenAI baselines remain gaps; separate 20000-token retests were 96/96 scorable. Broader 177-probe coverage deferred. See [compatibility](compatibility.md). |
| R-12 | Batch Windows execution | EXERCISED on the existing Windows lab from supplied batch records and console output. Fresh checkout/scanner installation remain R-02/R-03; this does not validate every error path. |
| R-13 | Candidate delta validation | Seven targeted Windows checks passed at `4fedd3f`; full Windows pass at `09e8128` remains distinct. Later reply-formatting, prepared-flow and inline Kumu code changes have separate offline results in [release-v1.md](release-v1.md). No full Windows automated pass is claimed for the latest code. The editorial pass also changes four display strings, with separate offline checks; scan behavior and settings are unchanged. |
| R-14 | AVID smoke | DEFERRED after one synthetic export attempt: `avidtools` missing. No dependency added, troubleshooting or live integration. |
| R-15 | Assisted Windows walkthrough | PASSED: login, flow/file setup, traced Playground dataset lookup, authenticated MCP discovery/submission and archived reply opened. Assistance and a manual component edit were used. An independent guide-only install, including a fresh generated-flow import, remains UNVERIFIED. |
| R-16 | Inline Kumu finish line | PASSED for the observed AML.T0068 saved-file/browser case at `82ba06f`. Console shows one `SEND`; saved analysis contains the URL and the browser displays the technique. The matching submission-record counters and internal agent tool trace remain unverified. See [evidence and limits](inline-kumu-acceptance.md). |

This checklist does not imply completed broader research features.
