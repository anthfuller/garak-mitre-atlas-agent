# Garak Playbook

A Windows-first runner for supported Garak model scans, evidence preservation, concise MITRE ATLAS investigation handoffs, optional authenticated MCP submission, separate Kumu requests and optional Chroma research indexing with local EmbeddingGemma.

**Public v1 candidate, based on runner 0.5.0.** The Windows registry has 191 probe IDs. This runner enables 14. Live results apply to specific probe/model pairs. See the [compatibility table](docs/compatibility.md) and [v1 release instructions](docs/public-v1.md).

**Independent project.** This is a personal, independently maintained project. It is not affiliated with, sponsored by, or endorsed by Microsoft, NVIDIA, OpenAI, MITRE, or the other organizations whose products it references. The authors speak only for themselves. Product and project names identify integrations and belong to their respective owners.

**Use and interpretation.** Evaluate only systems you own or have explicit authorization to test. Detector flags are screening results. ATLAS mappings are candidates pending analyst review. A paid provider can charge for requests made through the runner. Inspect the destination, settings and prompts before confirmation. Keep credentials and real evidence outside public issues and pull requests.

## What it does

- Runs `base64-32`, `dan-wild-32`, or a reviewed probe selected in the supported-probe browser. Search, pagination and Back do not launch scans; `RUN` does.
- Preserves original reports, per-run settings, exact counts and coverage gaps. Null/error outputs are not passes.
- Produces a compact handoff with input excerpts and detector observations. Full model responses remain in original evidence; ATLAS cannot assess omitted responses from this handoff.
- Supports explicitly confirmed ATLAS MCP submission and separate Kumu requests. Analysis stays unreviewed; mappings stay candidates. Graph scope includes selected IDs plus one-hop research context.
- Explicitly indexes one saved run into a dedicated Chroma research collection; reindexing unchanged evidence creates no duplicate. Original evidence stays separate. Automatic post-scan indexing and separate finding/note workflows are not implemented.

This is a model-testing and research workflow. It does not by itself establish enterprise impact, agent tool misuse or RAG authorization enforcement. Broader probe validation and PyRIT scenarios are deferred.

## Windows quick start

Use normal Windows PowerShell, Git for Windows and Python 3.11. An external SSD is optional. Default private configuration, evidence and optional research storage use `%LOCALAPPDATA%\GarakPlaybook`, outside the checkout. Clone the supplied local review bundle using [clean Windows testing](docs/clean-windows.md); a public repository URL has not yet been selected.

```powershell
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
# Start in the cloned source folder containing playbook.py.
$repo = (Get-Location).Path
if (-not (Test-Path -LiteralPath "$repo\playbook.py")) { throw 'Open PowerShell in the source checkout.' }
New-Item -ItemType Directory -Path $labRoot -Force | Out-Null
if (Test-Path "$labRoot\scanner-env") { throw 'Preserve the existing environment.' }
py -3.11 -m venv "$labRoot\scanner-env"
if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed.' }
$scannerPython = "$labRoot\scanner-env\Scripts\python.exe"
& $scannerPython -m pip install -r "$repo\requirements-scanner.txt"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $scannerPython "$repo\tools\configure.py" --garak-python $scannerPython
if ($LASTEXITCODE -ne 0) { throw 'Configuration creation failed.' }
$config = "$labRoot\garak-playbook-private\config.private.json"
& $scannerPython "$repo\playbook.py" plan --config $config --target ollama-local --campaign base64-32
```

The plan makes no model requests. Garak dependencies may be substantial. Directly tested package versions are pinned; transitive dependencies are resolved by pip, not fully locked across platforms. Do not install into an existing working environment. Install Ollama separately using its [official instructions](https://docs.ollama.com/quickstart). The example model is `llama3.2:3b`; explicitly install it or select an already-installed model in private configuration. No model is downloaded by this runner.

With Ollama running, `preflight` inspects local metadata without generation; `menu` offers the reviewed scans:

```powershell
& $scannerPython "$repo\playbook.py" preflight --config $config --target ollama-local --campaign base64-32
& $scannerPython "$repo\playbook.py" menu --config $config
```

To use another storage location, supply `tools/configure.py --data-root 'D:\YourLab'` during initial setup. Existing configs are never overwritten. Add `--openai-model MODEL_ID` at initial setup to choose your reasoning model. The historical default cloud model is not a guarantee of public availability. OpenAI requires hidden key entry and a paid compatibility request after confirmation; broader probe compatibility remains separate. Verify pricing for your account/model. No credit balance becomes an automatic runner spending cap.

## Optional ATLAS and research

Deploy your own [MITRE ATLAS agent](https://github.com/mitre-atlas/atlas-knowledge-base-agent), verify its actual LLM provider and enable project MCP authentication. Read the exact endpoint from Langflow. Authenticated discovery is included:

```powershell
& $scannerPython "$repo\tools\inspect_atlas_mcp.py" `
  --url 'http://localhost:PORT/api/v1/mcp/project/YOUR_PROJECT_ID/streamable' `
  --output-dir "$labRoot\garak-playbook-private\mcp-discovery" --api-key-prompt
```

Discovery invokes no ATLAS tools. Use the resulting report with `playbook.py atlas`; review the handoff and type `SEND`. A different flow/schema requires review. Kumu uses a separate command and independent private project/map configuration. See [operator guide](docs/operator-guide.md) and [target binding](docs/patch-0.4.2.md).

For Chroma, create a separate environment using `requirements-research.txt`, install EmbeddingGemma locally through Ollama, and use a new dedicated research directory. `tools/configure.py --research-python PATH` can create the research profile during initial setup. See [research commands](docs/patch-0.5.0.md). Research indexing is an explicit action. Some failures exit before receipt creation (R-01); successful receipts do not establish complete failure auditing.

## Validation and release

[Clean Windows testing](docs/clean-windows.md) uses synthetic reports, fake local HTTP endpoints and real embedded Chroma. It does not scan a real model or make paid calls. Desktop actions are mocked. Public source uses an allowlist; private configuration, actual evidence, keys, environments and databases stay outside Git. A fresh local Git history is prepared for review. No GitHub publication has occurred. Original project code and documentation are available under the [MIT License](LICENSE), including its warranty and liability terms. Separately installed components and models retain their own terms. See [third-party notices](THIRD_PARTY.md).
