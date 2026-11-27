# Install and verify

You'll install the tools, send the included sample Garak results to the MITRE ATLAS Agent, and open its reply.

## 1. Open Windows PowerShell

**Where:** your Windows laptop.

1. Click **Start**, type **Windows PowerShell**, and open it normally. Do not choose **Run as administrator** yet.
2. Keep this guide open in your browser beside PowerShell.
3. Copy only the text **inside** each command box, paste it into the named terminal, and press **Enter**. Do not paste headings, explanations, or `PS C:\...>` prompts.

**You should see:** a terminal prompt beginning with `PS`. If a step fails, stop at that step and keep its error; later steps depend on it.

This guide uses Windows 11 with an x64 processor and the default `C:` layout. The runner goes in `%USERPROFILE%\source\garak-mitre-atlas-agent`; its environment and sample evidence go in `%LOCALAPPDATA%\GarakPlaybook`. Ubuntu/WSL holds Langflow separately. No external drive is needed.

The sample results are made-up demonstration data included in the repository. **You will not run a Garak scan.** Sending the sample to a cloud-backed ATLAS Agent can incur API charges. You will choose the model and confirm with `SEND` before that happens. Clean-laptop validation is still in progress.

## 2. Check Git and Python 3.11; install what is missing

**Where:** the normal Windows PowerShell window from step 1.

### Check Git

**Windows PowerShell:**

```powershell
git --version
```

**You should see:** `git version ...`. Git is ready; check Python below.

If Windows does not recognize `git`, install it:

**Windows PowerShell — only if Git is missing:**

```powershell
winget install --id Git.Git --exact --source winget
```

When installation finishes, close PowerShell, reopen **Start → Windows PowerShell** normally, and run `git --version` again. Continue only when it prints `git version ...`. If `winget` is missing, use the fallback below, then return here.

### Check Python 3.11

**Windows PowerShell:**

```powershell
py -3.11 --version
```

- **You see `Python 3.11.x`:** Python is ready. Continue to Step 3. If you already cloned the repo, use the **Step 4 recovery** below; do not clone again.
- **You see `No suitable Python runtime found`, or Windows doesn't recognize `py`:** **Stay here. Install Python 3.11 with the command below.** Do not continue to cloning or environment creation yet.

**Windows PowerShell — install Python 3.11:**

```powershell
winget install --id Python.Python.3.11 --exact --source winget --architecture x64
```

When it finishes, **close PowerShell**, reopen **Start → Windows PowerShell** normally, and check again:

**Windows PowerShell — after reopening:**

```powershell
py -3.11 --version
```

**Continue only when it prints `Python 3.11.x`.** If an installer asks for a Windows restart, restart, reopen this guide and normal Windows PowerShell, and repeat the check. Another Python version does not replace 3.11 for this guide.

**If `winget` is missing:** open **Start → Microsoft Store**, find **App Installer** published by **Microsoft Corporation**, and choose **Install** or **Update**. Close and reopen PowerShell, then check:

**Windows PowerShell:**

```powershell
winget --version
```

**You should see:** a version starting with `v`. Return to the installation command for the missing tool above. Accept an installer prompt if Windows displays one.

If the launcher still cannot find 3.11, use the [Python 3.11.9 Windows installer](https://www.python.org/downloads/release/python-3119/): select **Windows installer (64-bit)**, run it, enable the **Python launcher** and **Add python.exe to PATH**, and install. Reopen PowerShell and check again. These are the [Git for Windows](https://git-scm.com/downloads/win) and [Python package](https://github.com/microsoft/winget-pkgs/tree/master/manifests/p/Python/Python/3/11) installation sources.

## 3. Copy this repository to your laptop

**Where:** normal Windows PowerShell. Stay on Windows, not Ubuntu.

**Windows PowerShell:**

```powershell
$sourceRoot = Join-Path $env:USERPROFILE 'source'
$repo = Join-Path $sourceRoot 'garak-mitre-atlas-agent'
if (Test-Path -LiteralPath $repo) { throw 'This checkout already exists. Use the existing-installation section at the end; do not overwrite it.' }
New-Item -ItemType Directory -Path $sourceRoot -Force | Out-Null
git clone https://github.com/anthfuller/garak-mitre-atlas-agent.git $repo
if ($LASTEXITCODE -ne 0) { throw 'Clone failed. Check your GitHub access before continuing.' }
Set-Location -LiteralPath $repo
git rev-parse HEAD
```

While the repository is private, Git may open a GitHub sign-in window. Sign in with the GitHub account that can view this repository. If Git reports **Repository not found**, confirm that you can open [the repository](https://github.com/anthfuller/garak-mitre-atlas-agent) in your browser with that account; the clone cannot proceed without access.

**You should see:** cloning completes, the prompt ends in `\source\garak-mitre-atlas-agent>`, and Git prints a 40-character commit ID. Record that ID with your test results. It identifies the instructions and code you tested.

## 4. Install the Windows runner's dependencies

**Where:** normal Windows PowerShell. Python must have printed `Python 3.11.x` in Step 2.

**Already cloned the repo and reopened PowerShell?** Restore the repository variable and folder with these two lines. Keep your existing clone.

**Windows PowerShell:**

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
Set-Location -LiteralPath $repo
```

**You should see:** the prompt ends in `\source\garak-mitre-atlas-agent>`.

**Create the scanner environment — Windows PowerShell:**

```powershell
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
New-Item -ItemType Directory -Path $labRoot -Force | Out-Null
if (Test-Path -LiteralPath "$labRoot\scanner-env") { throw 'Scanner environment already exists. Preserve it and use the existing-installation section.' }
py -3.11 -m venv "$labRoot\scanner-env"
if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
```

Before installing dependencies, check the Python executable inside that new environment:

**Windows PowerShell — verify the environment:**

```powershell
& $scannerPython --version
```

- **You see `Python 3.11.x`:** the environment is ready. Paste the dependency-install block below.
- **You see any error or a different version:** **Stop here. Do not paste the dependency-install commands.** If creation reported `No suitable Python runtime found`, return to **Check Python 3.11** in Step 2. Preserve any existing environment; do not delete it to get past an error.

**Install dependencies — Windows PowerShell, only after the environment check passes:**

```powershell
& $scannerPython -m pip install -r "$repo\requirements-scanner.txt"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Stop and keep the error.' }
& $scannerPython -c "import importlib.metadata; print(importlib.metadata.version('garak'))"
& $scannerPython "$repo\playbook.py" --help
if ($LASTEXITCODE -ne 0) { throw 'The runner did not load.' }
```

The download/install may take several minutes. Wait for the prompt to return.

**You should see:** Garak version `0.17.0`, then help containing `atlas`, `research-index`, and `research-search`. This installs the scanner but does not scan a model. The included sample does not need a scan-target configuration or an OpenAI scan key. Do not start the menu or a batch for this check.

## 5. Install Ubuntu through WSL and restart Windows

**Where:** a **new administrator Windows PowerShell** window.

Right-click **Start → Windows PowerShell → Run as administrator**, or search for Windows PowerShell in Start and choose **Run as administrator**. Accept the Windows permission prompt. Keep the ordinary runner window separate.

**Windows PowerShell — administrator:**

```powershell
wsl --install -d Ubuntu-24.04
```

**You should see:** WSL/Ubuntu installation messages. When Windows asks for a restart, save other work and choose **Start → Power → Restart**. Do not repeat the installer while it is running.

After the restart:

1. Open **this guide in your Windows browser** and return to step 6.
2. Open **Start → Ubuntu 24.04 LTS**. If it is not listed, open normal Windows PowerShell and run `wsl -d Ubuntu-24.04`.
3. If WSL said a restart was required but Ubuntu was not installed yet, reopen **administrator Windows PowerShell**, run the step 5 command again, and then open Ubuntu.

The [Microsoft WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install) covers WSL installation errors such as virtualization being disabled. Stop on those errors; Langflow cannot run in Ubuntu until WSL works.

## 6. Create your Ubuntu user and reopen the runner window

**Where:** the **Ubuntu** window opened after the restart.

**Note:** If your name is already shown at `Create a default Unix user account:` and pressing **Enter** leaves the cursor sitting there, use **Backspace** to erase the displayed name, retype your name, and press **Enter** again.

Ubuntu will finish its first-time setup. Choose a Linux username and password when prompted. Password entry shows no characters; type it and press Enter anyway. Keep this password: Ubuntu will ask for it when you use `sudo`. It is separate from your Windows password and the Langflow password you will create later.

**WSL — Ubuntu:**

```bash
whoami
pwd
```

**You should see:** your Linux username and a path such as `/home/yourname`. The prompt ends with `$`, not the Windows `PS ...>` prompt.

Now open **Start → Windows PowerShell** normally in a separate window. Restore the paths that were lost during the restart:

**Windows PowerShell — normal:**

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
Set-Location -LiteralPath $repo
& $scannerPython "$repo\playbook.py" --help
```

**You should see:** the runner help again. Leave this window open. **Switch back to Ubuntu for steps 7–10.**

## 7. Install the Ubuntu tools

**Where:** **WSL — Ubuntu**, not PowerShell.

**WSL — Ubuntu:**

```bash
sudo apt-get update && sudo apt-get install -y git curl ca-certificates nano
```

Enter your **Ubuntu password** if asked. Wait until installation finishes.

**WSL — Ubuntu:**

```bash
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/atlas-uv-install.sh && sh /tmp/atlas-uv-install.sh
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

**You should see:** `uv` followed by a version. [uv](https://docs.astral.sh/uv/getting-started/installation/) installs the separate Python environment used by Langflow.

## 8. Download the MITRE ATLAS Agent and install Langflow

**Where:** the same **WSL — Ubuntu** window.

**WSL — Ubuntu:**

```bash
export UV_CACHE_DIR="$HOME/.cache/atlas-uv"
mkdir -p "$HOME/source" && cd "$HOME/source" && \
    git clone https://github.com/mitre-atlas/atlas-knowledge-base-agent.git && \
    cd atlas-knowledge-base-agent && \
    git checkout --detach b2bca6438e99cb72752c27be1728f062b6f943ca && \
    uv sync --locked --python 3.12 && \
    uv run --locked python -c 'import importlib.metadata; print(importlib.metadata.version("langflow"))'
```

This downloads the upstream agent and its dependencies. It may take several minutes. Python 3.12 here is **inside Ubuntu**; it does not replace Windows Python 3.11.

**You should see:** the final version `1.10.2`. A Git message about **detached HEAD** is expected: this guide selects a specific upstream version. If the folder already exists, do not delete it; use the existing-installation section at the end.

## 9. Create your Langflow login

**Where:** **WSL — Ubuntu**, in the new ATLAS Agent folder.

The upstream download includes somebody else's prepared Langflow database. This step gives your installation a **new database and your own account**. It keeps the upstream ATLAS dataset and vector store.

**WSL — Ubuntu:**

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

**You should see:** the Nano text editor with those settings. If it does not open, stop: the setup file/database may already exist. Do not overwrite either.

In Nano:

1. Move to the line `LANGFLOW_SUPERUSER_PASSWORD=` with the arrow keys.
2. Edit the password line using this format (example only):

   ```dotenv
   LANGFLOW_SUPERUSER_PASSWORD='Example-Only-84!River'
   ```

   **In Nano, replace `Example-Only-84!River` with your own password. Keep both single quotes. The opening quote goes immediately after `=`. Do not add a comma or use a single quote inside your password.**

3. Save: **Ctrl+O**, then **Enter**.
4. Exit: **Ctrl+X**.

**You should see:** the Ubuntu prompt again. Your Langflow username will be **`atlas-researcher`**, with the password you just saved. Keep it privately. Editing this file later does **not** reset a password already stored in Langflow's database.

## 10. Start Langflow and sign in

**Where:** **WSL — Ubuntu**.

**WSL — Ubuntu:**

```bash
cd "$HOME/source/atlas-knowledge-base-agent"
export UV_CACHE_DIR="$HOME/.cache/atlas-uv"
uv run --locked langflow run --host 127.0.0.1 --port 7860 --env-file "$HOME/.config/garak-atlas/langflow.env"
```

Wait for **Welcome to Langflow** and its **Open Langflow** address. Startup can take several minutes. **Leave this Ubuntu window running. Do not start another copy.**

**Where next:** **Microsoft Edge on Windows**, in a new **InPrivate** window.

1. Open Microsoft Edge. Select **Settings and more (...) → New InPrivate window**, or press **Ctrl+Shift+N**. Confirm that the new window shows **InPrivate**.
2. In that window, open the exact address printed by Langflow, normally `http://localhost:7860`. If it prints a different port, use that port throughout this guide.
3. Sign in with **`atlas-researcher`** and the password from step 9.

**InPrivate is for session privacy, not transport security.** It separates this login from your ordinary browser session. It does **not** encrypt HTTP: the password and session traffic to this HTTP endpoint are unencrypted. This guide binds Langflow to `127.0.0.1` for use from the same laptop. Keep this HTTP setup local; do not expose it to other machines. See Microsoft's [HTTP and HTTPS explanation](https://support.microsoft.com/en-us/edge/secure-your-web-browsing-with-https-first-mode-in-microsoft-edge).

**HTTPS and certificates:** before enabling access from other machines, configure HTTPS with a certificate matching the server hostname, issued by a certificate authority (CA) trusted by your browser and connecting clients. Use your organization's CA for an internal deployment, or a public CA for a domain you control. A standalone self-signed server certificate can encrypt traffic, but clients do not automatically trust it; do not bypass certificate warnings. InPrivate does not change certificate trust. Certificate installation and HTTPS setup are separate from this local walkthrough; see [Langflow's HTTPS certificate settings](https://docs.langflow.org/environment-variables).

**You should see:** Langflow's **Welcome to Langflow** screen with **Create first flow** if the account has no flows, or its **Projects** page if flows already exist. Both mean sign-in succeeded. Continue to Step 11. An incorrect-password message is a failed checkpoint; do not turn off login or create another database to continue.

## 11. Import the supplied ATLAS Agent flow

**Where:** your **Windows browser**, on Langflow's **Welcome to Langflow** screen. It may show **Create first flow** and **Already have a flow? Drag and drop to upload.**

Step 9 created a fresh Langflow database for your own login. MITRE's default startup uses its bundled database, which already contains the ATLAS flow. With this fresh database, import the supplied flow once. The JSON file downloaded in Step 8 supplies the components and their connections; you do not build or wire them yourself.

If **ATLAS Agent v1.1.0** is already listed in this installation, open it and continue to Step 12 without importing another copy.

1. Open **Windows File Explorer** with **Windows+E**.
2. Press **Ctrl+L** to select File Explorer's address bar. Paste `\\wsl.localhost\Ubuntu-24.04\home` and press **Enter**.
3. Open your Ubuntu username folder, then **source → atlas-knowledge-base-agent → flows**. Find **ATLAS Agent v1.1.0.json**.
4. Place File Explorer beside the Langflow browser window.
5. Drag **ATLAS Agent v1.1.0.json** from File Explorer onto the Langflow welcome page, where it says **Already have a flow? Drag and drop to upload.** Do not use **Create first flow** to build an empty flow.
6. Wait for the import to finish. If Langflow displays a flow list, click **ATLAS Agent v1.1.0** to open it.

**You should see:** the **ATLAS Agent v1.1.0** editor with connected components, including **ATLAS Vector Store**, **ATLAS Dataset Sandbox**, **ATLAS Graph Generator**, and **Model Configuration**. Continue to Step 12 to attach the supplied files, then Step 13 to set your model. The fresh import still needs those file selections and your provider credentials.

Langflow may put the imported flow in a default project. Keep that project; Step 14 uses the project containing this flow. If you already have a Projects page instead of the welcome screen, **Upload a flow** can import the same JSON file. See the [flow import reference](https://docs.langflow.org/concepts-flows-import).

## 12. Attach the ATLAS data and instruction files

**Where:** the **Langflow flow editor in your Windows browser**.

The supplied flow JSON leaves the file-upload selections empty. MITRE's bundled database already had these uploads; your fresh import needs them attached once. Keep the existing wires between components. Use the same Windows file-picker route from step 11 to reach the upstream folder.

For each **Read File** component, follow its wire to the named input on **Prompt Template**. Click **+** beside **Files** and upload the matching file below. If an old file is selected, remove it using **X** first. You can zoom in on the canvas to read labels.

| Read File connects to | File under `atlas-knowledge-base-agent` |
| --- | --- |
| `vector_store_contract` | `prompts\tool-contracts\ATLAS Vector Store.md` |
| `dataset_sandbox_contract` | `prompts\tool-contracts\ATLAS Dataset Sandbox.md` |
| `graph_generator_contract` | `prompts\tool-contracts\ATLAS Graph Generator.md` |

Then check these two components:

| Component | What to do |
| --- | --- |
| **ATLAS Dataset Sandbox** | Replace the **CSV File** selection with `data\atlas-data\v2026-07\atlas-nodes-with-emb-text-v2026-07.csv`. |
| **ATLAS Vector Store** | Set **Collection Name** to `atlas-vectors-v2026-07` and **Persistence Path** to `./data/atlas-data/vectors`. |

**You should see:** the three selected `.md` filenames, the selected CSV filename, and those vector-store values. The relative vector path works because step 10 starts Langflow from the upstream project folder. This is the ATLAS knowledge database; optional Chroma search for your own Garak results comes later. Its embedding component may download model assets on first use.

## 13. Configure the model used by the ATLAS Agent

**Where:** the **Langflow flow editor in your Windows browser**.

The **provider** is the service that runs the language model. The steps below describe direct **OpenAI API** access. You need your own API account, billing/access, and model key; a ChatGPT subscription alone is not that API credential.

1. Open the [OpenAI API key page](https://platform.openai.com/api-keys) in another browser tab. Sign in to the API account you intend to use and create or retrieve your own key. Keep it private.
2. Return to the flow. Find the highlighted **Model Configuration** area and its **vLLM** component. Despite that component name, this field accepts an OpenAI-compatible API.
3. Fill in the three fields below. Keep its language-model wire connected to **Agent**.

| Field | Enter |
| --- | --- |
| **Model Name** | A tool-calling model ID enabled for your API account. For example, `gpt-4.1-mini` if your account supports it. |
| **vLLM API Base** | `https://api.openai.com/v1` |
| **API Key** | Your **OpenAI API key**, in the concealed key field. |

The [model reference](https://developers.openai.com/api/docs/models/gpt-4.1-mini) documents Chat Completions and function calling for that example; **this guide has not validated its availability in your account or a fresh ATLAS run with it**. If you already have a working tool-compatible provider/model, use that provider's matching base URL, model ID and key instead. Do not mix credentials from two providers.

Wait for the flow's save indicator. Record your provider name and exact model ID; the runner asks for both later. **You should see:** the intended model/base URL and a concealed key in the saved flow. Do not run a separate Playground test for this walkthrough. Step 17 will make the confirmed submission.

## 14. Enable MCP access and create a Langflow API key

**Where:** **Langflow in your Windows browser**.

MCP is the connection the Windows runner uses to send the handoff to your flow.

1. Return to the project containing your imported **ATLAS Agent v1.1.0** flow and open its **MCP Server** tab. Use that project's actual name; it need not be named **ATLAS Agent**. This is the project tab, not **Settings → Langflow MCP Client**.
2. Click **Edit Tools**. Enable the checkbox for the imported ATLAS flow. Click its tool name and set it to **`atlas_agent_v110`**. Close the dialog to save.
3. Beside **Auth**, choose **Add Auth** or **Edit Auth**, then **API Key**. If **API Key** is already shown, keep it enabled.
4. Open your profile menu at the top right → **Settings → Langflow API Keys → Add New**. Name the key **Garak runner**. If asked for expiry, choose a period that covers your test. Click **Create API Key** and copy the key into your password manager/private notes.
5. Return to that same project's **MCP Server** tab. Select **JSON → Windows → Streamable HTTP**.
6. Find the URL ending in `/api/v1/mcp/project/.../streamable`. Copy **just that URL**, without quotes. Keep its actual localhost port. You will paste it into PowerShell next.

**You should see:** **Auth: API Key**, the ATLAS tool listed, and the Streamable HTTP URL. The displayed `cmd`, `uvx` and `mcp-proxy` lines are for other clients; you do not run them for this runner. See [Langflow's MCP setup reference](https://docs.langflow.org/1.10.0/mcp-server).

Keep these credentials distinct:

| Credential | Where you use it |
| --- | --- |
| Ubuntu password | Ubuntu `sudo` prompts |
| Langflow password | Browser sign-in as `atlas-researcher` |
| OpenAI/provider API key | The model component in step 13 |
| **Langflow API key** | The runner's hidden prompts in steps 15 and 17 |

## 15. Check that the runner can find your ATLAS tool

**Where:** switch to **normal Windows PowerShell**. Keep the Ubuntu window running Langflow. The block restores the runner paths, so it also works in a newly opened PowerShell window.

**Windows PowerShell:**

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
Set-Location -LiteralPath $repo
$endpoint = Read-Host 'Paste the project Streamable HTTP URL (no key)'
$discoveryDir = Join-Path $labRoot 'garak-playbook-private\mcp-discovery'
& $scannerPython "$repo\tools\inspect_atlas_mcp.py" `
    --url $endpoint --output-dir $discoveryDir --api-key-prompt
if ($LASTEXITCODE -ne 0) { throw 'Discovery failed. Stop and keep the displayed error.' }
```

Paste the URL from step 14. At **Langflow API key (hidden; session only)**, paste your **Langflow API key** and press Enter. No characters are displayed.

**You should see:** `Discovery status: discovery_complete`, `Tool invocations: 0`, and a **Discovery report** path. This check does not ask the model a question.

Now paste the **full Discovery report path** printed above when this next block asks for it:

**Windows PowerShell:**

```powershell
$discovery = Read-Host 'Paste the full Discovery report path printed above'
@'
import atlas_mcp, sys
connection = atlas_mcp.load_discovery(sys.argv[1])
print("Validated tool:", connection["tool"]["name"])
print("Endpoint:", connection["endpoint"])
'@ | & $scannerPython - $discovery
if ($LASTEXITCODE -ne 0) { throw 'The discovered ATLAS tool does not match this runner. Stop here.' }
```

**You should see:** `Validated tool: atlas_agent_v110` and your endpoint. The check also validates the server identity and input schema. If it fails, do not proceed to `SEND`: HTTP 401/403 points to authentication; a tool/schema error points to the exposed flow or Langflow version. Keep the report for diagnosis.

## 16. Prepare the included sample Garak results

**Where:** the **same normal Windows PowerShell** window.

Copy the whole block. It prepares the included sample, creates its saved handoff and checksums, then opens the handoff in Notepad. It makes no model request and does not run Garak.

**Windows PowerShell:**

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

**You should see:** `SYNTHETIC example ready`, Run ID **`synthetic-example`**, and `process_outcome_unknown`. That status is intentional: these are sample records, not a completed scan. There is one sample response and one sample detector flag; neither is real model evidence. Notepad should display `atlas_handoff.md`.

Read the handoff, then close Notepad. Keep PowerShell open. If the sample directory already exists from an earlier attempt, preserve it and use the resume instructions after the finish line; do not replace its files.

## 17. Send the sample handoff to ATLAS

**Where:** the **same normal Windows PowerShell** window. Langflow must still be running in Ubuntu.

The diagram shows the overall workflow. For this setup test, the sample from step 16 takes the place of a real saved scan. Optional local search is a separate step later.

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

**Windows PowerShell:**

```powershell
& $scannerPython "$repo\playbook.py" atlas --run-dir $savedRun --discovery $discovery
```

Respond to the prompts in order:

1. **ATLAS model provider shown in Langflow:** enter the provider from step 13, such as `OpenAI`.
2. **ATLAS model name shown in Langflow:** enter exactly the **Model Name** from step 13.
3. Review the displayed endpoint, `atlas_agent_v110`, Run ID `synthetic-example`, and handoff text. These provider/model labels record your selection; they do not change the flow.
4. To submit, type **`SEND`** and press Enter. Pressing Enter without SEND cancels.
5. At the hidden key prompt, paste your **Langflow API key** and press Enter.

Wait for the reply. **This is the paid-call boundary if your ATLAS model provider charges for usage.** One MCP submission may trigger multiple model/tool calls; the runner does not measure those charges. Initial data/model loading may also take time. Do not submit a second time while waiting.

**You should see:**

- `ATLAS status: response_received_unreviewed`
- `ATLAS archive:` followed by a folder path
- `Unreviewed ATLAS reply:` followed by a file path
- `Recorded Garak scan outcome is unchanged.`

If an error or timeout appears, preserve the displayed archive and stop before retrying; the provider may already have processed the request.

## 18. Open the saved ATLAS reply

**Where:** the **same normal Windows PowerShell** window.

Copy the **folder path after `ATLAS archive:`** from step 17, without the label. Paste it when this command asks:

**Windows PowerShell:**

```powershell
$atlasSubmission = Read-Host 'Paste the ATLAS archive folder path from step 17'
notepad.exe "$atlasSubmission\atlas_response.md"
```

**You should see:** Notepad displaying the saved ATLAS reply. **This is the core setup finish line.** A reply that says the sample evidence is insufficient is valid; success here means the handoff reached your agent and its reply was saved.

The archive is inside `%LOCALAPPDATA%\GarakPlaybook\examples\synthetic-atlas-run\atlas-submissions`. It contains the submitted handoff, reply, submission record and checksums. Keep it private. The reply is **unreviewed analysis**, mappings are **candidates**, and detector flags are **screening results**. ATLAS cannot assess model responses that were not included in the handoff.

Record your commit ID from step 3, the final status and the reply path. If you needed an instruction from chat or another laptop, record the step number and missing instruction as a documentation gap. Do not rerun the fourteen-probe campaign for this installation check.

---

## After the finish line: resuming or using an existing installation

### Reopen after shutting down or restarting

**Where:** **Start → Ubuntu 24.04 LTS**. If it is not listed, use normal Windows PowerShell to run `wsl -d Ubuntu-24.04`. If Langflow is already running, keep that instance; do not start another.

**WSL — Ubuntu, for the installation created by this guide:**

```bash
cd "$HOME/source/atlas-knowledge-base-agent"
export PATH="$HOME/.local/bin:$PATH"
export UV_CACHE_DIR="$HOME/.cache/atlas-uv"
uv run --locked langflow run --host 127.0.0.1 --port 7860 --env-file "$HOME/.config/garak-atlas/langflow.env"
```

**You should see:** the Welcome message. Leave Ubuntu running, open its printed localhost address in your Windows browser, and sign in. Your flow and uploaded files should still be present. Do not repeat account creation or flow import.

Open **Start → Windows PowerShell** normally and restore the paths:

**Windows PowerShell:**

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
$savedRun = Join-Path $labRoot 'examples\synthetic-atlas-run'
Set-Location -LiteralPath $repo
```

**You should see:** the repository prompt. This restores variables; it installs or submits nothing.

- If discovery was not complete, follow step 15. If it was complete, run `$discovery = Read-Host 'Paste your saved Discovery report path'`, enter the path you recorded, and use the validation block in step 15.
- If the sample already exists, skip its creation in step 16 and open it with `notepad.exe "$savedRun\atlas_handoff.md"`. The runner checks its saved hashes before submission.
- If a reply was already received, go straight to step 18 with that archive path. Do not repeat SEND just to reopen the reply.

### If you already completed the Garak quick start

Keep your existing checkout, scanner environment and `config.private.json`. Set the Windows paths above to your actual locations, verify `playbook.py --help` as in step 4, then continue at the first unfinished step. Do not rerun `tools/configure.py` over existing private configuration; it refuses to replace it.

The sample-to-ATLAS path does not need `config.private.json`. For later **real scans**, use the [Windows scan quick start](../README.md#windows-quick-start) and your intended target configuration. During initial scan configuration, `--data-root` is the optional way to select different storage; retain that location afterward.

### If you already have a working ATLAS Agent

Keep its database, account, model provider, flow and private environment file. Use its established startup command in its existing WSL directory, then continue at step 14. For an installation using a local `.env` file, that command is:

**WSL — Ubuntu, from the existing upstream ATLAS directory:**

```bash
uv run langflow run --env-file .env
```

**You should see:** the existing instance's Welcome message. Use its printed port. Editing an environment-file password does not reset an existing database account; use the installed version's account-recovery procedure if needed.

For a real saved Garak run, set `$savedRun` to that run's directory, review what its handoff will disclose, and use steps 17–18. Do not sanitize by editing hashed original evidence. [Kumu](operator-guide.md) is a separate confirmed action, not part of the first submission.

## Optional: index and search locally

Start only after step 18. This uses the **same saved example and ATLAS archive**. It needs no new scan or cloud call. Use a dedicated research store; do not point it at the upstream ATLAS vector store or another existing Chroma database.

### Ollama and EmbeddingGemma

**Where:** your Windows browser, then normal Windows PowerShell.

Reuse a working Windows Ollama installation. Otherwise download the Windows installer from [Ollama](https://ollama.com/download/windows), open the downloaded installer, and complete installation. Open **Start → Ollama**, then reopen **Start → Windows PowerShell** normally so the `ollama` command is available. The Windows app normally serves loopback port 11434. Do not start a second `ollama serve` if it is already running. [EmbeddingGemma requires Ollama 0.11.10 or later](https://ollama.com/library/embeddinggemma).

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

Restore the Windows paths in this window and enter the archive folder from the core setup:

**Windows PowerShell:**

```powershell
$repo = Join-Path $env:USERPROFILE 'source\garak-mitre-atlas-agent'
$labRoot = Join-Path $env:LOCALAPPDATA 'GarakPlaybook'
$scannerPython = Join-Path $labRoot 'scanner-env\Scripts\python.exe'
$savedRun = Join-Path $labRoot 'examples\synthetic-atlas-run'
$atlasSubmission = Read-Host 'Paste the ATLAS archive folder path from step 18'
Set-Location -LiteralPath $repo
```

**You should see:** the repository prompt. These paths select the saved example and reply; no new submission is made.

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
& $researchPython -c "import importlib.metadata; v=importlib.metadata.version('chromadb'); assert v == '1.5.9', v; print('Chroma', v)"
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
New-Item -ItemType Directory -Path (Split-Path -Parent $researchConfig) -Force | Out-Null
$researchSettings | ConvertTo-Json | Set-Content -LiteralPath $researchConfig -Encoding UTF8
```

**Success:** `Chroma 1.5.9` and a separate research configuration. The main scanner config remains untouched. No Chroma server is required. On first use the research root must be new/empty; an unowned nonempty directory is rejected. Do not delete an existing database to bypass that check.

If reusing research configuration, set `$researchConfig` to its actual full path before continuing. Keep `$savedRun` and `$atlasSubmission` from steps 16–18. Index once, then repeat the **same** command to verify no duplicate:

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
| Windows runner installation and integrations | Full Windows pass at `09e8128`; seven Windows delta checks at `4fedd3f`. See the [release record](release-v1.md). This documentation revision does not claim a new full Windows pass. Record the actual clean-laptop commit and result separately. |
| Existing Langflow/ATLAS deployment | Startup, authenticated discovery, confirmed MCP submission and reply archival were exercised in the maintainer's existing Windows/WSL lab. |
| Fresh WSL/uv/Langflow, new account and flow import | Instructions checked against upstream revision `b2bca6438e99cb72752c27be1728f062b6f943ca` and official documentation. A clean-machine execution of this exact route remains **unverified**. Current upstream docs may describe a newer UI than the pinned flow/runtime. |
| Synthetic saved-run preparation and archive routing | The guide's fixture assembly is checked offline against the existing renderer/loader. MCP archival is exercised with a synthetic protocol server; this does not validate a new Langflow deployment or paid model. |
| Optional research search | The maintainer exercised real local EmbeddingGemma indexing, unchanged reindexing, model/probe filters, search and evidence opening. This guide's synthetic example is checked with real embedded Chroma and fake embedding vectors; a fresh Windows installation following every new instruction remains **unverified**. |
| Release scope | Runtime, profiles, credentials and the fourteen-probe campaign are unchanged. Kumu remains separate, AVID and broader probes remain deferred, and public release/tagging require owner approval. |

The revised instructions still require the clean-laptop test; a documentation or syntax check is not an installation pass. Keep the guide's expected results distinct from observed validation evidence.
