# Version 0.6.1 changes (historical)

Version 0.6.1 integrated batch execution into the 0.5.0 source. The results below describe that checkpoint. Use the [current install guide](install-and-verify.md), [compatibility table](compatibility.md) and [release record](release-v1.md) for later behavior and validation.

- Added `batch` and read-only `coverage` commands, per-run evidence, saved-run reconciliation, consolidated reports, and one hidden key entry through child stdin. Existing scan, handoff, ATLAS, Kumu and research workflows remain available.
- Corrected batch stopping after a timeout, nonzero or unknown process exit, missing native completion, or a reconciliation warning on a newly generated run. Scored gaps remain reviewable and do not alone trigger an automatic repeat.
- Added focused regressions and actual scanner subprocess tests using synthetic provider responses. Exact-commit validation receipts are shipped outside the source tree. Native Windows execution was unverified at this checkpoint.
- Added a fresh-checkout Windows validation helper. It installs separate test/scanner environments, requires the full suite with Chroma and runs five scanner integration checks. It does not scan live models.
- Updated the compatibility table with reported Ascii85 outcomes. At that checkpoint, 24 of 28 v1 pairs lacked live evidence and terminal-reported results awaited native reconciliation. The other 177 IDs remain proposed v2 scope.

Original scan settings and evidence are not modified. Batch skipping is evidence reuse, not release acceptance. Research failure receipts (R-01), broader research records and retrieval-quality validation remain open or explicitly deferred in the current requirements record.
