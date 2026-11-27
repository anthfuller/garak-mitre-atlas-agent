# 0.2.0: installed probe browser

**Historical version 0.2.0 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

Historical release notes. Version 0.2.1 adds Back at review; see [the correction](patch-0.2.1.md) for the subsequent navigation correction and the cumulative update.

The existing runner now lists the full probe registry from the configured Garak 0.17.0 installation. It shows twenty entries per page, with case-insensitive name/family search, descriptions, runner support status, and short reasons for unavailable probes. Default-inactive probes remain visible and can be explicitly selected when supported. Probe discovery and execution support are separate: the catalog is not restricted to the compatibility list.

## Operator flow

Start the existing `menu --config <private-config-path>` command in **Windows PowerShell**. Choose the target/model, then:

```text
[1] Existing campaigns
[2] Browse or search all installed probes
[3] Exit
```

`base64-32` and `dan-wild-32` remain in Existing campaigns. In the browser, use `N`/`P` to change pages, `S` to search, `A` to clear the search, or `B`/Enter for the main menu. Select a probe by its number on the current page. An unavailable selection prints its reason and remains in the browser.

Selecting a supported probe displays the exact probe, detector, target/model/endpoint, workload basis, limits, settings, dependency/API requirements and interpretation limits. **Only typing `RUN` starts the scan.** At confirmation, Enter, any other answer, Ctrl+C or EOF cancels without creating a scan folder, calling preflight or launching Garak. The runner then returns to the shell. Browser selection and searching do not contact a model.

The original evidence, manifest, result accounting, concise ATLAS handoff and single-action Copy/Notepad menu use the existing workflow. Handoff-only regeneration remains offline and preserves its previous revision. OpenAI, profile saving, GitHub publication and Chroma/embeddings are not added by this release.

## Execution support in this release

The full reference installation contains 191 probes across ten pages. Your catalog is read at runtime from your configured installation. Fourteen pairs are enabled by a source-checked compatibility policy:

| Probe | Detector | Workload |
| --- | --- | --- |
| `encoding.InjectBase64` | `encoding.DecodeMatch` | Native pruning, at most 32 |
| `encoding.InjectBase16` | `encoding.DecodeMatch` | Native pruning, at most 32 |
| `encoding.InjectBase32` | `encoding.DecodeMatch` | Native pruning, at most 32 |
| `encoding.InjectAscii85` | `encoding.DecodeMatch` | Native pruning, at most 32 |
| `encoding.InjectHex` | `encoding.DecodeMatch` | Native pruning, at most 32 |
| `encoding.InjectROT13` | `encoding.DecodeMatch` | Native pruning, at most 32 |
| `dan.DanInTheWild` | `mitigation.MitigationBypass` | Native pruning, expected 32 for the pinned corpus |
| `goodside.WhoIsRiley` | `goodside.RileyIsnt` | Full fixed corpus, 6 |
| `goodside.ThreatenJSON` | `goodside.PlainJSON` | Full fixed corpus, 1 |
| `goodside.Davidjl` | `goodside.Glitch` | Full fixed corpus, 4 |
| `goodside.Tag` | `base.TriggerListDetector` | Full generated corpus, 32 |
| `lmrc.Anthropomorphisation` | `lmrc.Anthro` | Full fixed corpus, 6 |
| `lmrc.Deadnaming` | `base.TriggerListDetector` | Full fixed corpus, 6 |
| `lmrc.QuackMedicine` | `lmrc.QuackMedicine` | Full fixed corpus, 1 |

Other installed probes show as unavailable in this runner, with a modality, dependency or unvalidated-workload explanation. This is not a claim that Garak cannot run them. Further support requires reviewing their workload, detector and any helper model/service use; it is not inferred solely from a probe's name or metadata. Neither optional dependencies nor models are installed automatically.

Browser selections use temperature 0, seed 42, one response per attempt, 256 output tokens, sequential requests and a 1,800-second wall-time limit. These values are shown before confirmation and recorded as a new experiment. The generation settings of the existing campaigns are unchanged. No universal expected count is derived from the prompt cap. Browser encoding runs retain a nullable expected count and a 32-attempt ceiling; the fixed corpora have separately justified expected counts. Missing outputs, errors and cap breaches remain coverage gaps. HTTP retries are not bounded by the logical-attempt cap.

Garak 0.17.0 excludes base detector classes from explicit detector selection. For Tag and Deadnaming, the runner uses `--detectors auto`, with extended detectors disabled, allowing the audited probewise harness to load the stated `base.TriggerListDetector`. Both the selected detector and selection mechanism are recorded; the report's actual detector must match. Other enabled probes use explicit detector selection.

## Apply

Save `Garak_Playbook_0_2_0_Probe_Browser.zip` beside the existing `garak-playbook` directory. From that parent directory, run in **Windows PowerShell**:

```powershell
Expand-Archive -LiteralPath .\Garak_Playbook_0_2_0_Probe_Browser.zip -DestinationPath . -Force -ErrorAction Stop
```

This single patch replaces runner/test/documentation files and adds the catalog helper and support policy. It does not include or replace `campaigns.json`, private configuration, the Garak environment, models, databases or previous evidence. No earlier patch ZIP is required over the existing working installation. Launch the same menu command afterward; no automatic scan occurs on launch.

## Implementation and validation

The inventory helper runs through `garak_python` from private configuration. It uses `garak._plugins.enumerate_plugins('probes')` and `plugin_info`, verified against the installed 0.17.0 source. It does not instantiate plugins and denies network connections. Its temporary XDG configuration/cache is removed after inspection. Inventory errors are shown rather than silently dropping probes.

The source hashes in `probe-support.json` bind each enabled pair's workload and detector review to the installed version. Preflight checks those sources again after confirmation. The manifest retains the selected probe's metadata, default-active flag, inventory method/hash/count, workload basis and detector mode. Hashes establish file correspondence, not a security certification.

- 87 offline unit tests passed on Linux, including navigation/search/pagination, full mocked registry coverage, unavailable reasons, cancellation, unchanged existing campaigns and handoff actions, selected-source changes, exact single-probe execution and synthetic-report processing.
- Real installed-registry comparison: all 191 probes reachable across ten pages, including inactive entries; all 14 reviewed probe/detector pairs constructed with their expected counts or cap bounds; zero generation requests.
- Six real Garak 0.17.0 CLI runs passed against a synthetic Ollama-protocol endpoint: existing Base64 and DAN campaigns (32 each), Base32 (32), WhoIsRiley (6), Tag (32), and inactive Davidjl (4). Settings, native probe/detector identity, counts, artifacts and unattended behavior were checked.
- No real LLM or paid API was used. These synthetic outputs are transport/accounting validation, not adversarial findings.
- The new browser has not been exercised on the operator's Windows machine. Clipboard/Notepad adapters are unchanged and their unit checks use mocks. Existing Windows process-tree cancellation remains outside this validation.
