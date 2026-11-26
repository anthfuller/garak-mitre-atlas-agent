# Install and verify

Follow this guide from a Windows checkout to a saved MITRE ATLAS Agent reply. The first submission uses the repository's synthetic fixture: no target-model scan is needed. Submitting it to a cloud-backed ATLAS agent can incur model/tool charges. Optional local search comes last.

**Validation boundary:** the existing Windows runner, authenticated ATLAS submission and local research workflow have been exercised in the maintainer's lab. The fresh WSL/Langflow installation and fresh-account flow import below are source-checked instructions, **not a completed clean-machine acceptance test**. See [verification coverage](#verification-coverage). Do not reopen the fourteen-probe campaign to follow this guide.

## 1. Keep the Windows runner layout

**New installation:** complete the [Windows quick start](../README.md#windows-quick-start) through its offline `plan` command. Stop before the scan/menu/batch examples. It installs the scanner and creates private configuration; it does not install Langflow.

**Already completed the quick start:** keep the checkout, Python environment and private configuration. Do not rerun `configure.py` over them. It deliberately refuses existing files. Use your actual paths if you chose different locations.

An external drive is optional. The defaults below use your Windows user profile. During initial configuration only, `--data-root` selects another storage location; keep using that location afterward.

**Windows PowerShell — normal terminal, not WSL, Ollama chat or Langflow Playground:**

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
$config = Join-Path $labRoot 'garak-playbook-private\config.private.json'
Set-Location -LiteralPath $repo
foreach ($path in @($scannerPython, $config, "$repo\playbook.py")) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing prerequisite: $path. Complete or reuse the quick start first."
    }
}
& $scannerPython "$repo\playbook.py" --help
if ($LASTEXITCODE -ne 0) { throw 'Runner did not load.' }
```

**Success:** help lists `atlas`, `research-index` and `research-search`. Keep this PowerShell terminal for the runner steps. The quick start's OpenAI scan target is independent of the model you configure inside ATLAS.

## 2. Start or install Langflow in WSL

### Reuse a working ATLAS installation

If your ATLAS Agent already works in Langflow, keep its project, database, login, provider settings and environment. If it is running, leave that terminal open and go to [configure the agent](#3-configure-the-agent). Otherwise, in its existing WSL project directory, use your established startup command:

**WSL — Ubuntu terminal, from your existing ATLAS project directory:**

```bash
uv run langflow run --env-file .env
```

Use your existing environment-file path if it differs. Wait for the Welcome message and use the **actual localhost port printed there**. Do not start a second instance just because startup takes time. Changing `LANGFLOW_SUPERUSER_PASSWORD` in an environment file does not reset an existing database account's password; retain that account and use the installed version's account-recovery procedure if necessary.

**Success:** the Windows browser opens that instance, your existing login works, and the ATLAS project is present. Skip the new-install section.

### New WSL and ATLAS installation

If Ubuntu under WSL is already available, skip this first command. Otherwise follow [Microsoft's WSL installation instructions](https://learn.microsoft.com/en-us/windows/wsl/install), restart if requested, open Ubuntu and create its Linux username/password.

**Windows PowerShell — Run as administrator, only to install WSL:**

```powershell
wsl --install -d Ubuntu-24.04
```

**Success:** Ubuntu opens to a Linux shell. That Linux password is separate from Langflow and provider credentials. Subsequent Windows runner commands use normal PowerShell.

Install prerequisites and [uv](https://docs.astral.sh/uv/getting-started/installation/) only if missing. If uv already works, skip its installer.

**WSL — Ubuntu terminal:**

```bash
sudo apt-get update && sudo apt-get install -y git curl ca-certificates
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/atlas-uv-install.sh && \
    sh /tmp/atlas-uv-install.sh && export PATH="$HOME/.local/bin:$PATH"
uv --version
```

**Success:** uv prints its version. These downloads install tools, not a scan target.

Clone the upstream MITRE agent separately from this runner. The inspected upstream revision is pinned below: it provides agent v1.1.0, Python >=3.12, Langflow 1.10.2, flow JSON, ATLAS CSV data and a prepared ATLAS vector store. This is a reproducibility reference, not a claim of a current dependency security audit. Do not upgrade an existing working deployment as part of this guide.

**WSL — Ubuntu terminal:**

```bash
export UV_CACHE_DIR="$HOME/.cache/atlas-uv"
mkdir -p "$HOME/source" && cd "$HOME/source" && \
    git clone https://github.com/mitre-atlas/atlas-knowledge-base-agent.git && \
    cd atlas-knowledge-base-agent && \
    git checkout --detach b2bca6438e99cb72752c27be1728f062b6f943ca && \
    uv sync --locked --python 3.12 && \
    uv run --locked python -c 'import importlib.metadata; print(importlib.metadata.version("langflow"))'
```

Stop on an error; do not overwrite an existing checkout. **Success:** the revision checks out and the version command prints `1.10.2`. This installs into the upstream project's WSL environment, separate from the Windows scanner environment.

The upstream checkout includes a preloaded `langflow.db` and its account. For a **new installation**, create your own empty configuration directory and import the flow instead of adopting that database or guessing its password. Keep the new environment file outside both repositories.

**WSL — Ubuntu terminal, still in the new upstream checkout:**

```bash
mkdir -p "$HOME/.config/garak-atlas" "$HOME/.local/share/garak-atlas"
(
    set -e
    umask 077
    test ! -e "$HOME/.config/garak-atlas/langflow.env"
    test ! -e "$HOME/.local/share/garak-atlas/langflow"
    set -C
    cat > "$HOME/.config/garak-atlas/langflow.env" <<EOF
LANGFLOW_CONFIG_DIR=$HOME/.local/share/garak-atlas/langflow
LANGFLOW_SAVE_DB_IN_CONFIG_DIR=True
LANGFLOW_AUTO_SAVING=True
DO_NOT_TRACK=True
LANGFLOW_ADD_PROJECTS_TO_MCP_SERVERS=False
LANGFLOW_CREATE_STARTER_PROJECTS=False
LANGFLOW_AUTO_LOGIN=False
LANGFLOW_SUPERUSER=atlas-researcher
LANGFLOW_SUPERUSER_PASSWORD=
EOF
) && nano "$HOME/.config/garak-atlas/langflow.env"
```

If either location already exists, stop and reuse its configuration; do not replace it. In Nano, set the password to your own nonempty password, save with **Ctrl+O, Enter**, then exit with **Ctrl+X**. Normal `.env` single quoting is allowed. Do not paste the password into chat, the repository or a shell command. These settings initialize a new account; they do not reset an existing one.

**WSL — Ubuntu terminal, still in the upstream checkout:**

```bash
uv run --locked langflow run --host 127.0.0.1 --port 7860 --env-file "$HOME/.config/garak-atlas/langflow.env"
```

Leave this terminal running. In the **Windows browser**, open the localhost URL printed by Langflow and sign in as `atlas-researcher` with the password you set. If the port is occupied, inspect the existing instance first; use the port actually selected by the instance you intend to connect to. Keep the service on loopback.

**Success:** the authenticated Projects page opens. Fresh-account initialization and the import below still require clean-machine validation; a Welcome banner alone does not validate them.

## 3. Configure the agent

**Existing working flow:** inspect the model/provider and continue to MCP setup. Do not import a duplicate or replace working data references.

**New instance:** in Langflow's **Projects** page create/select an **ATLAS Agent** project, then use **Upload a flow** to import `flows/ATLAS Agent v1.1.0.json` from the upstream checkout. Windows File Explorer can reach it through `\\wsl.localhost\Ubuntu-24.04\home\<your-linux-user>\source\atlas-knowledge-base-agent`. Substitute your actual WSL distribution/user; the Linux shell's current directory is not a Windows path. See [Langflow's import instructions](https://docs.langflow.org/concepts-flows-import).

The exported flow's file references belong to the upstream database account. In your new account, remove stale file selections and upload these files into the corresponding components; keep the existing wires:

| Component / connection | Upstream file or setting |
| --- | --- |
| Read File feeding `vector_store_contract` | `prompts/tool-contracts/ATLAS Vector Store.md` |
| Read File feeding `dataset_sandbox_contract` | `prompts/tool-contracts/ATLAS Dataset Sandbox.md` |
| Read File feeding `graph_generator_contract` | `prompts/tool-contracts/ATLAS Graph Generator.md` |
| ATLAS Dataset Sandbox / CSV File | `data/atlas-data/v2026-07/atlas-nodes-with-emb-text-v2026-07.csv` |
| ATLAS Vector Store / Collection Name | `atlas-vectors-v2026-07` |
| ATLAS Vector Store / Persistence Path | `./data/atlas-data/vectors` — start Langflow from the upstream checkout so this resolves correctly |

**Success:** the flow is named **ATLAS Agent v1.1.0**, the three contract files and CSV are selected without missing-file errors, and the vector-store settings match the supplied data. The upstream ATLAS vector store is separate from the runner's optional research database; do not replace its embedding configuration with EmbeddingGemma. Its existing embedding implementation may download its own embedding-model assets on first use.

Open the highlighted **Model Configuration** component. In this flow its component label is **vLLM**, but it accepts an OpenAI-compatible API; the label alone does not identify your provider.

1. Set **Model Name** to a model your chosen provider/account supports, with tool calling.
2. Set **vLLM API Base** to that provider's actual API base. For a direct OpenAI setup, the base is `https://api.openai.com/v1`.
3. Set **API Key** using your own provider credential in Langflow's protected field/global variable. Save the flow. Reuse a working configured provider rather than copying the maintainer's historical model ID.

**Success:** the saved flow shows your intended model and base URL, with the key concealed and the language-model output connected to the Agent. This is configuration verification only. The confirmed submission in step 6 will exercise the flow; no separate paid Playground test is required here. Provider/model labels entered in the runner later record what you observed; they do not configure or independently inspect Langflow.

## 4. Enable authenticated project MCP access

In the **Windows browser**, return to **ATLAS Agent project -> MCP Server**. Use **Edit Tools** to expose the ATLAS flow. Configure its MCP tool name as `atlas_agent_v110` if the generated name differs; the UI may display `ATLAS_AGENT_V110`. The runner requires the exact lowercase name returned by discovery and the reviewed input schema.

Choose **Add Auth / Edit Auth -> API Key**. Under **Settings -> Langflow API Keys**, create a key for your account (or use **Generate API key** on the project page if available). Save it privately. This is the **Langflow API key**, separate from your browser login password and the model provider's API key. The runner asks for it with hidden input, keeps it in memory for that command, and does not need it saved in runner configuration.

On the project's **MCP Server -> JSON -> Windows -> Streamable HTTP** tab, copy only the actual URL ending in `/api/v1/mcp/project/<project-id>/streamable`. Preserve the displayed localhost port. Do not copy a key-bearing client configuration into this repository. The runner connects directly; it does not require the displayed `cmd / uvx / mcp-proxy` wrapper or an installation into Claude/Cursor. This is the **project MCP server**, not Settings -> Langflow MCP Client.

**Success:** Auth shows **API Key**, the intended flow is listed, and you have its loopback Streamable HTTP URL. If these controls differ in another Langflow version, use that version's [project MCP documentation](https://docs.langflow.org/mcp-server) and confirm discovery below; do not assume compatibility.

## 5. Discover and validate the expected tool

Return to the **same Windows PowerShell terminal** as step 1. Leave Langflow running in WSL.

**Windows PowerShell — normal terminal:**

```powershell
$endpoint = Read-Host 'Paste the project Streamable HTTP URL (no key)'
$discoveryDir = Join-Path $labRoot 'garak-playbook-private\mcp-discovery'
& $scannerPython "$repo\tools\inspect_atlas_mcp.py" `
    --url $endpoint --output-dir $discoveryDir --api-key-prompt
if ($LASTEXITCODE -ne 0) { throw 'Discovery failed; inspect its saved report before continuing.' }
$discovery = Read-Host 'Paste the full Discovery report path printed above'
& $scannerPython -c 'import atlas_mcp,sys; c=atlas_mcp.load_discovery(sys.argv[1]); print("Validated tool:", c["tool"]["name"]); print("Endpoint:", c["endpoint"])' $discovery
if ($LASTEXITCODE -ne 0) { throw 'Discovered identity/schema is not compatible with this runner.' }
```

At the hidden prompt, enter the **Langflow API key**. **Success:** `Discovery status: discovery_complete`, `Tool invocations: 0`, then `Validated tool: atlas_agent_v110`. Its input schema has exactly the string properties `input_value` and `session_id`. Initialization, tool listing and schema validation do not invoke the ATLAS model. HTTP 401/403 means the key/access was rejected; a missing tool or schema mismatch needs configuration/version review, not a scan or guessed bypass.

## 6. Submit a synthetic saved handoff and read the archive

For this first connection test, prepare a **new, separate synthetic example** using the public parser fixture. It contains no private transcript. The following block calls the existing renderer, records the fixture manifest and hashes, and refuses to replace an existing example. It does not run Garak or invent a successful scanner process. Bare `summarize` output is insufficient for `atlas`: the complete report, manifest, summary, handoff and checksums are required.

**Windows PowerShell — normal terminal, still in `$repo`:**

```powershell
$savedRun = Join-Path $labRoot 'examples\synthetic-atlas-run'
@'
from pathlib import Path
import shutil, sys
import playbook as p
import atlas_mcp as a
run = Path(sys.argv[1])
run.mkdir(parents=True, exist_ok=False)
report = run / "scan.report.jsonl"
shutil.copyfile(p.ROOT / "examples" / "synthetic_fixture.jsonl", report)
manifest = {"synthetic": True, "notice": "SYNTHETIC parser fixture; no model or scanner was run.",
            "process_status": "not_run_synthetic", "exit_code": None,
            "target": {"provider": "synthetic", "model": "synthetic:no-model-called"}}
p.write_json(run / "manifest.json", manifest)
summary = p.render_outputs(report, run, manifest)
p.checksums(run)
a.load_run(run, p.analyze)
print("SYNTHETIC example ready:", run)
print("Run ID:", summary["garak_run_id"])
print("Execution status:", summary["execution_status"])
'@ | & $scannerPython - $savedRun
if ($LASTEXITCODE -ne 0) { throw 'Example preparation failed; do not send it.' }
notepad.exe "$savedRun\atlas_handoff.md"
```

**Success:** `SYNTHETIC example ready`, Run ID `synthetic-example`, and `process_outcome_unknown`. That last status is intentional: this is generated parser data, not a completed scan. The example has one recorded response and one synthetic detector flag; neither is live-model evidence. If the folder already exists from this guide, reuse it without regenerating or editing its hashed files.

Review the handoff in Notepad. Then submit the **saved file** through the existing runner:

```mermaid
flowchart TD
    scan["Garak scan"] --> saved["Saved run: original report, settings, and evidence"]
    saved --> handoff["Runner prepares ATLAS handoff"]
    handoff --> confirm["Operator types `SEND` to submit the handoff"]
    confirm -->|"Authenticated MCP"| agent["MITRE ATLAS Agent in Langflow"]
    agent --> reply["Archived reply: candidate mappings for analyst review"]
    saved -->|"Optional local search"| selectRun["Researcher selects a run to index"]
    selectRun --> embed["EmbeddingGemma via local Ollama"]
    embed --> index["Local Chroma index: search saved runs and open linked evidence"]

    classDef evidence fill:#f1f5f9,stroke:#64748b,color:#1e293b
    classDef investigation fill:#e7f1ff,stroke:#3178bd,color:#173c60
    classDef confirmation fill:#f4faff,stroke:#b8cddd,color:#00549e
    classDef research fill:#e3f4ed,stroke:#2d8b70,color:#174f42
    class scan,saved evidence
    class handoff,agent,reply investigation
    class confirm,selectRun confirmation
    class embed,index research
```

**Windows PowerShell — interactive normal terminal:**

```powershell
& $scannerPython "$repo\playbook.py" atlas --run-dir $savedRun --discovery $discovery
```

Enter the provider and model names you just observed in the Langflow flow. Review the endpoint, tool, run ID and entire handoff. Type **SEND** only when they are correct, then enter your **Langflow API key** at the hidden prompt. Enter instead of SEND cancels. One MCP invocation can result in multiple paid model/tool calls inside ATLAS; that cost is not measured by the runner.

**Success:** `ATLAS status: response_received_unreviewed`, an **ATLAS archive** path, an **Unreviewed ATLAS reply** path, and `Recorded Garak scan outcome is unchanged.` A reply can correctly say the synthetic evidence is insufficient for a mapping. Success here means a reply was archived, not that mappings or internal tool execution were independently verified.

Copy the exact archive directory printed for this submission:

**Windows PowerShell — normal terminal:**

```powershell
$atlasSubmission = Read-Host 'Paste the ATLAS archive directory printed for this submission'
notepad.exe "$atlasSubmission\atlas_response.md"
```

The archive is under `$savedRun\atlas-submissions\<timestamp-id>`. It includes the exact submitted `handoff.submitted.md`, `atlas_response.md`, `submission.json` and checksums. Keep it private. On an error/timeout inspect that archive before retrying: remote execution may already have occurred. A received reply remains **unreviewed analysis**, and detector flags/mappings require analyst review. The compact handoff omits full model responses; ATLAS cannot infer behavior from those omitted responses.

For an existing real saved run, use its directory instead, review the handoff for intended disclosure, and preserve its original files. Do not sanitize by editing hashed evidence in place. Kumu is a [separate confirmed action](operator-guide.md); it is not automatically requested by this submission.

## 7. Optional: index and search locally

This uses the **same saved example and ATLAS archive**. It needs no new scan or cloud call. Use a dedicated research store; do not point it at the upstream ATLAS vector store or another existing Chroma database.

### Ollama and EmbeddingGemma

Reuse a working Windows Ollama installation. Otherwise install the native Windows app from [Ollama](https://ollama.com/download/windows), start it, and reopen normal PowerShell so `ollama` is on PATH; restore the variables from step 1 and the two saved paths if you opened a new terminal. The Windows app normally serves loopback port 11434. Do not start a second `ollama serve` if it is already running. [EmbeddingGemma requires Ollama 0.11.10 or later](https://ollama.com/library/embeddinggemma).

**Windows PowerShell — normal terminal, not Ollama's `>>>` chat:**

```powershell
ollama --version
ollama list
```

If `embeddinggemma:latest` is absent, download it once. Skip this download when reusing an already indexed model: pulling `latest` can change its digest.

**Windows PowerShell — only when the model is absent:**

```powershell
ollama pull embeddinggemma:latest
if ($LASTEXITCODE -ne 0) { throw 'Embedding model download failed.' }
```

**Windows PowerShell — verify the model and one local embedding:**

```powershell
ollama show embeddinggemma:latest
if ($LASTEXITCODE -ne 0) { throw 'Embedding model is unavailable.' }
$body = @{model='embeddinggemma:latest'; input='Synthetic Garak evidence search'; truncate=$false} | ConvertTo-Json
$embedding = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:11434/api/embed' `
    -ContentType 'application/json' -Body $body
if ($embedding.embeddings.Count -ne 1 -or $embedding.embeddings[0].Count -lt 1) {
    throw 'Expected one nonempty embedding vector.'
}
"Local embedding dimensions: $($embedding.embeddings[0].Count)"
```

**Success:** the named embedding model is present and the local API returns one nonempty vector. This verifies service/model operation, not retrieval quality. The runner separately records and pins its installed digest when the collection is created.

### Separate embedded Chroma environment and private configuration

If you already have a valid `research.private.json`, reuse it and its configured interpreter/store; skip environment/config creation. Do not rerun the main `configure.py`. For a new research setup:

**Windows PowerShell — normal terminal:**

```powershell
$researchEnv = Join-Path $labRoot 'research-env'
$researchPython = Join-Path $researchEnv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $researchEnv)) {
    py -3.11 -m venv $researchEnv
    if ($LASTEXITCODE -ne 0) { throw 'Research environment creation failed.' }
    & $researchPython -m pip install -r "$repo\requirements-research.txt"
    if ($LASTEXITCODE -ne 0) { throw 'Research dependency installation failed.' }
}
& $researchPython -c 'import importlib.metadata; v=importlib.metadata.version("chromadb"); assert v == "1.5.9", v; print("Chroma", v)'
if ($LASTEXITCODE -ne 0) { throw 'Use a dedicated environment with Chroma 1.5.9; preserve the existing environment.' }
$researchConfig = Join-Path $labRoot 'garak-playbook-private\research.private.json'
if (Test-Path -LiteralPath $researchConfig) { throw 'Research configuration exists; reuse it instead of replacing it.' }
$researchSettings = [ordered]@{
    schema_version = 1
    python = $researchPython
    storage_root = (Join-Path $labRoot 'research')
    ollama_endpoint = 'http://127.0.0.1:11434'
    embedding_model = 'embeddinggemma:latest'
}
$researchSettings | ConvertTo-Json | Set-Content -LiteralPath $researchConfig -Encoding UTF8
```

**Success:** `Chroma 1.5.9` and a separate research configuration. The main scanner config remains untouched. No Chroma server is required. On first use the research root must be new/empty; an unowned nonempty directory is rejected. Do not delete an existing database to bypass that check.

If reusing research configuration, set `$researchConfig` to its actual full path before continuing. Keep `$savedRun` and `$atlasSubmission` from step 6. Index once, then repeat the **same** command to verify no duplicate:

**Windows PowerShell — normal terminal:**

```powershell
$indexArgs = @('research-index', '--research-config', $researchConfig,
    '--run-dir', $savedRun, '--atlas-submission', $atlasSubmission)
& $scannerPython "$repo\playbook.py" @indexArgs
if ($LASTEXITCODE -ne 0) { throw 'Indexing failed; inspect the displayed error/receipt.' }
& $scannerPython "$repo\playbook.py" @indexArgs
if ($LASTEXITCODE -ne 0) { throw 'Reindex verification failed.' }
& $scannerPython "$repo\playbook.py" research-search --research-config $researchConfig `
    --query 'synthetic Base64 parser demonstration' --model 'synthetic:no-model-called'
if ($LASTEXITCODE -ne 0) { throw 'Search failed.' }
```

**Success:** first `indexed`, then `unchanged`; for a new store the collection counts are `0 -> 1`, then `1 -> 1`, with `exact read-back: PASSED` and original evidence unchanged. Search returns `synthetic-example`, its original report/summary and unreviewed ATLAS reply paths, and matching evidence hashes. Existing stores can have higher counts. Receipts are under the configured research root's `receipts` directory. Finding one demonstration record establishes retrieval plumbing, not ranking quality or security impact.

Open the indexed original summary:

**Windows PowerShell — normal terminal:**

```powershell
& $scannerPython "$repo\playbook.py" research-open --research-config $researchConfig `
    --run-id 'synthetic-example' --evidence summary
```

**Success:** the hash-checked original summary opens in Notepad. For real research, explicitly index a chosen saved run, then search/filter using its recorded model/probe; [research command details](patch-0.5.0.md) explain the stored fields and limits. Indexing remains opt-in. Some research failures have no durable receipt (R-01); a successful demonstration does not close that gap.

## Verification coverage

| Checkpoint | Evidence and limit |
| --- | --- |
| Windows runner installation and integrations | Full Windows pass at `09e8128`; seven Windows delta checks at `4fedd3f`. See the [release record](release-v1.md). This guide does not claim a new full Windows pass. |
| Existing Langflow/ATLAS deployment | Startup, authenticated discovery, confirmed MCP submission and reply archival were exercised in the maintainer's existing Windows/WSL lab. |
| Fresh WSL/uv/Langflow, new account and flow import | Instructions checked against upstream revision `b2bca6438e99cb72752c27be1728f062b6f943ca` and official documentation. A clean-machine execution of this exact route remains **unverified**. Current upstream docs may describe a newer UI than the pinned flow/runtime. |
| Synthetic saved-run preparation and archive routing | The guide's fixture assembly is checked offline against the existing renderer/loader. MCP archival is exercised with a synthetic protocol server; this does not validate a new Langflow deployment or paid model. |
| Optional research search | The maintainer exercised real local EmbeddingGemma indexing, unchanged reindexing, model/probe filters, search and evidence opening. This guide's synthetic example is checked with real embedded Chroma and fake embedding vectors; a fresh Windows installation following every new instruction remains **unverified**. |
| Release scope | Runtime, profiles, credentials and the fourteen-probe campaign are unchanged. Kumu remains separate, AVID and broader probes remain deferred, and public release/tagging require owner approval. |

The documentation closes the instruction gap; it does not turn the remaining clean-install checkpoints into passes. Keep the guide's expected results distinct from observed validation evidence.
