# Garak Evidence for the MITRE ATLAS Agent

Investigate Garak detector flags with the MITRE ATLAS Agent in Langflow.

**New laptop? Start with [Install on Windows and open your first ATLAS reply](docs/install-and-verify.md).**

Review candidate technique mappings and search saved evidence locally with Chroma and EmbeddingGemma.

The Windows runner turns a saved Garak run into a concise `atlas_handoff.md`. You can copy it to your configured MITRE ATLAS Agent in Langflow, or review and confirm submission over authenticated MCP. The runner archives the handoff and the agent's reply beside the run; the reply remains unreviewed analysis. You supply and configure the Langflow agent and its model provider separately. This repository does not bundle the agent, flow, ATLAS dataset or model credentials.

ATLAS supports investigation of candidate techniques and related mitigations/case studies. Its answers require analyst review and authoritative source verification. A separate confirmed Kumu request explores selected candidate mappings; optional Chroma indexing with local EmbeddingGemma makes saved run records searchable while original evidence stays separate.

![Workflow from a saved Garak run and reviewed handoff to the MITRE ATLAS Agent in Langflow and an archived reply with candidate mappings for analyst review; optional local search uses EmbeddingGemma via Ollama and a Chroma index.](docs/images/garak-atlas-workflow.png)

**Unpublished v1.0.0 candidate; no public release or tag yet.** The inspected Garak 0.17.0 registry has 191 probe IDs. This runner enables 14; that is permission to test, not proof that all 28 provider/probe pairs work. Live results apply to specific probe/model pairs. See the [compatibility table](docs/compatibility.md) and [v1 release instructions](docs/public-v1.md). The remaining 177 probes are deferred v2 work, not supported by this release candidate.

This is an independent community project maintained in a personal capacity. It does not represent Microsoft or imply its endorsement. Use it on systems you own or have permission to test. The software is provided as is under the MIT License.

**Interpretation:** detector flags are screening results, ATLAS mappings are candidates, and confirmed findings require analyst review. Cloud scans and the backing model/tools of a Langflow agent can incur charges. Review the destination, settings and handoff before confirmation. Keep credentials and real evidence outside public issues and pull requests. See [third-party notices](THIRD_PARTY.md) for integration attribution.

## What it does

- Runs `base64-32`, `dan-wild-32`, or a reviewed probe selected in the supported-probe browser. Search, pagination and Back do not launch scans; `RUN` does.
- Batches missing enabled probe/model pairs after one explicit review. Existing scored runs are credited, including gaps; failed/unscored runs are held unless explicitly selected for retry. Each run retains its own evidence and handoff. One consolidated report lists gaps and saved transport diagnostics. See [batch operation](docs/batch.md).
- Preserves original reports, per-run settings, exact counts and coverage gaps. Null/error outputs are not passes.
- Produces a compact handoff with input excerpts and detector observations. Full model responses remain in original evidence; ATLAS cannot assess omitted responses from this handoff.
- Supports explicitly confirmed ATLAS MCP submission and separate Kumu requests. Analysis stays unreviewed; mappings stay candidates. Graph scope includes selected IDs plus one-hop research context.
- Explicitly indexes one saved run into a dedicated Chroma research collection; reindexing unchanged evidence creates no duplicate. Original evidence stays separate. Automatic post-scan indexing and separate finding/note workflows are not implemented.

This is a model-testing and research workflow. It does not by itself establish enterprise impact, agent tool misuse or RAG authorization enforcement. Broader probe validation and PyRIT scenarios are deferred.

## Install on Windows and open your first ATLAS reply

Follow the installation guide from Step 1 through **Open the saved ATLAS reply**. It installs Git, Python, Ubuntu/WSL and Langflow, prepares the ATLAS flow with the tested OpenAI Responses model component, verifies a dataset lookup in Playground, and sends the included synthetic Garak handoff over MCP. You do not run a Garak scan during installation.

## Configure Garak for live scans after installation

Use this path **after the installation guide** when you want to scan a real model. It reuses your existing checkout and Windows scanner environment. The ATLAS model from Step 13 and a Garak scan target are separate settings; success with the ATLAS model does not establish Garak compatibility with that model.

### Reopen the existing runner

**Where:** normal **Windows PowerShell**. Restore these paths after opening a new window:

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath "$repo\playbook.py")) { throw 'Runner missing. Complete the installation guide first.' }
if (-not (Test-Path -LiteralPath $scannerPython)) { throw 'Scanner environment missing. Complete Step 4 of the installation guide.' }
Set-Location -LiteralPath $repo
& $scannerPython --version
& $scannerPython "$repo\playbook.py" --help
```

**You should see:** `Python 3.11.x` and runner help. If you chose different paths during installation, use those same paths here. Keep the existing checkout and environment; no clone or dependency installation is needed.

### Create or reuse your private scan configuration

**Where:** the same normal **Windows PowerShell** window.

The sample-to-ATLAS installation did not need scan configuration. This block creates it only if missing. If a configuration already exists, it keeps that file and lists its configured targets.

```powershell
$config = Join-Path $labRoot 'garak-playbook-private\config.private.json'
if (-not (Test-Path -LiteralPath $config)) {
    $openaiModel = Read-Host 'OpenAI reasoning model ID you intend to scan with Garak'
    if ([string]::IsNullOrWhiteSpace($openaiModel)) { throw 'A model ID is required; no API call made.' }
    & $scannerPython "$repo\tools\configure.py" --data-root $labRoot --garak-python $scannerPython --openai-model $openaiModel
    if ($LASTEXITCODE -ne 0) { throw 'Configuration creation failed. Keep the error.' }
}
(Get-Content -LiteralPath $config -Raw | ConvertFrom-Json).targets | Format-List
```

**You should see:** your configured targets and model names. The new configuration includes `openai-reasoning` and an optional `ollama-local` target. Listing Ollama does not install it. Existing configuration is reused without changing its model IDs, settings or evidence paths.

### Review a plan before a live scan

For the configured OpenAI target, run:

```powershell
& $scannerPython "$repo\playbook.py" plan --config $config --target openai-reasoning --campaign base64-32
```

**You should see:** a plan with the target/model, probe and completion budget. Planning makes no model requests and does not verify access. If your existing configuration has no `openai-reasoning` target, use its intended target name or follow the [operator guide](docs/operator-guide.md#start-in-windows-powershell); do not replace the configuration to get past an error. Check the [compatibility table](docs/compatibility.md) before selecting a scan model. The closed fourteen-probe validation campaign is not an installation step.

For OpenAI, start the menu and choose the OpenAI target. Review the selected probe, effective completion budget and estimated cost before `RUN`. Only then enter the API key at the hidden prompt. No Ollama service or Langflow instance is required for OpenAI scanning.

```powershell
& $scannerPython "$repo\playbook.py" menu --config $config
```

For missing enabled OpenAI combinations, review one batch before `RUN`:

```powershell
& $scannerPython "$repo\playbook.py" batch --config $config --target openai-reasoning
```

The batch skips existing scored pairs, including gaps. It does not automatically retest gaps at a larger limit. For `gpt-5.6-sol`, Ascii85, Base32 and Base64 default to 20000 total completion tokens (reasoning included), based on the paired 96/96-scorable retest. The other 11 probes retain 1500; other model IDs also retain 1500. Explicit operator limits take precedence. Original 1500-token baselines and their gaps remain recorded. See the compatibility table. Omitting `--target` selects all configured targets, so choose the provider explicitly.

Ollama remains optional. Install it and a chosen local model separately using its [official instructions](https://docs.ollama.com/quickstart); this runner downloads no models. Select `ollama-local` when intentionally testing it. DAN on the recorded `llama3.2:3b` setup failed and its investigation is closed for v1. Existing local evidence remains retained.

Keep the storage location chosen during installation and any existing private configuration. For a new setup using another location, set `$labRoot` to that location before the configuration block. The historical default cloud model is not a guarantee of public availability. OpenAI requires hidden key entry and a paid compatibility request after confirmation; broader probe compatibility remains separate. Verify pricing for your account/model. No credit balance becomes an automatic runner spending cap.

## Connect your Langflow ATLAS Agent

Deploy your own [MITRE ATLAS agent](https://github.com/mitre-atlas/atlas-knowledge-base-agent), verify its actual LLM provider and enable project MCP authentication. Read the exact endpoint from Langflow. Authenticated discovery is included:

```powershell
& $scannerPython "$repo\tools\inspect_atlas_mcp.py" `
  --url 'http://localhost:PORT/api/v1/mcp/project/YOUR_PROJECT_ID/streamable' `
  --output-dir "$labRoot\garak-playbook-private\mcp-discovery" --api-key-prompt
```

Discovery invokes no ATLAS tools. Use the resulting report with `playbook.py atlas`, or select **Send saved handoff to ATLAS over MCP** from the completion/existing-run menu. Review the saved handoff and destination, then type `SEND` to authorize submission. The Langflow key uses hidden input. Full model responses remain in the original Garak evidence; the compact handoff includes selected input excerpts and detector observations, so ATLAS cannot assess omitted responses. A different flow/schema requires review.

Kumu remains a separate action using approved candidate IDs and independently configured project/map binding. The view contains selected IDs plus one-hop research context, not additional confirmed findings. See the [operator guide](docs/operator-guide.md) and [target binding](docs/patch-0.4.2.md).

## Optional local research search

For Chroma, create a separate environment using `requirements-research.txt`, install EmbeddingGemma locally through Ollama, and use a new dedicated research directory. `tools/configure.py --research-python PATH` can create the research profile during initial setup. See [research commands](docs/patch-0.5.0.md). Research indexing is an explicit action. Some failures exit before receipt creation (R-01); successful receipts do not establish complete failure auditing.

## Validation and release

[Clean Windows testing](docs/clean-windows.md) uses synthetic reports, fake local HTTP endpoints and real embedded Chroma. It does not scan a real model or make paid calls. Desktop actions are mocked. Public source uses an allowlist; private configuration, actual evidence, keys, environments and databases stay outside Git. Tracked source and reachable Git history are reviewed for publication. Windows full validation passed at `09e8128`, and the seven targeted Windows delta checks passed at `4fedd3f`. The installation guide records the clean-laptop checkpoint and remaining documentation test. Setup-file preparation is checked offline; no new scan is required. No public GitHub release or tag has been authorized. Original project code and documentation are available under the [MIT License](LICENSE), including its warranty and liability terms. Separately installed components and models retain their own terms. See [third-party notices](THIRD_PARTY.md).

## Optional encoding headroom diagnostic

The [paired OpenAI diagnostic](docs/headroom-diagnostic.md) compares three saved 1,500-token encoding scans against a separately confirmed 20,000-token retest. It preserves exact prompt samples, produces paired usage/scorability evidence, and leaves campaign defaults unchanged.

A [sanitized worked example](docs/worked-example.md) traces one recovered detector flag to its supporting records and states the limits of the evidence. See [v1 validation and changes](docs/release-v1.md) for the carried Windows checkpoint and later validation. The single optional AVID export smoke test stopped on a missing `avidtools` dependency; AVID is deferred, with no added dependency or integration.
