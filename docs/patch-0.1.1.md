# Version 0.1.1 corrections

**Historical version 0.1.1 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

The independent review identified two real defects in 0.1.0. Both were reproduced before changing the implementation.

1. An exception after subprocess launch, such as failure to write the running manifest, could return without stopping Garak. Scanner cleanup and console-reader completion now occur through `finally` before final artifact writing. Transient and persistent manifest-write regression tests use real inert child processes and verify termination before return or propagation of a write error. Termination failure is surfaced rather than silently ignored.
2. The previous classifier treated any completion record plus gaps as `complete_with_gaps`, including a marker from another run and timeouts. Completed statuses now require a unique matching native run ID and a recorded successful process outcome. Failed, interrupted, timed-out or mismatched runs are `incomplete`. A report-only analysis with no process outcome is `process_outcome_unknown`.

All 37 unit tests and both real-Garak/synthetic-endpoint integrations passed on Linux. Windows process-tree cleanup still requires platform validation. No real LLM security result or mitigation validation is claimed.

## Apply the update

This update archive contains only files under `garak-playbook`. Extract it into the existing projects directory and replace the matching source/test/documentation files. It contains no private configuration, campaign changes, model files, database files or scan evidence. Keep the previous archive for rollback.

No package installation or upgrade is needed. After replacement, `playbook.py --version` reports `0.1.1`. Continue with the existing menu command. Its normal run preflight remains in place; a separate repeated metadata preflight is unnecessary solely for this patch.

## Experiment settings

Temperature 0, seed 42, a 256-token output limit and 32 sampled prompts remain the disclosed defaults. They define a new experiment. Preflight does not use them for generation. The interactive menu displays the resolved configuration and starts only after RUN; unattended `--yes` explicitly selects execution without that prompt. These defaults are not a claim of optimal settings for every research objective.
