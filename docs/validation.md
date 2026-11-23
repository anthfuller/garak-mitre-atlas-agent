# Validation record for release 0.3.0

Build date: November 22, 2026 (America/New_York).

| Item | Status | Evidence and boundary |
| --- | --- | --- |
| Installed CLI interface | Confirmed | Operator-supplied `--help` output identifies Garak 0.17.0 and required arguments; retained privately |
| Source behavior | Inspected | Exact PyPI Garak 0.17.0 wheel; selected source and payload SHA-256 hashes recorded in `source-audit.json` |
| Unit tests | Passed for 0.3.0 | 103 offline tests cover existing evidence/handoff behavior, filtered inventory/search/pagination and Back, OpenAI menu/settings/credentials, estimates and optional controls |
| Reviewer defects reproduced | Confirmed against 0.1.0 | Three targeted regressions failed: mismatched completion identity, timed-out process classification, and a real inert child left running after manifest-write failure |
| Exceptional child cleanup | Passed on Linux | Real inert Python child was already terminated after transient and persistent manifest-write failures; no LLM was used |
| Base64 profile integration | Passed again for 0.3.0 against synthetic endpoint | Real Garak CLI made 32 synthetic protocol requests with expected model, messages, seed, temperature and output limit; native evidence and runner artifacts generated |
| DAN profile integration | Passed again for 0.3.0 against synthetic endpoint | Same integration checks, 32 synthetic protocol requests |
| Test platform | Linux, Python 3.12 | Isolated test dependencies; these are not changes to the operator's environment |
| Windows PowerShell preflight | Reported successful for 0.1.0 | Operator supplied a passing preflight with zero generation requests |
| Windows real-model run | Exercised using 0.1.1 | Supplied console and summary agree on a completed local run, exit code 0, matching completion identity, 32 evaluated responses and zero DecodeMatch flags; the exported handoff contains the same summary. The full native report was not supplied for this review |
| ATLAS handoff sample review | Reviewed five of 32 responses | Three incorrect decoded answers, one incorrect decoding procedure ending mid-answer, and one refusal. Possible truncation is unresolved. These results do not prove security resistance |
| Windows clipboard/open actions | Mocked only | Fixed PowerShell command, UTF-8 reading, literal path forwarding, error handling and menu control flow tested on Linux. Detached Notepad Popen arguments, all three DEVNULL streams, closed extra handles and absence of wait/communicate calls are asserted with mocks. Actual clipboard round-trip, Notepad display and terminal isolation remain to be exercised on Windows |
| Real Ollama model assessment | Partial analyst review | Operator scan evidence reviewed as above; no model was scanned by the builder during this patch. No confirmed vulnerability or mitigation result |
| OpenAI | Offline synthetic integration passed | 15 cases with actual Garak 0.17.0/OpenAI SDK 2.54.0/HTTPX 0.28.1 and MockTransport; socket access denied. No live account/model access validated |
| Chroma/embeddinggemma | Unfinished integration | Run/observation exports exist; database and collections have not been accessed or changed |
| Langflow submission | Unfinished integration | Handoff file generation works; no evidence automatically sent |
| Finding/mitigation validation | Unfinished | No analyst-confirmed model vulnerability or successful mitigation claimed |

## Current 0.3.0 validation

See [release notes](patch-0.3.0.md) for current behavior and detailed test boundaries. All 103 unit tests pass. The real installed inventory contains 191 entries; filtering displays 14 supported workloads for each target and excludes unavailable entries from search and pagination. The two-page Back regression uses extra supported synthetic rows to verify state retention after filtering.

Six existing Ollama protocol integrations were rerun successfully for this release. Fifteen OpenAI MockTransport cases passed with socket access denied. A complete synthetic API response confirms only the simulated model-access path. Two distinct probes exercised native report/handoff generation; other available workloads are source-reviewed and constructed offline, not live-validated. No paid call occurred.

Both request caps and spending alerts are optional and OFF by default. Tests cover cap stop/raise/remove, alert Continue/Raise/Stop, incomplete usage, missing/expired rates without blocking, and independence from any credit balance. OpenAI limits are per-run settings; no generation seed/temperature is sent.

The Windows inherited-console path (hidden key entry, optional interactive pauses, process cancellation) and live OpenAI model/probe validation remain unfinished. No user environment, model, database or private configuration was changed by these build tests.

## Historical review Back correction (0.2.1)

All 88 offline tests passed on Linux. The new regression searches a synthetic inventory, goes to page two, selects Davidjl, chooses `B`, verifies that the same filter/page and numbered results reappear, selects WhoIsRiley, and types `RUN`. Before the second selection, it asserts that no run directory, preflight or scanner launch exists. The inventory loads once and the target/main menu is not restarted. Only the second selection reaches the mocked scanner; its synthetic report produces the existing manifest, summary and ATLAS handoff. Cancellation checks also cover lowercase `run`, `yes`, a number and `RUN now`; none launches a scan.

This release changes navigation and confirmation only. The six real Garak CLI integrations and installed-registry checks below were run for 0.2.0, not repeated for 0.2.1. No real model scan or Windows validation was performed for the Back correction.

## Probe browser validation (0.2.0)

The configured interpreter's real Garak registry returned 191 probes. A direct registry comparison and traversal of all ten pages verified complete membership, including inactive entries. All 14 enabled probe/detector pairs were instantiated offline and their actual prompt counts checked against the source-reviewed fixed counts or upper limit; no generator was instantiated and network access was denied.

The real Garak CLI also exercised four browser selections against a synthetic Ollama endpoint: `encoding.InjectBase32` (32 requests), `goodside.WhoIsRiley` (6), `goodside.Tag` (32), and the default-inactive `goodside.Davidjl` (4). The two existing 32-request campaigns passed again. Each test checked model/options, one selected probe, the actual detector, counts and generated evidence/ATLAS artifacts. During development, Tag exposed a CLI restriction on explicit base-detector selection; the final implementation uses its audited native primary-detector path, with extended detectors disabled, and passed the real CLI test.

Workload regression tests confirm that a five-attempt result under an unknown expected count and cap of 32 is not falsely marked short. A known six-attempt corpus returning five is a gap; 33 attempts against a ceiling of 32 is a gap; null/missing outputs remain unscorable. Legacy manifests for the existing 32-prompt campaigns remain compatible.

The new browser has not been exercised on the operator's Windows installation. Linux tests validate menu logic and synthetic Garak execution. Windows clipboard/Notepad adapters are unchanged and their automated checks are mocked. No actual model's security was assessed by these tests.

The synthetic endpoint returns a fixed text response. Its outputs exist solely to test invocation, parameter forwarding, native report parsing and file creation. They do not measure any model's security.

The integration test confirmed the important distinction between requested settings and native report content: Garak 0.17.0's setup writer omits some standalone floats. The runner retains its supplied configuration and marks the threshold's provenance. When analyzing an external report without that information, it records an evidence gap instead of guessing.

Remaining limits include absent wire-level request capture, token usage and truncation reasons, untested Windows process-tree cancellation, and unexercised Windows desktop actions. Errors and incomplete runs are surfaced; native diagnostic output still warrants review.

The patch preserves existing campaign files and generation settings, private configuration, prior evidence and the GitHub publication plan. Browser runs add source checks and workload metadata for their selected probe.

Historical 0.1.4 validation: that release changed the shared handoff renderer and its tests; scanning, profiles and desktop adapters are unchanged. The prompt contains one investigation request, run facts and one line per selected response. It labels input excerpts untrusted, asks for official ATLAS links and allows an insufficient-evidence answer. It states attack success is unverified and behavior is not assessed. Exact full transcripts remain in original records; only declared bounded excerpts appear in the handoff.

Both automatic scan completion and `handoff --regenerate` were exercised offline through the runner, using a synthetic report and mocked scanner. Regeneration preserves native evidence, full extracted records, settings, scan outcome and prior handoff/checksum bytes. A mismatch refuses regeneration before any writes. Copy/open actions use the same finished file, return after one choice, and cannot alter the recorded scan outcome. `--yes` does not prompt, open applications or change the clipboard.

The patched renderer also generated a preview from the supplied exported summary and five observations. It retained their five IDs and original zero detector scores, and reported 32 evaluated responses and zero flags. Excerpts were compared to the saved input strings. This is an export-based preview: the builder did not have the complete native report or a standalone native manifest. No real model scan or Windows desktop validation was performed for this patch. The operator's local regeneration performs native report/manifest reconciliation.
