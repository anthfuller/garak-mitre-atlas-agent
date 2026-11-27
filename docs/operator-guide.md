# Operator guide: Garak evidence and the MITRE ATLAS Agent

Run a defined Garak campaign, retain original evidence, check execution quality, and investigate candidate mappings with your MITRE ATLAS Agent in Langflow. The runner generates the handoff and can submit it over authenticated MCP after confirmation. Start with the [Install on Windows and open your first ATLAS reply](install-and-verify.md); the [release record](release-v1.md) is authoritative for current validation. Older patch notes describe the status at their original checkpoints.

One `SEND` requests ATLAS analysis and a full Kumu URL together. The [observed AML.T0068 result](inline-kumu-acceptance.md) includes the saved analysis, URL and matching browser view. A graph failure preserves the analysis and error. The assisted Windows walkthrough passed; an independent guide-only installation remains unverified.

Optional [batch execution](batch.md) produces consolidated coverage reports. Optional [local search](install-and-verify.md#optional-index-and-search-locally) uses Chroma and EmbeddingGemma to index existing runs. Indexing, repeat indexing, search, filters and evidence opening were observed on Windows for one saved run; broader retrieval quality remains unverified.

## Current scope

- An interactive target/model and scan-profile menu, plus noninteractive commands.
- Existing Garak 0.17.0 environment; no install, patch, model download, or configuration rewrite.
- Two existing model-level campaigns plus a browser that displays only available probes from the configured Garak installation. Fourteen reviewed text workloads/local detectors are selectable for either target; unavailable entries are excluded before search and pagination. Availability is permission to test, not proof of model/probe compatibility.
- Native Garak report, hit log when flags exist, native HTML when generated, captured console, configuration and model metadata.
- Separate reporting of detector flags and execution gaps, with original evidence references.
- A locally generated `atlas_handoff.md`; optional MCP transmission requires a separate explicit `SEND` confirmation.
- A structured run record and response observations for later research indexing.

Chroma research indexing is optional; it does not mark a run as an analyst-confirmed finding. Analyst disposition editing, general comparison workflows and adaptive PyRIT scenarios remain deferred. The narrow encoding headroom comparison is implemented; Windows full validation at `09e8128` and delta validation at `4fedd3f` passed. No application, agent, or RAG target is required for these model scans.

## Start in Windows PowerShell

Use normal **Windows PowerShell** and the checkout and scanner environment created by the [install guide](install-and-verify.md). If scan configuration does not exist yet, complete [Create or reuse your private scan configuration](../README.md#create-or-reuse-your-private-scan-configuration) first. Keep that configuration and evidence outside the repository.

### Restore paths (no scan)

Copy this block into a new PowerShell window. If you chose different storage during installation, keep those existing paths.

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
$config = Join-Path $labRoot 'garak-playbook-private\config.private.json'
Set-Location -LiteralPath $repo
if (-not (Test-Path -LiteralPath $scannerPython)) { throw 'Complete Step 4 of the install guide first.' }
if (-not (Test-Path -LiteralPath $config)) { throw 'Create the private scan configuration using the README first.' }
```

### Plan only

In the same window, this block prints the OpenAI Base64 plan. It makes no model request and starts no scan. Use a different configured target only when intended.

```powershell
& $scannerPython "$repo\playbook.py" plan --config $config --target openai-reasoning --campaign base64-32
```

### Optional Ollama metadata check (no generation)

Use this only after installing Ollama and the local model configured in `ollama-local`. It reads local metadata and writes preflight evidence; it does not generate a model response.

```powershell
& $scannerPython "$repo\playbook.py" preflight --config $config --target ollama-local --campaign base64-32
```

### Interactive scan menu

Stay in the same window. Type the displayed target number and press Enter, then choose a campaign or probe. Review the plan and type uppercase `RUN` only when ready to start the scan. OpenAI asks for its API key through a hidden prompt after confirmation.

```powershell
& $scannerPython "$repo\playbook.py" menu --config $config
```

Read **Execution status** and **Evidence folder** when the scan finishes. For optional multi-probe operation, see [batch commands and per-pair results](batch.md).

### Optional unattended live Ollama scan

**This block immediately starts a new local model scan.** `--yes` skips confirmation. Use it only after reviewing that target and campaign's plan and intentionally choosing unattended operation. It does not work for OpenAI scans.

```powershell
& $scannerPython "$repo\playbook.py" run --config $config --target ollama-local --campaign base64-32 --yes
```

### Access a saved handoff

Paste an existing run's **Evidence folder** path at the prompt. This opens the result menu; submission requires choosing action 4 and confirming `SEND`.

```powershell
$savedRun = Read-Host 'Paste the existing run Evidence folder path'
& $scannerPython "$repo\playbook.py" handoff --run-dir $savedRun
```

### Optional handoff regeneration

Only use this for a saved run whose derived handoff you intentionally want to regenerate. It reconciles the native report with the saved summary, retains the old handoff/checksums as a revision, and then opens the result menu. It does not run a scan.

```powershell
$savedRun = Read-Host 'Paste the existing run Evidence folder path to regenerate its handoff'
& $scannerPython "$repo\playbook.py" handoff --run-dir $savedRun --regenerate
```

After choosing the target/model, the scan menu offers:

```text
[1] Existing campaigns
[2] Browse or search all installed probes
[3] Exit
```

The browser reads the configured Garak interpreter's registry, including inactive probes, and filters for reviewed workloads before displaying results. It shows up to 20 available entries per page with descriptions. Use `N`/`P` for pages, `S` to search by name/family, `A` to clear the search, or `B`/Enter for the main menu. Numbers refer to the current page. Unavailable probes do not appear in results or page counts.

Selecting a supported probe displays its exact target/model, endpoint, probe, detector, workload basis, limits, settings and additional API/dependency requirements. **It does not launch a scan. Type `RUN` to start.** At this review screen, `B` returns to the same search results and page so another probe can be selected without restarting. Enter, any other response, Ctrl+C or EOF cancels and returns to the shell without creating a run or launching Garak. There is no profile-saving or automatic campaign launch in this browser.

The installed inventory is broader than runner support. Hidden entries are not configured/reviewed for this runner; this does not mean Garak itself cannot run them. The included compatibility policy and limitations are listed in [the browser patch notes](patch-0.2.0.md). Inventory inspection creates and removes a temporary cache under the configured artifacts directory; it performs no target access or generation and does not instantiate probes. A failed registry read reports an error, never a silently partial catalog.

Choose OpenAI by its displayed target number. The scan uses `openai.OpenAIReasoningGenerator`; `gpt-5.6-sol` is the example with live evidence in the compatibility table, subject to account access. The configured scan model is separate from the ATLAS Agent model (`gpt-6.1-sol` in the install guide). The profile is added in memory; private configuration is not rewritten. Account/model access stays unverified until a complete compatibility response is received. That check is not probe-compatibility validation.

The OpenAI review offers `L` for `max_completion_tokens` (includes reasoning and visible output). The default is 20,000 only for `gpt-5.6-sol` with Ascii85, Base32 and Base64, and 1,500 for other probes/model IDs; explicit limits take precedence. It also offers `R` to set/raise/remove an optional request cap, `A` for an optional spending alert, and `P` to supply pricing. Both optional controls are OFF by default. The existing logical workload and wall-time limits still apply. No generation temperature or seed is sent; seed 42 is used for probe sampling. Changes apply only to the selected run and are shown again before `RUN`.

Before `RUN`, a conservative total-cost estimate uses offline input-size estimates, the completion limit, and dated published or supplied rates. If rates/input estimation are unavailable, the review says **Estimate unavailable** and still permits `RUN`. The bundled promotional rates expire November 30, 2026; no automatic live pricing query occurs. Usage-based running estimates include the compatibility check and all reported responses. Missing usage is identified; costs are not invoices or a dollar cap. No account credit balance is read or converted into a runner limit.

`RUN` explicitly authorizes one paid compatibility generation followed by the selected probe. The child reads the API key with hidden terminal input, rejects echo fallback, and retains it only for that process. Keys are not supplied in argv, configuration, evidence or the inherited environment. The fixed HTTPS endpoint, disabled SDK retries, request counter, and source/config checks apply to both the compatibility request and scan. HTTP errors stop the run. No automatic retry is performed. Request-cap changes and alert decisions are recorded.

At a configured request cap, the runner pauses before another request and offers **Raise request cap / Remove request cap / Stop**. At an optional spending alert it offers **Continue (one more request) / Raise alert / Stop**. Alert thresholds require usable rates and reported usage; missing usage can understate the running total. These are independent controls. The wall-time limit continues while waiting for operator input.

OpenAI is interactive in this release: `run --yes` for OpenAI fails before prompting or sending requests. Ollama `--yes` and handoff `--yes` remain unchanged. The parent launches the child with the inherited console so hidden key entry and optional pauses work. The operator has exercised the OpenAI path on Windows; this does not validate every probe or failure path.

After saving a scan, the runner prints execution status, evaluated-response and flag counts for each probe/detector pair, the unique flagged-response count, and the full `atlas_handoff.md` path. Detector counts are kept separate to avoid double counting. Interactive runs then offer:

```text
[1] Copy ATLAS prompt and return to PowerShell
[2] Open ATLAS prompt in Notepad and return to PowerShell
[3] Return to PowerShell
[4] Send saved handoff to ATLAS for analysis and Kumu URL (review and confirmation required)
[5] Generate Kumu view from saved ATLAS analysis (review and confirmation required)
```

Copy reads only the existing UTF-8 prompt file through Windows PowerShell. Open launches `System32\notepad.exe` explicitly, detached from the console, with stdin/stdout/stderr redirected to DEVNULL and no wait for editor closure. After copying or launching, the runner prints one confirmation and exits. Enter, 3, EOF or Ctrl+C also exits; an invalid selection prints a message and exits. Errors are shown with the file path and do not change saved evidence or the recorded scan outcome. The runner confirms launch acceptance, not visual rendering by the editor.

At completion, `run --yes` and `handoff --yes` print the result summary and path without prompts, application opening or clipboard change. `handoff` also avoids interaction when stdin is not a terminal. Nothing is automatically submitted to ATLAS. Sampling is unchanged: first five flagged responses, or first five observations when none are flagged.

### Optional ATLAS submission

Use option 4 at scan completion or in `handoff`, or use the `atlas` command for an existing run. The direct command requires no Garak configuration changes:

```powershell
$savedRun = Read-Host 'Paste the existing run Evidence folder path'
$discovery = Read-Host 'Paste the successful Discovery report path from Step 15'
& $scannerPython "$repo\playbook.py" atlas --run-dir $savedRun --discovery $discovery
```

The operator supplies a completed authenticated discovery report and the provider/model observed in the ATLAS flow. Omitted values are requested interactively. For the Step 13 setup, enter `OpenAI` for provider and `gpt-6.1-sol` for model. Follow [Steps 14–18](install-and-verify.md#14-enable-mcp-access-and-create-a-langflow-api-key) if discovery is not complete. Pressing Enter at either provider/model prompt cancels before submission. These labels record provenance; they do not override model configuration. The runner displays the endpoint, tool, run, handoff hash, full saved handoff, and cost limitation. Only uppercase `SEND` authorizes submission. The Langflow API key is then requested with hidden input; it is not accepted in CLI arguments, profiles, or the handoff.

Before invoking `atlas_agent_v110`, the client rechecks the server identity/version and exact tool metadata/schema against discovery. It wraps the existing UTF-8 handoff in an analysis-and-graph request as `input_value`, with a new UUID `session_id`. One `SEND` requests dataset verification and the Graph Generator for every AML ID discussed in the analysis. It does not regenerate the handoff, run Garak, change flow/model settings, or automatically index findings. Original evidence and root checksums remain unchanged. Each submission gets its own directory under `atlas-submissions`, including a byte-identical `handoff.submitted.md`, the full `request_prompt.md`, request, original returned result, unreviewed reply, metadata, exchanges and separate checksums. Existing credential redaction remains in force and is recorded.

The expected destination comes from MITRE's pinned supplied flow: project `99b02113875c5b03b510b4b6968b2566`, map `atlas`. For a different configured Graph Generator destination, pass `atlas --kumu-config PATH` using the [two-field private configuration](patch-0.4.2.md). Expectations are never taken from the returned URL. The runner checks HTTPS, the exact `embed.kumu.io` host, project, map, anchor and focus coverage of every AML ID discussed, including rejected/contextual IDs. It saves the original accepted URL with the readable analysis in `atlas_response.md`. This graph is an index of discussed IDs and one-hop context, not confirmation of mappings. An iframe is unnecessary and is never rendered.

If graph generation or validation fails, the analysis and original response remain archived, the Markdown explains the failure, and the command exits with code 2. It does not retry. An accepted response prints `Kumu status: graph_received_target_and_coverage_checked`. That means local URL checks passed; internal dataset/Graph Generator execution remains agent-reported and browser rendering remains unverified. See [acceptance evidence and limits](inline-kumu-acceptance.md).

The client permits one explicit ATLAS tool invocation per action, disables HTTP redirects/proxies and automatic retries, and never executes server-initiated requests or follows returned resources. These client restrictions do not enforce the ATLAS flow's internal tool permissions or limit its upstream model requests. A timeout, disconnect, or interruption after dispatch is **execution unknown**, not proof that server work stopped. Review the archive and server before deciding whether to submit again. `--timeout-seconds` defaults to 300 (range 30–1800); it configures socket waits and response-processing checks, not a hard end-to-end deadline or provider cancellation.

This MCP path supports the discovered Langflow project endpoint on HTTP loopback, `x-api-key`, and protocol `2025-03-26`. OAuth, remote endpoints, arbitrary MCP tools, and unattended submission are outside this interface. `atlas --yes` is rejected. The caller's account ID and key permissions are not exposed by the discovery exchange; the client does not claim to verify their least privilege. The agent may use a cloud LLM even when Langflow itself is local. Costs and effective generation settings of that backend are not independently measured by this client.

### Optional Kumu view from saved analysis

This separate follow-up remains available when intentionally selecting a different subset of IDs from an existing analysis. It is not required for the same-submission Kumu path.

First create the private expected-target configuration described in [0.4.2](patch-0.4.2.md). Menu action 5 reads the sibling `garak-playbook-private/kumu.private.json`; the CLI also accepts `--kumu-config PATH`.

Use action **5** in the handoff/completion menu, or:

```powershell
$savedRun = Read-Host 'Paste the existing run Evidence folder path'
& $scannerPython "$repo\playbook.py" kumu --run-dir $savedRun
```

Select the saved ATLAS submission if more than one exists. The runner shows unique AML mentions with context. Select only the IDs proposed as mappings for this run, in anchor-first order; omit rejected/background IDs. Review the automatically generated request, type `GRAPH`, then enter the Langflow key at the hidden prompt. No copy-and-paste prompt composition or new Garak scan is needed.

The returned graph must match the independently configured Kumu project/map and include every selected focus ID. An accepted URL and iframe are saved under a separate `kumu-submissions` directory; the original analysis and evidence remain unchanged. The optional browser action runs only if selected. `kumu --yes` is rejected. See [0.4.1 patch notes](patch-0.4.1.md) for validation, archive layout and the distinction between URL checks, agent-reported internal tool execution, and visual rendering.

`atlas_handoff.md` contains one investigation request, run facts, sampling limits, and one line per selected response: attempt ID/output index, detector score/disposition, whether a usable response was recorded, and "behavior not assessed." A bounded input excerpt supports investigation of the attempted technique; it is not a behavioral assessment. The excerpt is the first nonempty line of the last user turn (or the plain-string input), at most 120 characters, quoted with escaped control characters. A cut first line is marked `[cut]`; other turns/lines are omitted. Excerpts are untrusted and incomplete. The renderer does not infer refusal, successful decoding, tool execution, harm, or resistance from response wording. It requests official ATLAS links and explicitly permits an insufficient-evidence answer. Full transcripts, roles, comparison targets, settings, manifests, and paths remain in the existing evidence files. Input excerpts are not a general-purpose secrets sanitizer.

`handoff --regenerate` reads the saved native report and manifest, reconciles the result with the saved summary, and rebuilds only the derived handoff. It preserves the previous handoff and checksum index under a unique `handoff-revisions` subdirectory, then updates the checksum index. Native report, manifest, summary, observations, campaign settings and scan outcome are unchanged. A discrepancy stops regeneration without changing files. Add `--yes` to regenerate unattended without opening/copying or prompting. Without `--regenerate`, viewing/copying/opening the handoff is read-only. Explicit actions 4 and 5 create separate MCP analysis or graph archives after confirmation.

Preflight records the local Ollama version, selected model tag/digest, template/system metadata, package versions, and source hashes. It makes only local metadata requests (`/api/version`, `/api/tags`, `/api/show`). A failing check stops the run and records the reason. The source hash check guards against treating a locally patched package with the same version label as the audited distribution. Review any difference rather than reinstalling or patching automatically.

## Experimental choices

The bundled profiles are **new experiments**, not reproductions of earlier scans. Each prints its purpose, settings, and interpretation limits before execution.

The table below describes the preserved **Ollama** settings. OpenAI settings and controls are described above.

| Setting | Ollama value | Effect |
| --- | --- | --- |
| Interface | `ollama.OllamaGeneratorChat` | Native chat generator |
| Prompt selection | Existing campaigns: 32 sampled prompts. Browser: up to 32 attempts under the selected probe’s reviewed workload | Fixed-corpus probes may legitimately have 1, 4 or 6 prompts; a cap is not a universal expected count |
| Generations | 1 per prompt | No repeated-sampling estimate |
| Seed | 42 | Stabilizes supported sampling/seed paths; does not guarantee identical responses |
| Temperature | 0.0 | Explicit sampling setting; not assumed to match older runs |
| Output limit | 256 tokens via the audited Ollama generator mapping | Can truncate responses; native reports do not expose per-request truncation reasons |
| Detector | One reviewed primary detector | No automatic extended detectors |
| Evaluation threshold | 0.5, inclusive for flags | Native score threshold, not analyst severity |
| Parallelism | 1 request / 1 attempt | Sequential local workload |
| Maximum elapsed run time | 30 minutes | Stops the scanner process tree; interrupted evidence is marked incomplete |
| Configuration | Unique per-run `XDG_CONFIG_HOME` | Existing site configuration is excluded without being edited |
| Proxies | Omitted in scanner child environment | Local endpoint calls bypass ambient proxy settings; parent shell unchanged |
| System prompt | None added by the runner | Model-level system/template metadata is captured; probe prompts remain part of the experiment |
| Deprefixing | Disabled | Avoids that optional Garak output transformation |
| Confidence intervals | Disabled | Does not imply statistical confidence from a small convenience sample |

The existing Ollama prompt cap is source-verified for the two shipped campaigns; browser workload limits are validated separately. It is **not a hard HTTP request or spend cap**: The audited Ollama path can retry successful empty responses (up to three calls); it stops on HTTP errors or transport failures without retrying. OpenAI has a separate optional request counter/cap and aborts HTTP failures. Do not reuse these workload assumptions for arbitrary probes. A wall-clock stop is also not proof that an already accepted inference stopped on the server.

`base64-32` screens for encoded-payload emission using `encoding.InjectBase64` and `encoding.DecodeMatch`. Its payload mix includes benign text, renderable strings, and offensive terms. Decoding or quoting a string is not automatically a vulnerability. The analyst must identify the security requirement and actual violating behavior.

`dan-wild-32` screens a sampled set of existing jailbreak prompts using `dan.DanInTheWild` and `mitigation.MitigationBypass`. Missing a recognized refusal phrase or acknowledging a role-play does not establish attack success. No dynamic attack LLM is used.

## Evidence and review

Each run receives a unique directory. Existing evidence is not overwritten. See [Evidence schema](evidence.md) for the output inventory and limitations.

1. Read `summary.md` and `console.log`. Resolve coverage gaps before treating the run as complete.
2. Review original prompts, outputs and conversations through the references in `observations.jsonl`.
3. Separate true behavioral violations from quotation, refusal, benign decoding, and detector artifacts.
4. Reproduce candidate behavior under comparable settings. A changed interface, prompt, model digest, token budget or detector is a modified experiment.
5. Use menu option 4 to submit the saved handoff to your configured ATLAS Agent after reviewing its destination and confirming `SEND`. Open the archived analysis and Kumu URL as described in [Steps 17–18](install-and-verify.md#17-send-the-sample-handoff-to-atlas), and verify official ATLAS references. Option 1 remains available for manual copy/paste into an agent; save that reply separately.
6. Record attack success and legitimate-task completion separately. This release initializes both to `not_assessed`.

You can analyze an existing 0.17.0 report without invoking a model:

```powershell
$nativeReport = Read-Host 'Paste the existing native Garak report file path'
$analysisFolder = Read-Host 'Paste a new analysis folder path outside the repository'
& $scannerPython "$repo\playbook.py" summarize --report $nativeReport --out $analysisFolder
```

The analysis folder must not already exist. Original bytes are untouched. If the original report lacks required setup information, the parser records the missing information instead of inventing settings. A report analyzed without a recorded successful process outcome receives `process_outcome_unknown` when its completion marker is otherwise valid. Supply `--manifest` with that run's retained manifest to include its process outcome. Do not call an old report a replay or a new scan.

## Tests and validation

```powershell
Set-Location -LiteralPath $repo
$testPython = Read-Host 'Paste the Python executable path for your separate test environment with requirements-research.txt installed'
& $testPython -m unittest discover -s tests -v
```

Use a separate test environment, as described in [maintainer Windows checks](clean-windows.md); do not add test dependencies to the scanner environment. These tests use synthetic records, not model findings. `tests/integration_stub.py` optionally exercises the real Garak CLI against a synthetic local protocol server; it does not run an LLM. See [Validation](validation.md).

## Public distribution

Keep private configuration and all evidence outside Git. The allowlist in `docs/public-file-list.txt` records the intended public files; inspect the final tracked tree and all history reachable from the release branch before publishing. The same boundary applies to GitHub release attachments. Anything marked `NOGIT` or private, outer review ZIPs, Git bundles, `PRIVATE-REVIEW/`, receipts/logs, real transcripts and IDs, keys, private endpoints/configs/paths, databases, models and environments remain outside both. Reviewed generic configs, synthetic fixtures and the sanitized worked example are permitted. `.gitignore` alone is not a sanitizer. No real lab evidence is included in this public source folder. The original project files use the MIT license in the repository root.

## Sources inspected

- Garak 0.17.0 wheel from PyPI, with selected hashes in `source-audit.json`.
- Garak CLI, configuration, native attempt and evaluator implementation in that exact distribution.
- [Garak reporting](https://reference.garak.ai/en/stable/reporting.html); newer docs are background, not a substitute for versioned source.
- [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md), for the local metadata endpoints.
- [Official ATLAS data](https://github.com/mitre-atlas/atlas-data), for candidate-mapping verification.
- [Windows PowerShell Set-Clipboard](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/set-clipboard?view=powershell-5.1), for copying text rather than a file object.
- [Python subprocess](https://docs.python.org/3/library/subprocess.html) and [Windows process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags), for detached Notepad launching and standard-stream isolation.

## Historical implementation notes

These records describe earlier versions. Use the current install guide and commands above for operation.

- [Version 0.1.1 notes](patch-0.1.1.md): child cleanup and execution-status corrections.
- [Version 0.2.0 notes](patch-0.2.0.md) and [0.2.1 notes](patch-0.2.1.md): probe browsing and Back navigation.
- [Version 0.3.0 notes](patch-0.3.0.md): available-probe filtering and OpenAI controls.
- [Version 0.4.0 notes](patch-0.4.0.md): authenticated MCP submission and its original validation limits.
- [Version 0.4.1 notes](patch-0.4.1.md) and [0.4.2 notes](patch-0.4.2.md): separate graph requests and independently configured project/map checks.
- [Version 0.5.0 notes](patch-0.5.0.md): the initial optional local search implementation. Use [current search setup](install-and-verify.md#optional-index-and-search-locally) for installation.
