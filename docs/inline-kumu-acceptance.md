# Analysis and Kumu URL in one submission

**Status: current-laptop acceptance passed for AML.T0068 on November 27, 2026, using runtime commit `82ba06f63c582b933f7493c77a60656ccf2e51b3`.** The next guide-only clean-laptop test may proceed. Public release and tagging still require owner approval. No existing flow import, model edit, file reattachment, new Garak scan or separate graph action was needed for this checkpoint.

## Observed result

| Check | Evidence supplied by the operator | Result |
| --- | --- | --- |
| One confirmed submission | Console output shows `SEND`, followed by `response_received_unreviewed` and `graph_received_target_and_coverage_checked`. | Passed for the observed submission. |
| Analysis and URL saved together | Uploaded `atlas_response2.md` contains the complete analysis, candidate AML.T0068, its official ATLAS link, and the full Kumu URL under **View Kumu graph**. Only AML.T0068 is discussed. | Passed. |
| Matching browser view | Supplied `Kumu_link.png` displays the same URL and **AML.T0068 — LLM Prompt Obfuscation** as the focused technique. | Passed for this browser view. |
| Interpretation preserved | The reply calls the mapping tentative, explains that the synthetic excerpt does not demonstrate an encoded attack, and keeps detector observations separate from behavior and unverified conclusions. | Candidate status retained; no attack success or model resistance established. |

The URL is `https://embed.kumu.io/99b02113875c5b03b510b4b6968b2566#atlas/aml-t0068?focus=1`. It matches the expected project, map and sole discussed ID in the uploaded reply. The original response's **Browser rendering remains unverified** line records the runner's automatic-check boundary; the later screenshot supplies the manual browser check. The original archive is not rewritten.

Evidence fingerprints (original uploads retained privately):

- `atlas_response2.md` SHA-256: `9766b5a2a1dde452d8dfa19904bfc2f36bb070eb2b3752f1e6e96c14ba4d3c96`.
- `Kumu_link.png` SHA-256: `4dff2951affd6146e8786576e6d0567dce4ab44c5ab44ed3923e9e702bc2ac64`.

This pass covers the saved-file and browser finish line for one synthetic case. Internal Dataset Sandbox/Graph Generator execution remains agent-reported for this submission; no internal tool trace or complete raw archive was supplied for this review. Broader research quality and a guide-only fresh installation remain unverified.

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

If any step fails, preserve the archive and displayed error. Do not submit again automatically or use a separate graph action to claim this acceptance passed. The README and [Step 18 of the install guide](install-and-verify.md#18-open-the-saved-atlas-reply) now describe this observed finish line.

## Evidence and limits

Offline result for runtime commit `82ba06f`: **157 targeted tests passed** (50 ATLAS/Kumu transport and archive tests; 107 graph, research-index, handoff, scan-profile and runner tests). The research tests use real embedded Chroma with synthetic vectors. Separately, the pinned Graph Generator's unchanged methods produced accepted URLs for one and three IDs with lightweight schema stubs, without running Langflow. None of these offline checks made a paid call or opened Kumu; the separately observed laptop result is recorded above.

- Synthetic local MCP checks exercise one confirmation/one invocation, original evidence and prior-archive preservation, raw reply retention, request integrity, readable-analysis extraction, and existing saved-record consumer compatibility.
- URL checks reject the wrong project, map, host, scheme, anchor, focus, omitted/extra/reordered AML IDs, invalid graph status, conflicting replies, and changed private destination configuration. Copyable URLs are sufficient; no iframe is required or executed.
- Equivalent replies with different blank lines display once; different analyses remain visible. An unsuccessful graph does not discard a successful analysis.
- These are offline checks. They do not prove the model obeyed the prompt, the agent called either tool, the dataset contains an ID, or Kumu renders it. Internal tool execution is agent-reported unless separately inspected in Langflow. A browser acceptance pass establishes only the observed case, not broader research quality or confirmed mappings.
- Garak scan settings, the closed fourteen-probe campaign, Kumu's flow configuration, Chroma/EmbeddingGemma and the user's existing Langflow model/files are unchanged.
