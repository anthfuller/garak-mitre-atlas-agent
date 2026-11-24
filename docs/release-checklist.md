# Release preparation checklist

Completed saved-run checks need not be repeated solely because a new reviewer joins.

| ID | Item | Status and acceptance |
| --- | --- | --- |
| R-01 | Research failure receipts | OPEN. Preparation, embedding, database and read-back errors may exit before receipt creation; research-open has no durable receipt. Preserve terminal logs. This does not block preparation or invalidate successful checks. Do not claim complete auditing. |
| R-02 | Clean Windows checkout | PENDING. Fresh clone, new test environment, complete suite with zero skips, retained OS/commit/result receipt. No private lab configuration or evidence. |
| R-03 | Fresh scanner installation | PENDING. New scanner environment, resolved package inventory and synthetic Garak integrations. Distinct from an already-working lab environment. |
| R-04 | Packaging/history review | Rechecked for this candidate; review receipt is outside the source bundle. Repeat if the tracked tree/history changes before publication. Synthetic dummy credentials are labeled. |
| R-05 | License and attribution | MIT included for original project files. Confirm copyright holder and complete final redistribution review for the release commit. |
| R-06 | Public repository | PENDING. Obtain intended owner/name and publication instruction after review. No GitHub repository created or published. |
| R-07 | Private setup/change log | PARTIAL. Reconstruct supported facts from existing records; mark unknown history rather than inventing it. |
| R-08 | Broader research workflow | DEFERRED, NOT COMPLETE. Automatic indexing; observations/findings/notes; analyst dispositions; baseline/retest links. |
| R-09 | Requirements reconciliation | Recorded in requirements-status.md; preserve explicit approvals for handoff, probe visibility, graph scope and dedicated research storage. |
| R-10 | Search quality | DEFERRED. Multiple distinct runs and prespecified queries/expected matches are required. |
| R-11 | Public v1 probe coverage | OPEN. Table updated: 24 completed, three OpenAI pairs with gaps, one Ollama DAN failed/unscored. Ollama DAN investigation closed for v1 by operator direction; OpenAI gaps remain open. See [v1 release instructions](public-v1.md). |
| R-12 | Batch Windows execution | EXERCISED on the existing Windows lab from supplied batch records and console output. Fresh checkout/scanner installation remain R-02/R-03; this does not validate every error path. |

Moving forward with preparation does not imply every open item blocks progress or has been accepted as complete. Publication must accurately describe unresolved limits.
