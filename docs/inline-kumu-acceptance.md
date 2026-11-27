# Analysis and Kumu URL in one submission

**Status: offline checks passed; current-laptop live acceptance pending.** Hold the next clean-laptop test and public release/tagging. No existing flow import, model edit, file reattachment, new Garak scan or separate graph action is required.

## What changed

The runner sends the existing saved handoff inside an analysis-and-graph request after one explicit `SEND`. ATLAS is asked to retain candidate labels, verify all discussed AML IDs through its Dataset Sandbox, and use its Graph Generator for those IDs. The same reply must contain the analysis and the full original graph URL. The runner does not create or repair that URL.

The runner checks the configured project/map and every discussed AML ID, including rejected/contextual IDs. Defaults are independently pinned to [MITRE's supplied flow](https://github.com/mitre-atlas/atlas-knowledge-base-agent/blob/b2bca6438e99cb72752c27be1728f062b6f943ca/flows/ATLAS%20Agent%20v1.1.0.json): project `99b02113875c5b03b510b4b6968b2566`, map `atlas`. Custom deployments can use the existing two-field private configuration through `atlas --kumu-config PATH`.

Each submission preserves the original handoff, full request prompt, raw returned response (with existing credential redaction), readable analysis, checksums and validation record. Historical archives are unchanged. Equivalent duplicate analysis blocks display once; distinct content remains visible. A graph failure retains the analysis and reports the reason without retrying.

## Current-laptop acceptance

Use the saved run whose earlier analysis discussed **AML.T0068**, the existing discovery report, and the existing working Langflow flow. Keep its Ubuntu terminal running. Update the checkout to this revision, then run in normal Windows PowerShell, using the paths already established by the guide:

```powershell
& $scannerPython "$repo\playbook.py" atlas --run-dir $savedRun --discovery $discovery `
    --provider OpenAI --model gpt-6.1-sol
```

Review the handoff and expected Kumu destination, confirm `SEND` once, and enter the Langflow key at the hidden prompt. This makes one MCP flow invocation; the agent may make several paid model/tool calls. It does not run Garak.

Acceptance requires all of the following:

1. The runner prints `ATLAS status: response_received_unreviewed` and `Kumu status: graph_received_target_and_coverage_checked`.
2. Open the **newly printed** `atlas_response.md` path in Notepad. It contains the candidate analysis and the full Kumu URL together.
3. Copy that URL into the browser. Confirm **AML.T0068** is visible in the focused Kumu view. Keep the new archive and screenshot/result for review.

If any step fails, preserve the archive and displayed error. Do not submit again automatically or use a separate graph action to claim this acceptance passed. The README/install-guide finish line remains pending until the current-laptop result is reviewed.

## Evidence and limits

Offline result for this revision: **157 targeted tests passed** (50 ATLAS/Kumu transport and archive tests; 107 graph, research-index, handoff, scan-profile and runner tests). The research tests use real embedded Chroma with synthetic vectors. Separately, the pinned Graph Generator's unchanged methods produced accepted URLs for one and three IDs with lightweight schema stubs, without running Langflow. None of these checks made a paid call or opened Kumu.

- Synthetic local MCP checks exercise one confirmation/one invocation, original evidence and prior-archive preservation, raw reply retention, request integrity, readable-analysis extraction, and existing saved-record consumer compatibility.
- URL checks reject the wrong project, map, host, scheme, anchor, focus, omitted/extra/reordered AML IDs, invalid graph status, conflicting replies, and changed private destination configuration. Copyable URLs are sufficient; no iframe is required or executed.
- Equivalent replies with different blank lines display once; different analyses remain visible. An unsuccessful graph does not discard a successful analysis.
- These are offline checks. They do not prove the model obeyed the prompt, the agent called either tool, the dataset contains an ID, or Kumu renders it. Internal tool execution is agent-reported unless separately inspected in Langflow. A browser acceptance pass establishes only the observed case, not broader research quality or confirmed mappings.
- Garak scan settings, the closed fourteen-probe campaign, Kumu's flow configuration, Chroma/EmbeddingGemma and the user's existing Langflow model/files are unchanged.
