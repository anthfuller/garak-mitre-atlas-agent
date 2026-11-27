# Analysis and Kumu URL in one submission

On November 27, 2026, an assisted Windows test used runtime commit `82ba06f63c582b933f7493c77a60656ccf2e51b3` to submit a synthetic Garak handoff. The operator typed `SEND` once. The saved reply proposed `AML.T0068` (LLM Prompt Obfuscation) and included a Kumu link. Opening the link displayed a graph focused on that technique.

## Observed result

| Check | Evidence | Result |
| --- | --- | --- |
| Operator confirmation | Console output shows one `SEND`, followed by `response_received_unreviewed` and `graph_received_target_and_coverage_checked`. | One confirmation was observed. |
| Analysis and URL saved together | The archived reply contains the analysis, candidate `AML.T0068`, its official ATLAS link and the full Kumu URL. Only `AML.T0068` is discussed. | Saved-file check passed. |
| Matching browser view | The browser screenshot shows the same URL and the `AML.T0068` technique description beside the graph. | Browser check passed for this example. |
| Interpretation | The reply labels the mapping tentative and explains that the synthetic excerpt does not demonstrate an encoded attack. | No attack success or model resistance was established. |

The saved URL is `https://embed.kumu.io/99b02113875c5b03b510b4b6968b2566#atlas/aml-t0068?focus=1`. It matches the expected project, map and sole discussed ID. The archive's **Browser rendering remains unverified** line describes the runner's automatic-check boundary; the subsequent screenshot provides the manual browser result. The archive remains unchanged.

Evidence fingerprints (original evidence retained privately):

- Saved analysis SHA-256: `9766b5a2a1dde452d8dfa19904bfc2f36bb070eb2b3752f1e6e96c14ba4d3c96`.
- Browser screenshot SHA-256: `4dff2951affd6146e8786576e6d0567dce4ab44c5ab44ed3923e9e702bc2ac64`.

## How the workflow operates

After `SEND`, the runner wraps the unchanged saved handoff in an analysis-and-graph request. ATLAS is asked to retain candidate labels, verify discussed AML IDs with its Dataset Sandbox, and use its Graph Generator. The same reply is requested to contain the analysis and full original graph URL. The runner does not construct or repair that URL.

The runner checks the independently configured project/map and every discussed AML ID, including rejected or contextual IDs. Defaults come from [MITRE's pinned flow](https://github.com/mitre-atlas/atlas-knowledge-base-agent/blob/b2bca6438e99cb72752c27be1728f062b6f943ca/flows/ATLAS%20Agent%20v1.1.0.json): project `99b02113875c5b03b510b4b6968b2566`, map `atlas`. A custom deployment can pass `atlas --kumu-config PATH` with its expected destination.

Each submission retains the original handoff, full request, returned response with credential redaction, readable analysis, checksums and validation record. Equivalent duplicate analysis blocks display once; distinct content remains visible. A graph failure preserves the analysis and reports the reason. Historical archives are not rewritten.

The client is designed to dispatch one MCP flow call per confirmed action without automatic retries. The agent may make multiple model/tool calls within that invocation. This design is tested offline; it is not a measured dispatch count for the observed submission.

## Reproduce the saved-file and browser check

Follow [Steps 14–18 of the install guide](install-and-verify.md#14-enable-mcp-access-and-create-a-langflow-api-key) using the included sample and a working Langflow flow. Keep the Ubuntu terminal running. The procedure needs no new Garak scan or separate graph action; submitting to ATLAS can incur model charges.

1. Confirm the displayed handoff with `SEND` once and wait for the result.
2. Check for `ATLAS status: response_received_unreviewed` and `Kumu status: graph_received_target_and_coverage_checked`.
3. Open the printed `atlas_response.md` path. Read the candidate analysis and copy its Kumu URL into the browser.
4. Compare the discussed technique ID with the focused graph view. The observed example proposed `AML.T0068`; a different answer needs its own evidence review.

If a step fails, retain the archive and error. Do not resubmit automatically or use a separate graph action to claim this check passed. An existing saved reply can be reopened without another model call.

## Evidence and limits

The console shows one operator confirmation. The matching submission record and internal Langflow tool trace were unavailable for independent review, so the dispatch and retry counts and the internal tool calls remain unverified for this submission. Claims that the Dataset Sandbox or Graph Generator ran internally are agent-reported.

The earlier Playground check has separate tool evidence: `atlas_dataset_sandbox` returned a successful dataset record with ID `AML.T0054` and name `LLM Jailbreak`, and the Playground reply matched it. This does not establish the internal calls made by the later MCP submission.

For runtime `82ba06f`, **157 targeted offline tests passed**: 50 ATLAS/Kumu transport/archive tests and 107 graph, research-index, handoff, scan-profile and runner tests. Research tests use real embedded Chroma with synthetic vectors. Two additional checks used the pinned Graph Generator's methods with schema stubs to produce accepted URLs for one and three IDs, without running Langflow.

These offline checks cover URL target and ID coverage, archive preservation, duplicate and distinct replies, graph failures, and saved-record consumer compatibility. They made no paid calls and did not open Kumu. The browser evidence above establishes only the observed synthetic example. Broader research quality, confirmed mappings and an independent guide-only installation remain unverified.
