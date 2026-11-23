# 0.4.0 — explicit ATLAS over MCP

Apply over the existing 0.3.2 installation. This patch adds `atlas_mcp.py`, the `atlas` command, and optional completion-menu action 4. Actions 1–3 and unattended scan/handoff behavior remain unchanged. No packages are installed or upgraded, and private configuration is not rewritten.

## Behavior and evidence

1. Select one existing native Garak run. The runner requires its report, manifest, summary, handoff and checksum index, verifies hashes and recomputed summary, and checks the handoff run ID.
2. Select the previously saved authenticated MCP discovery report. Only the explicitly selected loopback project endpoint and `atlas_agent_v110` are eligible. Tool names and routing are never taken from attack evidence or model output.
3. Supply the provider/model shown in the ATLAS flow. This records the operator's observation; it does not alter or independently inspect the flow. Review the entire saved handoff, destination and cost limitation, then type `SEND`. Enter/other text/Ctrl+C cancels. The API key is entered only in a hidden local prompt.
4. Reinitialize MCP, list tools, and require the server information and tool metadata/schema to match discovery. No ATLAS invocation occurs on an authentication, identity or schema failure.
5. Invoke the exact tool once with `input_value` containing the existing handoff and a fresh UUID `session_id`. No scan or regeneration occurs. Source hashes are rechecked after confirmation and before dispatch.
6. Save the reply as **UNREVIEWED**. All mappings remain candidates pending analyst review and authoritative-source verification. The client does not infer attack success from ATLAS prose.

Each explicit submission creates `atlas-submissions/<UTC>-<unique-id>/` under the selected run:

| File | Purpose |
| --- | --- |
| `handoff.submitted.md` | Exact original handoff bytes, including line endings |
| `request.json` | Full MCP tool request, arguments, conversation ID and request ID |
| `response.json` | Full returned MCP result when received |
| `atlas_response.md` | Returned text blocks, in order, marked unreviewed |
| `submission.json` | Run/submission identity, source hashes, destination/schema, operator-observed model, counts, status, timestamps, limitations and review disposition |
| `mcp-exchanges.json` | Requests, response objects, JSON/SSE response bodies, HTTP statuses and timestamps; no authentication headers |
| `checksums.json` | Checksums for this submission's files |

Known API-key and MCP-session reflections are redacted from returned metadata, response text and wire records; redaction is identified. HTTP error bodies are omitted explicitly to avoid credential persistence. Incomplete/invalid UTF-8 or oversized responses are not represented as complete. No original run file or previous submission is overwritten. The root run checksum index is deliberately not rewritten; the new archive has its own index.

`response_received_unreviewed` means a nonempty text response arrived, not that its analysis is correct. Tool `isError`, known Langflow flow-error text, empty replies, protocol errors, disconnects and interruptions are distinguished. A lost response is `execution_unknown`; a received response followed by an archive failure is `archive_incomplete_after_response`. No automatic retry follows either condition. A single MCP call may cause multiple model and internal tool calls, and disconnecting the client does not prove the agent stopped.

## Security and experimental limits

- The handoff cannot select another endpoint, tool, credential or additional input argument. Responses and tool descriptions are data, not executable instructions. No sampling, roots, elicitation, resource retrieval or command execution is offered by this client.
- The project/flow's internal authorization and the API key's privileges are not independently validated by this patch. Model/provider provenance is operator-supplied. Server-reported MCP version is retained as server metadata, not relabelled as the Langflow package version.
- Fresh conversation IDs reduce accidental reuse; actual server-side context isolation still requires live inspection. The client's restrictions do not establish broad confused-deputy resistance for the agent.
- Handoff excerpts are not a general secrets sanitizer. The operator reviews the exact outgoing content. Agent-side credentials and configuration remain in Langflow; the local MCP API key is not included in the prompt.
- Provider settings, cost, usage and internal agent traces are not independently captured through this MCP schema. Any returned data is retained, but the client does not manufacture missing telemetry.
- No automatic Kumu request, Chroma write, paid compatibility test, Garak scan or scan-setting change is introduced.

## Validation

- **Exercised on the operator's Windows lab:** authenticated MCP initialization and tool discovery; protocol `2025-03-26`, exact lowercase tool name, `input_value` and optional `session_id`; zero tool invocations. This is not a live send test or a negative authorization test.
- **Offline synthetic tests:** 105 existing tests plus 20 new MCP tests. A local fake HTTP server and dummy API key cover JSON/SSE, exact request/evidence preservation, fresh sessions/archives, authentication and schema failures, cancellation, credential reflection, redirect refusal, server-request rejection, error/empty replies, uncertain execution, archive failure, menu integration and unattended restrictions. No real model was called.
- **Pending:** the operator's first confirmed Windows `atlas` invocation, correct response archiving, independent analyst review and validation of the server-side context. Native evidence for that intended run was not available in the build environment, so test fixtures are synthetic, not a reproduction of its outputs.

Run offline tests from the source directory:

```powershell
& 'C:\AI-Lab\garak-env\Scripts\python.exe' -m unittest discover -s tests -v
```

The patch ZIP contains only changed/new source, matching tests and documentation, under a `garak-playbook` root. Extract it over the existing project's parent directory while the Garak runner is closed. Keep Langflow running for the MCP test. Existing PowerShell windows can remain open.

## Sources checked

- MCP 2025-03-26 [tools](https://modelcontextprotocol.io/specification/2025-03-26/server/tools) and [Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports).
- Langflow v1.10.2 [MCP flow invocation and returned text/error handling](https://github.com/langflow-ai/langflow/blob/v1.10.2/src/backend/base/langflow/api/v1/mcp_utils.py).
- The operator's saved live discovery report, used to establish the actual tool name/schema. Its endpoint/project identifiers are not embedded in this public source patch.
