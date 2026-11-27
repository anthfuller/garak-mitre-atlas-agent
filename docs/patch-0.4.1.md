# 0.4.1: optional Kumu graph from saved ATLAS analysis

**Historical version 0.4.1 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

Version 0.4.1 extended 0.4.0 with `kumu_mcp.py`, a `kumu` command and completion/handoff menu action **5**. It uses the existing authenticated MCP transport and fixed `atlas_agent_v110` tool. No package, model, scan profile, Langflow configuration, original handoff or ATLAS analysis is changed.

## Operator workflow

Keep Langflow running. Use a normal **Windows PowerShell** window, with the Garak runner closed while applying the ZIP. Extract the ZIP over the project parent directory; its top-level folder is `garak-playbook`.

Run against an existing run and its saved ATLAS submission:

```powershell
# Example paths; use your existing Garak Python and project locations.
& 'C:\AI-Lab\garak-env\Scripts\python.exe' `
  'D:\AI-Lab\projects\garak-playbook\playbook.py' kumu `
  --run-dir 'D:\AI-Lab\evaluations\existing-run' `
  --submission 'D:\AI-Lab\evaluations\existing-run\atlas-submissions\existing-submission'
```

Alternatively, use action **5** in `handoff` or the scan-completion menu. If exactly one ATLAS submission exists, it is selected automatically; multiple submissions require selection. This action requires a prior successful ATLAS analysis; it does not create one by sending the original handoff again.

1. The runner verifies the run and ATLAS archive checksums, run identities, original report/manifest/summary hashes, submitted handoff and recorded conversation ID.
2. It lists unique canonical AML IDs found in the saved response, in first-occurrence order, with excerpts of their surrounding context. This is a mention inventory, not automatic acceptance of a mapping. Review the saved analysis; exclude rejected mappings and background examples. Enter index numbers such as `1,2`, in anchor-first order, or `A` to select all displayed IDs. Enter/B cancels. Up to 50 focus IDs are supported by this client; a lower server limit can still reject the request.
3. Review the run, selected source, destination, IDs, previous provider/model observation, and the complete generated graph request. Type `GRAPH` to authorize one additional ATLAS invocation. The Langflow API key is then entered in a hidden prompt. An empty confirmation, another word or Ctrl+C cancels before network activity.
4. The runner rechecks MCP identity/schema and calls the same bound ATLAS flow with a fresh conversation UUID. It generates the prompt itself: only run ID, approved IDs and fixed graph instructions are sent. Prior attack excerpts and analysis prose are not replayed. No graph URL is constructed locally.
5. ATLAS is asked to verify all selected IDs using its Dataset Sandbox, invoke its Graph Generator, and return one JSON result containing `run_id`, `verified_ids` and `graph_result`. Partial graphs are not accepted automatically.
6. The runner checks the returned run ID, ordered ID list, anchor, focus mode, URL focus selectors and iframe source. For multiple IDs, the published generator's outbound-one-hop directives must include every selected ID exactly once. A two-ID request returning a one-ID URL is a failed graph-validation result. No URL is silently repaired or substituted.
7. On an accepted reply, it prints the exact returned URL and saved file paths. An optional one-shot menu offers **Open Kumu view / Return to PowerShell**. Enter returns without opening anything. Opening is explicit, and a browser failure does not change saved graph or scan outcomes.

`--discovery` can supply a current authenticated discovery report for the same ATLAS project if its saved report moved or became stale. Default discovery is the path recorded with the selected ATLAS submission. `--timeout-seconds` has the same 300-second default and 30–1800 range as the analysis client; these are socket/response-processing limits, not guaranteed server cancellation. `--yes` is not supported for `kumu`, and noninteractive calls stop before network activity. Existing unattended scan/handoff behavior remains unchanged.

## Evidence and limits

Each request gets a new `kumu-submissions/<UTC>-<unique-id>/` directory under the run:

| File | Contents |
| --- | --- |
| `graph_prompt.md` | Exact automatically generated outgoing prompt |
| `request.json` | MCP call and fresh conversation ID |
| `response.json` | Complete returned result when received, including duplicate blocks |
| `submission.json` | Selected source/run, hashes, ordered IDs, connection, confirmation, status, validation limitations and preservation checks |
| `mcp-exchanges.json` | Protocol exchanges using the existing credential-redaction behavior |
| `kumu_result.json` | Accepted structured result, once, when validation succeeds |
| `kumu_url.txt` | Exact returned URL bytes, when accepted |
| `kumu_iframe.txt` | Exact returned iframe bytes, when accepted; inert text, not executed HTML |
| `checksums.json` | This graph archive's hashes |

Equivalent JSON text blocks are accepted once for the derived graph result. Both original blocks remain in `response.json`. Conflicting results are rejected. The original Garak files, root checksum index, ATLAS submission and previous graph archives are never overwritten.

`graph_received_focus_checked` means the returned URL and metadata contain the selected IDs with the documented focus shape. It does **not** independently establish that ATLAS called its internal Dataset or Graph Generator tools, that each ID was actually verified there, that the configured Kumu project is authoritative, or that the browser rendered every node. Internal tool execution and dataset verification are agent-reported through the flow's text reply. Visual rendering requires operator review. Mappings remain candidates and neighboring graph nodes are not additional run findings.

`graph_reply_not_validated` retains the response and reason without producing an accepted link or opening it. Errors and uncertain execution are archived. After timeout, disconnect or interruption, server work might continue. There is no automatic retry. A received response followed by an archive failure is distinguished from an unknown remote outcome. One MCP invocation can cause multiple paid model/internal-tool calls; their usage and cost are not measured by this client.

## Validation record

- **Prior Windows exercise:** v0.4.0 authenticated discovery, one explicit analysis submission, a saved reply aligned with the correct run/attempt IDs, and matching archived request/handoff hashes. This does not establish Windows Kumu generation.
- **Offline, synthetic:** 19 new tests cover ordered ID selection/exclusions, single/multiple focus, duplicate responses, missing second focus, wrong run/anchor, unsafe or conflicting output, cancellation, failed authentication/schema, redirects, lost responses/no retries, archive failures, source preservation, repeated explicit calls, JSON/SSE, explicit browser opening, CLI/menu routing and unattended behavior. All 144 offline tests passed (125 existing + 19 new) in 20.302 seconds. These tests use synthetic local HTTP/MCP servers and mocked browser opening; no real model was called.
- **Saved analysis inspection:** the previously saved analysis contains exactly two unique IDs, `AML.T0054` and `AML.T0051.000`. This is an extraction check from the uploaded response, not a new ATLAS invocation or independent mapping validation.
- **Pending:** first confirmed Windows Kumu call, returned tool-shaped result, archived link and operator visual confirmation that both focus nodes appear. Native Garak evidence for that real run was not present in the build environment; offline native-run fixtures are synthetic.

## Authoritative implementation inspected

The published [Graph Generator contract](https://github.com/mitre-atlas/atlas-knowledge-base-agent/blob/b2bca6438e99cb72752c27be1728f062b6f943ca/prompts/tool-contracts/ATLAS%20Graph%20Generator.md) and [v1.1.0 flow component](https://github.com/mitre-atlas/atlas-knowledge-base-agent/blob/b2bca6438e99cb72752c27be1728f062b6f943ca/flows/ATLAS%20Agent%20v1.1.0.json) were checked for input/output fields and URL generation. The component uses `focus=1` for one ID and an outbound-one-hop focus directive per ID for multiple IDs. Its syntax check alone does not verify dataset existence. This inspection does not prove the operator's installed component is byte-identical.
