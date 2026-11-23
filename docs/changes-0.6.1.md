# Private candidate 0.6.1

This integrates batch execution into the sanitized v0.5.0 repository candidate. It is not a v1.0.0 public release.

- Added `batch` and read-only `coverage` commands, per-run evidence, saved-run reconciliation, consolidated reports, and one hidden key entry through child stdin. Existing scan, handoff, ATLAS, Kumu and research workflows remain available.
- Corrected batch stopping after a timeout, nonzero or unknown process exit, missing native completion, or a reconciliation warning on a newly generated run. Scored gaps remain reviewable and do not alone trigger an automatic repeat.
- Added focused regressions and actual scanner subprocess tests using synthetic provider responses. Exact-commit validation receipts are shipped outside the source tree. Native Windows execution remains pending.
- Added a fresh-checkout Windows validation helper. It installs separate test/scanner environments, requires the full suite with Chroma and runs five scanner integration checks. It does not scan live models.
- Updated the compatibility table with reported Ascii85 outcomes. 24 of 28 v1 pairs still lack live evidence in this review. Terminal-reported results await native reconciliation. The other 177 IDs remain proposed v2 scope.

Original scan settings and evidence are not modified. Batch skipping is evidence reuse, not release acceptance. Research failure receipts (R-01), broader research records, retrieval-quality validation and owner release decisions remain open or explicitly deferred.
