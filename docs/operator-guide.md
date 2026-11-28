# What do you want to do?

1. [Open a reply and Kumu graph I already have.](#1-open-a-reply-and-kumu-graph-i-already-have)
2. [Send a saved Garak run to ATLAS.](#2-send-a-saved-garak-run-to-atlas)
3. [Run one new Garak scan and read the result.](#3-run-one-new-garak-scan-and-read-the-result)

Use this guide after installing the lab. Each route starts with a fresh window; you do not need yesterday's terminal output. If you have not installed it, start with [Install on Windows and open your first ATLAS reply](install-and-verify.md).

## 1. Open a reply and Kumu graph I already have

**Start in Windows File Explorer.** Reopening a saved reply requires no scan configuration, running Langflow server, API key, or new `SEND`.

### Open the install guide's sample reply

1. Paste `%LOCALAPPDATA%\GarakPlaybook\examples\synthetic-atlas-run\atlas-submissions` into File Explorer's **address bar**, then press **Enter**. If you installed in another location, open `examples\synthetic-atlas-run\atlas-submissions` under that location instead.
2. Open the folder for the submission you want. Each submission has its own dated folder. If there are several, use the [saved record](#choose-the-right-submission) below to identify it; the newest folder may contain a failed attempt.
3. Confirm that **`atlas_response.md` is present**. This is what came back from ATLAS. Right-click it and choose **Open with → Notepad** (under **Choose another app** if needed).
4. In Notepad, find **View Kumu graph**, then **Full Kumu URL (copy into your browser)**. Copy the complete `https://embed.kumu.io/...` address beneath it into your browser's address bar and press **Enter**.

**Finish line:** the saved analysis is open in Notepad and its graph is open in your browser. Match the technique ID and name in the graph to the reply, regardless of punctuation. The observed sample opened to **AML.T0068 (LLM Prompt Obfuscation)**. Context nodes are investigation leads, not additional confirmed findings.

If the reply says **Kumu graph unavailable**, read the analysis and the error in that section. If the folder has no `atlas_response.md`, inspect `submission.json` for its status and error, or choose the correct submission folder. A missing file or path typo is not a reason to repeat `SEND`.

### Choose the right submission

Open **`submission.json`** in Notepad inside a submission folder. This saved record identifies the request and its outcome:

| Field | What to match |
| --- | --- |
| `created_at` | The submission time, recorded in UTC. |
| `run_id` and `run_folder` | The intended run; the install guide's sample has `run_id` `synthetic-example`. |
| `agent_provider` and `agent_model` | The ATLAS Agent you recorded when sending. These are operator-supplied labels. |
| `status` | `response_received_unreviewed` means an analysis reply was received, not that its conclusions are confirmed. |
| `graph.status` | Inside the `graph` object, `graph_received_target_and_coverage_checked` means the returned URL passed the runner's destination and ID checks. |

For otherwise similar submissions, open **`handoff.submitted.md`** in that folder to see the exact handoff sent on that occasion. The run's **`atlas_handoff.md`** is what you sent; `atlas_response.md` is what came back. Keep the saved files unchanged while reviewing them.

### Find a real run or custom storage

**Stay in Windows File Explorer.** A scan's **Evidence folder** is the individual run folder, not the parent containing all your runs.

- With the install guide's default scan configuration, paste `%LOCALAPPDATA%\GarakPlaybook\evidence` into the address bar. Open the dated folder containing `-scan-` for the run you want. Open **`summary.md`** in Notepad to check its probe and results. Open **`atlas_handoff.md`** for the Run ID and model; **`manifest.json`** has the recorded timing and settings if you need to distinguish similar runs.
- If you chose custom storage, open **`config.private.json`** in Notepad from your existing `garak-playbook-private` folder. Read **`evidence_root`** and open that location in File Explorer. The default configuration location is `%LOCALAPPDATA%\GarakPlaybook\garak-playbook-private\config.private.json`; use your existing custom location if different. In JSON, `\\` represents one `\` in a Windows path. This is only a way to locate existing evidence; you do not need to create or change configuration to open it.
- If the configuration moved or no longer exists, search the drive or folder where you stored the lab for **`atlas_response.md`** to find replies, or **`summary.md`** to find saved runs. Open the file's location and check the saved record. A consolidated batch report also links its individual run evidence.

Inside the chosen run, open **`atlas-submissions`**, choose the submission as above, then open `atlas_response.md` and its Kumu URL. If `atlas-submissions` does not exist, that run has no ATLAS submission saved there; use route 2 if you want to send it.

## 2. Send a saved Garak run to ATLAS

Use this route for a **new submission of existing evidence**. It does not run Garak. If you only want yesterday's reply, use [route 1](#1-open-a-reply-and-kumu-graph-i-already-have).

### Find the run and discovery report

**Start in Windows File Explorer.** Find the run using [Find a real run or custom storage](#find-a-real-run-or-custom-storage). For the install sample, use `%LOCALAPPDATA%\GarakPlaybook\examples\synthetic-atlas-run`. Open `atlas_handoff.md` in Notepad to review what will be sent. Copy the run folder's full address for the PowerShell prompt below; do not select its `atlas-submissions` subfolder.

Next, paste `%LOCALAPPDATA%\GarakPlaybook\garak-playbook-private\mcp-discovery` into File Explorer's address bar. If you used custom storage, use its `garak-playbook-private\mcp-discovery` folder. Open the `atlas-mcp-discovery-....json` reports in Notepad and find one with **`status` `discovery_complete`**, **`tool_invocations` `0`**, and **`atlas_agent_v110`** in its tools. Check that its `endpoint` is the project you intend to use. Keep that report's full path, including its filename. Failed discovery reports are not suitable.

If the report was saved elsewhere, search your chosen storage for `atlas-mcp-discovery-*.json`. If none succeeded or the project changed, follow [Step 15](install-and-verify.md#15-check-that-the-runner-can-find-your-atlas-tool) after restarting Langflow below. Its finish line is **`Validated tool: atlas_agent_v110`**. Discovery makes no model request.

### Restart Langflow, then open the saved-run menu

The menu route uses the supplied MITRE flow's expected Kumu destination. If you intentionally configured a different project/map, use the [custom-destination command](#custom-kumu-destination) instead of submitting through this menu.

**Open Ubuntu (WSL).** Follow [Reopen after shutting down or restarting](install-and-verify.md#reopen-after-shutting-down-or-restarting). Wait for Langflow's **Welcome** message and **leave that Ubuntu window open** while sending and waiting for the reply. Use the existing database, account and flow; no new import is needed.

**Open a separate, normal Windows PowerShell window.** Copy the whole block below. It restores its own paths, then asks for the saved run. If you used different checkout or scanner-environment locations, change those assignments to your existing paths first.

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath "$repo\playbook.py" -PathType Leaf)) { throw 'Runner not found. Check your existing checkout path.' }
if (-not (Test-Path -LiteralPath $scannerPython -PathType Leaf)) { throw 'Scanner Python not found. Check its existing path or use Step 4 of the install guide.' }
Set-Location -LiteralPath $repo
$savedRun = (Read-Host 'Paste the saved run Evidence folder path').Trim().Trim('"')
if ([string]::IsNullOrWhiteSpace($savedRun) -or -not (Test-Path -LiteralPath $savedRun -PathType Container)) { throw 'Run folder not found. Check the path and rerun this block.' }
& $scannerPython "$repo\playbook.py" handoff --run-dir $savedRun
```

No private scan configuration is required. The runner prints the saved scan results and the result menu. Respond in this order:

1. At **Selection (Enter to return)**, type **`4`** and press Enter: **Send saved handoff to ATLAS for analysis and Kumu URL**.
2. At **Full path to the completed MCP discovery JSON**, paste the successful report's full file path and press Enter. The runner validates the saved report before continuing. A blank or mistyped path sends nothing; rerun the block above, choose `4`, and enter the correct path.
3. At **ATLAS model provider shown in Langflow**, enter `OpenAI` for the install guide's tested flow.
4. At **ATLAS model name shown in Langflow**, enter `gpt-6.1-sol` for that flow. If your flow differs, enter its actual provider and model. These labels record what you use; they do not change Langflow. **Pressing Enter without a value at either prompt cancels before submission.**
5. Review **ATLAS submission review**: Run ID, endpoint, tool, provider/model, **Expected Kumu project/map**, and the displayed handoff. Submit only the evidence you intend to share with that agent and its model provider.
6. Type uppercase **`SEND`** and press Enter to authorize the submission. Enter without `SEND` cancels.
7. At **Langflow API key (hidden; session only)**, paste your **Langflow “Garak runner” API key** and press Enter. Nothing appears while entering it. This is not your OpenAI key or Langflow password. If you need to create a Langflow key, follow [Step 14](install-and-verify.md#14-enable-mcp-access-and-create-a-langflow-api-key).

**ATLAS can incur model charges.** One submission may cause multiple model/tool calls; the runner does not measure those charges. Keep both terminals open and wait. **Action 4 already requests the analysis and Kumu graph together.** Action 5 is a separate follow-up for intentionally selecting a different set of IDs; it is not the next step after action 4.

### Read the outcome and open the reply

**Stay in Windows PowerShell.** A received analysis with a checked graph prints:

```text
ATLAS status: response_received_unreviewed
ATLAS archive: <submission folder>
Unreviewed ATLAS reply: <path to atlas_response.md>
Kumu status: graph_received_target_and_coverage_checked
Kumu URL: <full URL>
Recorded Garak scan outcome is unchanged.
```

**Finish line:** open the folder printed after **ATLAS archive** in File Explorer, confirm `atlas_response.md` exists, and open it in Notepad. Copy its full Kumu URL into your browser as in [route 1](#1-open-a-reply-and-kumu-graph-i-already-have). Match the technique IDs and names to the saved analysis. The runner's graph checks do not verify browser rendering or confirm a finding.

| If you see | What to do |
| --- | --- |
| `graph_generation_failed` or `graph_validation_failed` under **Kumu status** | Open `atlas_response.md`. The analysis is retained, and **Kumu graph unavailable** explains the error. The console also prints **Kumu error**. Keep the archive; do not automatically repeat `SEND` or choose action 5. |
| `failed_before_tool_call` under **ATLAS status** | Open the archive's `submission.json` and read `error`. For a mistyped key, follow [Step 17 key recovery](install-and-verify.md#if-you-mistype-the-key-during-step-17), including its check that both tool-call attempt counts are zero. |
| `execution_unknown`, a timeout or disconnect after dispatch | Inspect `submission.json` and any saved reply before considering another submission. Check `tool_call_dispatch_attempts`, `recorded_tool_call_attempts`, `error`, and the Langflow terminal. The server may have processed the request or may still be running. Do not assume it stopped or resend automatically. |
| `tool_error_returned`, `response_without_analysis_text`, or `archive_incomplete_after_response` | Keep the archive and inspect `submission.json`, any `atlas_response.md`, and `response.json` if present. A returned response is not necessarily a usable analysis. |

A path typo is recoverable by opening the correct archive; it does not need another `SEND`. If you lost the printed path, look under the selected run's `atlas-submissions` and use [Choose the right submission](#choose-the-right-submission).

**Use the printed ATLAS/Kumu statuses and the saved files for menu action 4.** Its return code is not propagated by the menu. The direct `atlas` command does propagate the submission result; code `2` is a general failure result, not a graph-only signal. See [submission details](#submission-and-protocol-details).

## 3. Run one new Garak scan and read the result

<a id="start-in-windows-powershell"></a>

**Start in normal Windows PowerShell.** This route creates new model-test evidence. Use only a target you own or are authorized to test. OpenAI scanning does not require Langflow or Ollama. For a local Ollama target, open the installed **Ollama** app and ensure your configured model is already installed before running.

### Restore paths and check the private scan configuration

Copy the whole block into the new window. If you chose custom locations, change `$repo`, `$labRoot`, `$scannerPython`, and `$config` to those existing locations. Keep configuration and evidence outside the checkout.

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
$config = Join-Path $labRoot 'garak-playbook-private\config.private.json'
if (-not (Test-Path -LiteralPath "$repo\playbook.py" -PathType Leaf)) { throw 'Runner not found. Check your existing checkout path.' }
if (-not (Test-Path -LiteralPath $scannerPython -PathType Leaf)) { throw 'Scanner Python not found. Check its existing path or use Step 4 of the install guide.' }
Set-Location -LiteralPath $repo
if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { throw 'Scan configuration not found. Follow Create or reuse your private scan configuration in the README, then rerun this block.' }
$scanConfig = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
$scanConfig.targets | Format-List
"Evidence root: $($scanConfig.evidence_root)"
```

**You should see:** configured target names and models, plus the evidence root. If you only completed the sample-to-ATLAS install, scan configuration may not exist yet. Use [Create or reuse your private scan configuration](../README.md#create-or-reuse-your-private-scan-configuration) **in this same PowerShell window**, then rerun the block above. Do not replace an existing configuration just to match an example.

Check the [compatibility table](compatibility.md). The tested Garak targets were **`gpt-5.6-sol`** and **`llama3.2:3b`**. `gpt-6.1-sol` was the **Langflow ATLAS Agent**, a separate role. Access to an OpenAI model depends on your account. Fourteen reviewed probes are enabled; the closed fourteen-probe validation campaign is not a prerequisite for this single scan. The recorded Ollama DAN investigation is closed for v1; do not treat it as a passing pair.

### Review the plan, then use the interactive menu

**Stay in the same Windows PowerShell window.** This first block only prints a plan. At the prompt, type a configured target **name** from the preceding output, for example `openai-reasoning` or `ollama-local`. It plans the included `base64-32` campaign and makes no model request.

```powershell
$target = (Read-Host 'Configured target name to plan').Trim()
if ([string]::IsNullOrWhiteSpace($target)) { throw 'No target entered; no scan started.' }
& $scannerPython "$repo\playbook.py" plan --config $config --target $target --campaign base64-32
if ($LASTEXITCODE -ne 0) { throw 'Plan failed. Read the error and check the target/configuration before continuing.' }
```

Read the target/model, endpoint, probe, detector, output budget and evidence location. Planning does not verify model access. Once the plan is the one you intend, start the menu **in the same window**:

```powershell
& $scannerPython "$repo\playbook.py" menu --config $config
```

1. Under **Target/model profile**, type the displayed **number** for the target you just planned and press Enter. Target numbers depend on your configuration.
2. Type **`1`** for **Existing campaigns**, then select the displayed number for **`base64-32`**. This keeps the scan matched to the plan above. Other probes are available through the [probe browser](#probe-browser-and-scan-controls).
3. Read the final plan again. For OpenAI, check the completion budget and estimated cost; **Estimate unavailable** does not mean free. Type uppercase **`RUN`** and press Enter only when ready. Press Enter without `RUN` to cancel.
4. For OpenAI, enter your **OpenAI scan API key** at the hidden prompt. `RUN` authorizes a paid model-access check followed by the selected probe. This key is different from the Langflow key used in route 2. Local Ollama scans do not use an OpenAI key.
5. Wait for **Execution status** and **Evidence folder**. At the result menu, type **`3`** and press Enter to return to PowerShell and read the evidence first.

### Read the scan result

**Open Windows File Explorer.** Paste the path printed after **Evidence folder** into the address bar. Open **`summary.md`** with Notepad. If the terminal is closed, use [Find a real run or custom storage](#find-a-real-run-or-custom-storage).

| Execution status | Plain-language meaning |
| --- | --- |
| `completed` | The report completed, the scanner exited successfully, and the runner found no evidence/accounting gaps. This does not mean the model is secure. |
| `complete_with_gaps` | The report completed and the scanner exited successfully, but some responses, scores or other required evidence are missing or inconsistent. Review the gaps before interpreting coverage. |
| `incomplete` | The run did not establish a valid completed report and successful scanner exit, for example after an error, interruption or timeout. Partial evidence may still be useful. |
| `process_outcome_unknown` | The report has a matching completion marker, but the scanner's successful exit was not recorded. This is expected for the install guide's synthetic sample, which was not a live scan. |

**Finish line:** you have opened `summary.md` and read the execution status, detector counts and coverage gaps. A **detector flag needs analyst review** of the original prompt and response; it is not confirmed attack success. Zero flags do not prove resistance. Use [Evidence and review](#evidence-and-review) for that review, then [route 2](#2-send-a-saved-garak-run-to-atlas) if you want ATLAS analysis of this run.

## Optional tasks and technical reference

The three routes above cover everyday use. The material below is for a specific follow-up or implementation detail:

- [Unattended local scans and metadata checks](#optional-unattended-scans-and-preflight)
- [Handoff regeneration](#optional-handoff-regeneration)
- [Batch operation](batch.md) and [optional local search](install-and-verify.md#optional-index-and-search-locally)
- [Probe browser and scan controls](#probe-browser-and-scan-controls)
- [Submission and protocol details](#submission-and-protocol-details), including [custom Kumu destinations](#custom-kumu-destination)
- [A separate Kumu view from saved analysis](#optional-kumu-view-from-saved-analysis)
- [Experimental choices](#experimental-choices), [evidence review](#evidence-and-review), and [maintainer tests](#tests-and-validation)
- [Validation scope](#current-scope) and [historical implementation notes](#historical-implementation-notes)

### Optional unattended scans and preflight

**Start in normal Windows PowerShell.** These blocks use the install guide's default paths; substitute your existing custom paths if different. Reuse the private scan configuration checked in route 3.

#### Optional Ollama metadata check (no generation)

Use this only after installing Ollama and the local model configured in `ollama-local`. It reads local metadata and writes preflight evidence; it does not generate a model response.

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
Set-Location -LiteralPath $repo
$config = Join-Path $labRoot 'garak-playbook-private\config.private.json'
& $scannerPython "$repo\playbook.py" preflight --config $config --target ollama-local --campaign base64-32
```

#### Optional unattended live Ollama scan

**This block immediately starts a new local model scan.** `--yes` skips confirmation. Use it only after reviewing that target and campaign's plan and intentionally choosing unattended operation. It does not work for OpenAI scans.

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
Set-Location -LiteralPath $repo
$config = Join-Path $labRoot 'garak-playbook-private\config.private.json'
& $scannerPython "$repo\playbook.py" run --config $config --target ollama-local --campaign base64-32 --yes
```

### Optional handoff regeneration

**Start in normal Windows PowerShell.** Use your existing custom paths if different. Only use this for a saved run whose derived handoff you intentionally want to regenerate. It reconciles the native report with the saved summary, retains the old handoff/checksums as a revision, and then opens the result menu. It does not run a scan.

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
Set-Location -LiteralPath $repo
$savedRun = Read-Host 'Paste the existing run Evidence folder path to regenerate its handoff'
& $scannerPython "$repo\playbook.py" handoff --run-dir $savedRun --regenerate
```

### Probe browser and scan controls

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

### Submission and protocol details

Before invoking `atlas_agent_v110`, the client rechecks the server identity/version and exact tool metadata/schema against discovery. It wraps the existing UTF-8 handoff in an analysis-and-graph request as `input_value`, with a new UUID `session_id`. One `SEND` requests dataset verification and the Graph Generator for every AML ID discussed in the analysis. It does not regenerate the handoff, run Garak, change flow/model settings, or automatically index findings. Original evidence and root checksums remain unchanged. Each submission gets its own directory under `atlas-submissions`, including a byte-identical `handoff.submitted.md`, the full `request_prompt.md`, request, original returned result, unreviewed reply, metadata, exchanges and separate checksums. Existing credential redaction remains in force and is recorded.

The expected destination comes from MITRE's pinned supplied flow: project `99b02113875c5b03b510b4b6968b2566`, map `atlas`. For a different configured Graph Generator destination, use the [custom-destination command](#custom-kumu-destination) below. Expectations are never taken from the returned URL. The runner checks HTTPS, the exact `embed.kumu.io` host, project, map, anchor and focus coverage of every AML ID discussed, including rejected/contextual IDs. It saves the original accepted URL with the readable analysis in `atlas_response.md`. This graph is an index of discussed IDs and one-hop context, not confirmation of mappings. An iframe is unnecessary and is never rendered.

If graph generation or validation fails, the analysis and original response remain archived, the Markdown explains the failure, and the direct `atlas` command returns code `2`. That code also covers other submission or evidence failures; it is not a graph-only signal. The direct command returns `0` for a received analysis with unchanged source files and successful graph checks, or `3` for cancellation. Menu action `4` does not propagate these return codes: `handoff` returns `0` only for a saved scan status of `completed`, otherwise `2`; the post-scan menu preserves the scan result. Use the printed statuses and archive to judge the ATLAS outcome. There is no automatic retry. An accepted response prints `Kumu status: graph_received_target_and_coverage_checked`. That means local URL checks passed; internal dataset/Graph Generator execution remains agent-reported and browser rendering remains unverified. See [acceptance evidence and limits](inline-kumu-acceptance.md).

The client permits one explicit ATLAS tool invocation per action, disables HTTP redirects/proxies and automatic retries, and never executes server-initiated requests or follows returned resources. These client restrictions do not enforce the ATLAS flow's internal tool permissions or limit its upstream model requests. A timeout, disconnect, or interruption after dispatch is **execution unknown**, not proof that server work stopped. Review the archive and server before deciding whether to submit again. `--timeout-seconds` defaults to 300 (range 30–1800); it configures socket waits and response-processing checks, not a hard end-to-end deadline or provider cancellation.

This MCP path supports the discovered Langflow project endpoint on HTTP loopback, `x-api-key`, and protocol `2025-03-26`. OAuth, remote endpoints, arbitrary MCP tools, and unattended submission are outside this interface. `atlas --yes` is rejected. The caller's account ID and key permissions are not exposed by the discovery exchange; the client does not claim to verify their least privilege. The agent may use a cloud LLM even when Langflow itself is local. Costs and effective generation settings of that backend are not independently measured by this client.

### Custom Kumu destination

**Start in normal Windows PowerShell.** Use this only when your Graph Generator intentionally points to a different project or map. First create the [two-field private expected-target configuration](patch-0.4.2.md#private-configuration) from that known destination. Use your existing custom checkout/environment paths if different.

The following direct command replaces the menu route for this case. Locate the run and successful discovery report as in route 2. After the path prompts it asks for the ATLAS provider/model, shows the handoff review, asks for `SEND`, and then requests the hidden Langflow key. It does not submit before confirmation.

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
Set-Location -LiteralPath $repo
$savedRun = Read-Host 'Paste the existing run Evidence folder path'
$discovery = Read-Host 'Paste the successful MCP discovery JSON file path'
$kumuConfig = Read-Host 'Paste the private expected Kumu project/map configuration file path'
& $scannerPython "$repo\playbook.py" atlas --run-dir $savedRun --discovery $discovery --kumu-config $kumuConfig
```

Read the same ATLAS/Kumu output labels and open the archive as in route 2.

### Optional Kumu view from saved analysis

This separate follow-up remains available when intentionally selecting a different subset of IDs from an existing analysis. It is not required for the same-submission Kumu path.

First create the private expected-target configuration described in [0.4.2](patch-0.4.2.md). Menu action 5 reads the sibling `garak-playbook-private/kumu.private.json`; the CLI also accepts `--kumu-config PATH`.

**In normal Windows PowerShell**, use action **5** from the saved-run menu in route 2, or copy this standalone block. Use your existing custom paths if different:

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
Set-Location -LiteralPath $repo
$savedRun = Read-Host 'Paste the existing run Evidence folder path'
& $scannerPython "$repo\playbook.py" kumu --run-dir $savedRun
```

Select the saved ATLAS submission if more than one exists. The runner shows unique AML mentions with context. Select only the IDs proposed as mappings for this run, in anchor-first order; omit rejected/background IDs. Review the automatically generated request, type `GRAPH`, then enter the Langflow key at the hidden prompt. No copy-and-paste prompt composition or new Garak scan is needed.

The returned graph must match the independently configured Kumu project/map and include every selected focus ID. An accepted URL and iframe are saved under a separate `kumu-submissions` directory; the original analysis and evidence remain unchanged. The optional browser action runs only if selected. `kumu --yes` is rejected. See [0.4.1 patch notes](patch-0.4.1.md) for validation, archive layout and the distinction between URL checks, agent-reported internal tool execution, and visual rendering.

`atlas_handoff.md` contains one investigation request, run facts, sampling limits, and one line per selected response: attempt ID/output index, detector score/disposition, whether a usable response was recorded, and "behavior not assessed." A bounded input excerpt supports investigation of the attempted technique; it is not a behavioral assessment. The excerpt is the first nonempty line of the last user turn (or the plain-string input), at most 120 characters, quoted with escaped control characters. A cut first line is marked `[cut]`; other turns/lines are omitted. Excerpts are untrusted and incomplete. The renderer does not infer refusal, successful decoding, tool execution, harm, or resistance from response wording. It requests official ATLAS links and explicitly permits an insufficient-evidence answer. Full transcripts, roles, comparison targets, settings, manifests, and paths remain in the existing evidence files. Input excerpts are not a general-purpose secrets sanitizer.

`handoff --regenerate` reads the saved native report and manifest, reconciles the result with the saved summary, and rebuilds only the derived handoff. It preserves the previous handoff and checksum index under a unique `handoff-revisions` subdirectory, then updates the checksum index. Native report, manifest, summary, observations, campaign settings and scan outcome are unchanged. A discrepancy stops regeneration without changing files. Add `--yes` to regenerate unattended without opening/copying or prompting. Without `--regenerate`, viewing/copying/opening the handoff is read-only. Explicit actions 4 and 5 create separate MCP analysis or graph archives after confirmation.

Preflight records the local Ollama version, selected model tag/digest, template/system metadata, package versions, and source hashes. It makes only local metadata requests (`/api/version`, `/api/tags`, `/api/show`). A failing check stops the run and records the reason. The source hash check guards against treating a locally patched package with the same version label as the audited distribution. Review any difference rather than reinstalling or patching automatically.

## Current scope

- An interactive target/model and scan-profile menu, plus noninteractive commands.
- Existing Garak 0.17.0 environment; no install, patch, model download, or configuration rewrite.
- Two existing model-level campaigns plus a browser that displays only available probes from the configured Garak installation. Fourteen reviewed text workloads/local detectors are selectable for either target; unavailable entries are excluded before search and pagination. Availability is permission to test, not proof of model/probe compatibility.
- Native Garak report, hit log when flags exist, native HTML when generated, captured console, configuration and model metadata.
- Separate reporting of detector flags and execution gaps, with original evidence references.
- A locally generated `atlas_handoff.md`; optional MCP transmission requires a separate explicit `SEND` confirmation.
- A structured run record and response observations for later research indexing.

Chroma research indexing is optional; it does not mark a run as an analyst-confirmed finding. Analyst disposition editing, general comparison workflows and adaptive PyRIT scenarios remain deferred. The narrow encoding headroom comparison is implemented; Windows full validation at `09e8128` and delta validation at `4fedd3f` passed. No application, agent, or RAG target is required for these model scans.

The [release record](release-v1.md) is authoritative for validation. The assisted Windows walkthrough passed; an independent guide-only installation remains unverified. The [observed AML.T0068 result](inline-kumu-acceptance.md) includes the saved analysis, URL and matching browser view. Optional [batch execution](batch.md) produces consolidated coverage reports. Optional [local search](install-and-verify.md#optional-index-and-search-locally) uses Chroma and EmbeddingGemma to index existing runs. Indexing, repeat indexing, filters, search and evidence opening were observed on Windows for one saved run; broader retrieval quality remains unverified.

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

**In normal Windows PowerShell**, you can analyze an existing 0.17.0 report without invoking a model. Use your existing custom paths if different:

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
Set-Location -LiteralPath $repo
$nativeReport = Read-Host 'Paste the existing native Garak report file path'
$analysisFolder = Read-Host 'Paste a new analysis folder path outside the repository'
& $scannerPython "$repo\playbook.py" summarize --report $nativeReport --out $analysisFolder
```

The analysis folder must not already exist. Original bytes are untouched. If the original report lacks required setup information, the parser records the missing information instead of inventing settings. A report analyzed without a recorded successful process outcome receives `process_outcome_unknown` when its completion marker is otherwise valid. Supply `--manifest` with that run's retained manifest to include its process outcome. Do not call an old report a replay or a new scan.

## Tests and validation

**Maintainers, in normal Windows PowerShell:** use your existing checkout path if different.

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
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
