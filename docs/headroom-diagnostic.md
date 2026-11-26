# OpenAI 20,000-token diagnostic (0.6.5)

This opt-in command repeats exactly the saved 32-input samples for InjectAscii85, InjectBase32 and InjectBase64. The model remains gpt-5.6-sol and the detector remains encoding.DecodeMatch. It changes only the target's max_completion_tokens from 1,500 to 20,000. The diagnostic itself does not change default campaign settings or run the other eleven enabled probes, Ollama, ATLAS, Kumu or Chroma.

The dedicated diagnostic is necessary because normal batch execution credits previously scored evidence, including complete_with_gaps. It must not silently skip these three experiments.

## Invocation

Run the included Start-OpenAI-Headroom.ps1 in normal Windows PowerShell. It reads the existing private config and uses its configured Garak Python. No activation, installation, new credentials file or working-runner replacement is required. The private baseline JSON identifies three exact saved runs and pins their evidence hashes. Private paths are not part of public source.

For other operators the underlying command is:

```powershell
& $scannerPython -X utf8 .\headroom_retest.py --config $privateConfig --baselines $baselineConfig
```

The baselines file has a `baselines` array in Ascii85/Base32/Base64 order. Each entry contains `probe`, `folder`, native `run_id`, `scorable` (24/25/31 for this diagnostic), and an optional `sha256` filename-to-hash object. This particular diagnostic deliberately requires the original 80/96 baseline. It is not a generic arbitrary-campaign replay command.

## Before RUN

- Reconcile each saved native report, manifest, recorded summary and transport; verify pinned hashes.
- Verify the configured model and installed Garak/SDK versions and source hashes match the baseline.
- Construct probe prompts offline and compare all inputs and their order exactly with the baseline requests.
- Compare effective scanner configuration allowing only max_completion_tokens to change. Original detector, threshold, sample seed, parallelism and generation count remain unchanged.
- Review 99 planned requests: 96 scan generations plus one existing compatibility check per probe. SDK retries remain zero. Unknown estimates are shown honestly; optional operator-supplied rates remain possible. Estimates at or above $100 show an explicit alert before RUN. There is no credit-balance control.
- Existing HTTP timeout (120 seconds/request) and wall time (1800 seconds/probe) remain unchanged. More token headroom can take longer and still encounter those timeouts; no timeout increase is hidden in this experiment.

RUN is required before hidden, session-only API-key entry. Enter or Ctrl+C cancels. Every HTTP request is also checked against the exact saved request sequence before sending; only the approved token cap differs. Extra/mismatched requests stop without being sent. Authentication, transport, timeout or scanner failure stops the batch without retries.

## Evidence and comparison

Each probe writes its own ordinary scan folder, full native and HTTP evidence, configuration, costs and concise ATLAS handoff. No completion menus interrupt the batch. A separate `*-headroom-*` folder retains plans, preflight records, source fingerprints and the diagnostic receipt.

`comparison.md` and `comparison.json` contain:

- By-probe and overall scorable counts, recovered gaps, newly unscorable answers and unattempted inputs.
- Exact input/occurrence pairing, with both native attempt IDs. UUIDs from separate runs are never used as the pairing key.
- All original sixteen gaps with actual reported completion/reasoning token counts, visible-text presence and finish reason. Missing usage stays unknown.
- Usage-based cost including compatibility, elapsed scan time, and actual completion-token median/P95/maximum. Reasoning is included in completion tokens and is not double-counted.
- Execution status and coverage gaps, source-preservation results, evidence paths and limitations.

Scorable means the detector had valid output and a numeric score, not that the model is safe or the attack succeeded. Flags require analyst review. A single stochastic run cannot prove that the cap alone caused changes. Remote model alias/default drift remains possible; returned model/fingerprint fields are retained where supplied.

The report makes a provisional recommendation only from the retest observations. It never applies a new default. A lower cap inferred from token consumption would need its own validation. Failed/partial scans retain unknown and unattempted states rather than becoming passes.

## Validation scope

`tests/test_headroom.py`: offline comparisons, duplicate-input occurrences, unknown usage, cancellation, preflight failure receipts, scope checks and the $100 alert.

`tests/integration_headroom.py`: actual Garak 0.17.0/OpenAI SDK subprocesses with synthetic responses and socket access denied. Synthetic baseline 80/96, retest 96/96; all 99 retest requests, paired token evidence, prompt guards and source preservation. `failure` exercises HTTP 500 stopping with a partial comparison. These tests do not establish live OpenAI behavior or native Windows validation of this new command.

## Release profile decision

Following the completed Windows retest, the v1 candidate adopts 20000 as the default only for these three probes on `gpt-5.6-sol`. The historical 0.6.5 diagnostic left defaults unchanged. The dedicated diagnostic still requires explicit confirmation and preserves the 1500-token baseline; the release does not trigger another retest.
