# Batch execution and evidence collection

Use **Windows PowerShell** in the cloned source directory. Ollama's Windows service must be running for local live scans. Langflow and its Ubuntu WSL terminal are not involved. Commands invoke the scanner environment's Python directly; activation and administrator elevation are not required.

After the README setup:

```powershell
# Local target only; review the exact pending pairs before RUN.
& $scannerPython "$repo\playbook.py" batch --config $config --target ollama-local

# OpenAI target only; review model, settings and cost before RUN.
& $scannerPython "$repo\playbook.py" batch --config $config --target openai-reasoning
```

These are separate commands. To deliberately review both in one batch, repeat the target argument:

```powershell
& $scannerPython "$repo\playbook.py" batch --config $config `
  --target ollama-local --target openai-reasoning
```

The runner also offers its historical default OpenAI profile when absent from private configuration. Set the intended model explicitly during configuration; do not assume public access. Omitting all target arguments selects every offered target, so use the explicit commands above when limiting providers.

## What happens

1. Read the configured Garak registry and saved `*-scan-*` folders under the configured evidence root. Reconcile summaries with native reports, available source checksums and provider transport records. Original files are read only. External historical folders are not silently searched.
2. Retain every inventory ID and selected provider in the matrix, including unavailable probes and specific known requirements. Only enabled probes can enter this batch. There is no automatic allowlist expansion.
3. Credit existing scored evidence for the same probe/provider/model/endpoint, including runs with gaps. This avoids charging for a repeat merely to fill a table; it is not release acceptance or a claim of comparable settings. Original settings are retained in the report. Changed or unreconciled evidence is not silently credited.
4. Construct pending workloads offline. Record actual prompt counts separately from the cap and original expected-count contract. Construction failure blocks that pair and is not a live compatibility result.
5. Show exact pairs, effective generation parameters, detectors, workloads and cost estimates. `RUN` authorizes this batch; Enter cancels before model generation. If pricing is unavailable, P accepts optional operator rates and RUN remains available.
6. For OpenAI, prompt once for a hidden API key. Keep it in memory and send it to isolated scanner children over an anonymous stdin pipe, never argv or evidence. Each worker still performs a separate compatibility request and then its selected probe. API access alone does not validate probe compatibility.
7. Preserve separate original reports, manifests, transport/cost records and ATLAS handoffs. Suppress individual completion menus. No automatic ATLAS, Kumu or Chroma action is added.
8. Produce `batch-summary.md`, `probe-coverage.csv` and `batch.json` in a separate evidence folder. Include diagnostics from saved finish reasons, usage and empty-response records without copying whole transcripts into the summary. A diagnostic field is evidence to interpret, not an automatically confirmed cause.

Existing completed/scored runs are skipped when the batch command is repeated. This resumes at pair boundaries, not halfway through a probe. By default, pairs with only failed/unscored evidence are held; `--retry-failed` deliberately includes those pairs. Previously scored gaps are not automatically rerun or silently fixed by increasing token limits.

## Limits and stopping

- Defaults preserve the existing profiles: Ollama temperature 0, seed 42, 256 output tokens; OpenAI 1500 total completion tokens including reasoning, sampling seed 42, generation temperature/seed not sent, API-default reasoning effort. One generation and sequential requests. They are not matched settings for cross-model comparisons.
- `--completion-tokens N` explicitly changes the OpenAI limit and is recorded as a modified experiment. `--probe probes.FAMILY.CLASS` restricts the batch to exact enabled IDs and can be repeated.
- `--request-cap N` and `--spending-alert AMOUNT` are optional, off by default, and **per run**, not batch-wide. Compatibility requests count. The existing raise/remove/continue/stop controls remain interactive. Account credit balance is not read or used as a cap.
- Usage-based totals include reported compatibility usage and can undercount when usage is missing. The displayed estimate is not an invoice or a hard dollar ceiling. SDK retries remain disabled.
- Authentication/transport failure, operator Stop/interrupt, runner/preflight failure or an evidence reconciliation error stops further execution. Other scored gaps are retained while remaining approved probes continue. No automatic retries occur.
- Eight unscorable outputs cannot be relabeled eight passes. A detector flag cannot be relabeled confirmed attack success. Batch completion means the approved executions were attempted, not that every probe is accepted for release.

## Collect evidence without running models

```powershell
& $scannerPython "$repo\playbook.py" coverage --config $config `
  --target ollama-local --target openai-reasoning
```

This command reads the registry and saved records and makes zero model-generation requests. It creates a new derived report; it does not rewrite original evidence. Use its output to complete the public compatibility table with sanitized evidence aliases, preserving gaps and failed attempts.
