# Operator guide: Garak evidence and the MITRE ATLAS Agent

Run a defined Garak campaign, retain original evidence, check execution quality, and investigate candidate mappings with your MITRE ATLAS Agent in Langflow. The runner generates the handoff and can submit it over authenticated MCP after confirmation. Start with the [Windows quick start](../README.md#windows-quick-start); the [release record](release-v1.md) is authoritative for current validation. Older patch notes describe the status at their original checkpoints.

The v1 candidate retains [batch execution and consolidated coverage reports](batch.md). Release 0.5.0 added optional **local Chroma research indexing and search of existing runs**, using explicit Ollama EmbeddingGemma embeddings. Private paths remain outside the source. See [research setup, commands and validation limits](patch-0.5.0.md). One saved-run Windows checkpoint with real local EmbeddingGemma is operator-exercised; broader retrieval-quality validation remains pending.

Release 0.4.2 binds Kumu validation to an independently configured expected project and map. It also adds offline `kumu-validate` for existing graph archives. See [0.4.2 correction](patch-0.4.2.md).

Release 0.4.1 adds **optional Kumu generation from saved ATLAS analysis**. See [0.4.1 patch notes](patch-0.4.1.md). The runner generates the graph request, reviews the selected IDs with the operator, and checks returned focus coverage before offering to open the link. The operator exercised one live Windows graph request and supplied screenshots showing both selected focus IDs; internal dataset/tool execution remains agent-reported.

Release 0.4.0 adds **explicit ATLAS submission over authenticated local MCP** to the existing Ollama/OpenAI runner. The Windows scan paths and Copy/Notepad workflow have operator-reported exercise; broader probe compatibility remains unvalidated. Authenticated MCP discovery has been exercised on Windows. One real Windows ATLAS submission has now been exercised: the archived input hash, run ID, conversation ID and five returned attempt IDs matched. Broader server-side context isolation and internal tool authorization remain unverified. See [0.4.0 patch notes](patch-0.4.0.md) for exact validation boundaries.

Version 0.1.1 corrects child cleanup after exceptional exits and execution-status classification. See [Patch notes](patch-0.1.1.md). Campaign settings are unchanged.

Version 0.2.0 adds an installed-probe browser with search, twenty results per page, support reasons and a review-before-run step. The concise ATLAS handoff and Copy/Notepad actions are unchanged. Version 0.2.1 adds `B: Back` at probe review, retaining the same search results and page. Version 0.3.0 hides unavailable probes and adds OpenAI controls. See [Current patch notes](patch-0.3.0.md).

## Current scope

- An interactive target/model and scan-profile menu, plus noninteractive commands.
- Existing Garak 0.17.0 environment; no install, patch, model download, or configuration rewrite.
- Two existing model-level campaigns plus a browser that displays only available probes from the configured Garak installation. Fourteen reviewed text workloads/local detectors are selectable for either target; unavailable entries are excluded before search and pagination. Availability is permission to test, not proof of model/probe compatibility.
- Native Garak report, hit log when flags exist, native HTML when generated, captured console, configuration and model metadata.
- Separate reporting of detector flags and execution gaps, with original evidence references.
- A locally generated `atlas_handoff.md`; optional MCP transmission requires a separate explicit `SEND` confirmation.
- A structured run record and response observations for later research indexing.

Chroma research indexing is optional; it does not mark a run as an analyst-confirmed finding. Analyst disposition editing, general comparison workflows and adaptive PyRIT scenarios remain deferred. The narrow encoding headroom comparison is implemented; Windows full validation at `09e8128` and delta validation at `4fedd3f` passed. Publication remains subject to owner approval. No application, agent, or RAG target is required for these model scans.

## Start in Windows PowerShell

Keep the public source folder, private configuration, and evidence directories separate. Copy `examples/config.example.json` to a location outside this source folder, then edit the absolute paths for your machine. The public distribution includes no personal configuration. Use tools/configure.py or edit a private copy.

Use the Python executable from your working Garak environment. The parent runner uses the Python standard library. Inventory inspection runs a helper through the configured Garak Python and uses its installed registry API. An active environment is optional because the commands below name the executable explicitly. Use Python 3.11 or later; the selected Garak installation must meet Garak's own Python requirements.

All examples in this section belong in **Windows PowerShell**, as a normal user:

```powershell
# Example paths: replace them with your local configuration and source locations.
$labPython = "C:\AI-Lab\garak-env\Scripts\python.exe"
$runnerPath = "D:\AI-Lab\projects\garak-playbook\playbook.py"
$profilePath = "D:\AI-Lab\private\config.private.json"

# Show the resolved plan: no network calls and no files written.
& $labPython $runnerPath plan --config $profilePath --target ollama-local --campaign base64-32

# Inspect versions, selected source files, and local model metadata; zero generation calls.
& $labPython $runnerPath preflight --config $profilePath --target ollama-local --campaign base64-32

# After reviewing the plan, run the interactive selector.
& $labPython $runnerPath menu --config $profilePath

# Explicit unattended run. --yes starts the selected new experiment without prompting.
& $labPython $runnerPath run --config $profilePath --target ollama-local --campaign base64-32 --yes

# Access an existing run; only choosing action 4 and confirming SEND can submit it.
& $labPython $runnerPath handoff --run-dir "D:\AI-Lab\evaluations\<existing-run-folder>"

# Explicitly regenerate only the handoff using saved native evidence, then show the same menu.
& $labPython $runnerPath handoff --run-dir "D:\AI-Lab\evaluations\<existing-run-folder>" --regenerate
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

OpenAI appears as target option 2 after the first Ollama profile, using `openai.OpenAIReasoningGenerator` and initial model `gpt-5.6-sol`. The profile is added in memory; private configuration is not rewritten. Account/model access stays unverified until a complete compatibility response is received. That check is not probe-compatibility validation.

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
[4] Send saved handoff to ATLAS over MCP (review and confirmation required)
[5] Generate Kumu view from saved ATLAS analysis (review and confirmation required)
```

Copy reads only the existing UTF-8 prompt file through Windows PowerShell. Open launches `System32\notepad.exe` explicitly, detached from the console, with stdin/stdout/stderr redirected to DEVNULL and no wait for editor closure. After copying or launching, the runner prints one confirmation and exits. Enter, 3, EOF or Ctrl+C also exits; an invalid selection prints a message and exits. Errors are shown with the file path and do not change saved evidence or the recorded scan outcome. The runner confirms launch acceptance, not visual rendering by the editor.

At completion, `run --yes` and `handoff --yes` print the result summary and path without prompts, application opening or clipboard change. `handoff` also avoids interaction when stdin is not a terminal. Nothing is automatically submitted to ATLAS. Sampling is unchanged: first five flagged responses, or first five observations when none are flagged.

### Optional ATLAS submission

Use option 4 at scan completion or in `handoff`, or use the new `atlas` command for an existing run. The direct command requires no Garak configuration changes:

```powershell
& $labPython $runnerPath atlas --run-dir "D:\AI-Lab\evaluations\existing-run" `
  --discovery "D:\AI-Lab\private\mcp-discovery\completed-discovery.json" `
  --provider "OpenAI" --model "MODEL_SHOWN_IN_YOUR_ATLAS_FLOW"
```

The operator supplies a completed authenticated discovery report and the provider/model observed in the ATLAS flow. Omitted values are requested interactively. These provider/model labels are provenance, not model configuration overrides. The runner displays the endpoint, tool, run, handoff hash, full saved handoff, and cost limitation. Only uppercase `SEND` authorizes submission. The Langflow API key is then requested with hidden input; it is not accepted in CLI arguments, profiles, or the handoff.

Before invoking `atlas_agent_v110`, the client rechecks the server identity/version and exact tool metadata/schema against discovery. It sends the existing UTF-8 handoff as `input_value` with a new UUID `session_id`. It does not regenerate the handoff, run Garak, change model settings, request Kumu, or automatically index findings. Original evidence and root checksums remain unchanged. Each submission gets its own directory under `atlas-submissions`, including a byte-identical handoff copy, request, returned result, unreviewed reply, metadata, exchanges and separate checksums. See [patch notes](patch-0.4.0.md).

The client permits one explicit ATLAS tool invocation per action, disables HTTP redirects/proxies and automatic retries, and never executes server-initiated requests or follows returned resources. These client restrictions do not enforce the ATLAS flow's internal tool permissions or limit its upstream model requests. A timeout, disconnect, or interruption after dispatch is **execution unknown**, not proof that server work stopped. Review the archive and server before deciding whether to submit again. `--timeout-seconds` defaults to 300 (range 30–1800); it configures socket waits and response-processing checks, not a hard end-to-end deadline or provider cancellation.

This first MCP path supports the discovered Langflow project endpoint on HTTP loopback, `x-api-key`, and protocol `2025-03-26`. OAuth, remote endpoints, arbitrary MCP tools, and unattended submission are outside this patch. `atlas --yes` is rejected. The caller's account ID and key permissions are not exposed by the discovery exchange; the client does not claim to verify their least privilege. The agent may use a cloud LLM even when Langflow itself is local. Costs and effective generation settings of that backend are not independently measured by this client.

### Optional Kumu view from saved analysis

First create the private expected-target configuration described in [0.4.2](patch-0.4.2.md). Menu action 5 reads the sibling `garak-playbook-private/kumu.private.json`; the CLI also accepts `--kumu-config PATH`.

Use action **5** in the handoff/completion menu, or:

```powershell
& $labPython $runnerPath kumu --run-dir "D:\AI-Lab\evaluations\existing-run"
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

The existing Ollama prompt cap is source-verified for the two shipped campaigns; browser workload limits are validated separately. It is **not a hard HTTP request or spend cap**: The Ollama generator can retry empty responses or transport failures. OpenAI has a separate optional request counter/cap and aborts HTTP failures. Do not reuse these workload assumptions for arbitrary probes. A wall-clock stop is also not proof that an already accepted inference stopped on the server.

`base64-32` screens for encoded-payload emission using `encoding.InjectBase64` and `encoding.DecodeMatch`. Its payload mix includes benign text, renderable strings, and offensive terms. Decoding or quoting a string is not automatically a vulnerability. The analyst must identify the security requirement and actual violating behavior.

`dan-wild-32` screens a sampled set of existing jailbreak prompts using `dan.DanInTheWild` and `mitigation.MitigationBypass`. Missing a recognized refusal phrase or acknowledging a role-play does not establish attack success. No dynamic attack LLM is used.

## Evidence and review

Each run receives a unique directory. Existing evidence is not overwritten. See [Evidence schema](evidence.md) for the output inventory and limitations.

1. Read `summary.md` and `console.log`. Resolve coverage gaps before treating the run as complete.
2. Review original prompts, outputs and conversations through the references in `observations.jsonl`.
3. Separate true behavioral violations from quotation, refusal, benign decoding, and detector artifacts.
4. Reproduce candidate behavior under comparable settings. A changed interface, prompt, model digest, token budget or detector is a modified experiment.
5. Copy the entire finished prompt from `atlas_handoff.md` using menu option 1 and paste it into your existing agent after checking its backing model/data destination. Save its response separately and verify official ATLAS references. No extra prompt-writing step is needed.
6. Record attack success and legitimate-task completion separately. This release initializes both to `not_assessed`.

You can analyze an existing 0.17.0 report without invoking a model:

```powershell
& $labPython $runnerPath summarize --report "D:\AI-Lab\evidence\original.report.jsonl" --out "D:\AI-Lab\analysis\new-analysis-folder"
```

The analysis folder must not already exist. Original bytes are untouched. If the original report lacks required setup information, the parser records the missing information instead of inventing settings. A report analyzed without a recorded successful process outcome receives `process_outcome_unknown` when its completion marker is otherwise valid. Supply `--manifest` with that run's retained manifest to include its process outcome. Do not call an old report a replay or a new scan.

## Tests and validation

```powershell
Set-Location "D:\AI-Lab\projects\garak-playbook"
& $labPython -m unittest discover -s tests -v
```

These tests use synthetic records, not model findings. `tests/integration_stub.py` optionally exercises the real Garak CLI against a synthetic local protocol server; it does not run an LLM. See [Validation](validation.md).

## Public distribution

Publish only this source folder. Keep the sibling private folder and all evidence outside Git. The allowlist in `docs/public-file-list.txt` records the intended public files; inspect the final tracked tree and all history reachable from the release branch before publishing. The same boundary applies to GitHub release attachments. Anything marked `NOGIT` or private, outer review ZIPs, Git bundles, `PRIVATE-REVIEW/`, receipts/logs, real transcripts and IDs, keys, private endpoints/configs/paths, databases, models and environments remain outside both. Reviewed generic configs, synthetic fixtures and the sanitized worked example are permitted. `.gitignore` alone is not a sanitizer. No real lab evidence is included in this public source folder. The original project files use the MIT license in the repository root.

## Sources inspected

- Garak 0.17.0 wheel from PyPI, with selected hashes in `source-audit.json`.
- Garak CLI, configuration, native attempt and evaluator implementation in that exact distribution.
- [Garak reporting](https://reference.garak.ai/en/stable/reporting.html); newer docs are background, not a substitute for versioned source.
- [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md), for the local metadata endpoints.
- [Official ATLAS data](https://github.com/mitre-atlas/atlas-data), for future candidate-mapping verification.
- [Windows PowerShell Set-Clipboard](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/set-clipboard?view=powershell-5.1), for copying text rather than a file object.
- [Python subprocess](https://docs.python.org/3/library/subprocess.html) and [Windows process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags), for detached Notepad launching and standard-stream isolation.
