# 0.4.2: bind Kumu validation to independent private configuration

**Historical version 0.4.2 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

Version 0.4.2 corrected a reproduced gap in 0.4.1: 0.4.1 accepted another Kumu project or map when the focus selectors matched. This patch requires an independently configured project and map before accepting a URL. No expected value is learned, written or updated from an agent response.

## Private configuration

Create `kumu.private.json` outside the public source directory. The default location is the sibling directory `garak-playbook-private/kumu.private.json`; both `kumu` and `kumu-validate` also accept `--kumu-config PATH`. Menu action 5 uses the default location.

```json
{
  "expected_project_id": "YOUR_KUMU_PROJECT_ID",
  "expected_map_name": "atlas"
}
```

Take these values from the intended **ATLAS Graph Generator configuration**, independently of any returned URL. A public example is supplied at `examples/kumu.config.example.json`; replace the project placeholder in a private copy. Use the project ID, not a URL, and the lowercase map slug. The runner reads this file without changing it. Missing/invalid configuration stops before any MCP call or key prompt. The file's path, hash, values and provenance are recorded; changes during execution stop acceptance.

The review screen displays the expected project/map and **selected IDs plus one-hop research context** before `GRAPH`. This retains the existing graph scope. A selected-nodes-only graph is not implemented by this correction. For multiple selected IDs, the same published outbound-one-hop focus shape is required.

## Acceptance and rejection

An accepted result must match all of the following: the configured HTTPS Kumu host, the independently configured project and map, the selected run ID, ordered focus IDs, anchor, focus mode and iframe source. New accepted submissions use status `graph_received_target_and_focus_checked`.

A wrong project, wrong map, missing ID or other failed check produces `graph_reply_not_validated`. The full returned response and rejection reason are retained. No accepted URL/iframe files or browser-opening offer are produced. Configuration and original run/ATLAS evidence remain unchanged. Existing v0.4.1 statuses are historical records and are not rewritten.

URL validation is distinct from visual confirmation and from actual internal tool execution. Matching a configured target does not establish that its knowledge graph is authoritative or current. Dataset verification and Graph Generator execution remain agent-reported through the MCP flow reply. A screenshot can show that nodes rendered, but cannot prove those internal calls happened. Mapping dispositions remain candidates until reviewed.

## Offline check of an existing graph

This command reads saved evidence and private configuration. It makes **zero network requests**, asks for no API key, and never opens a browser or reruns Garak. Langflow does not need to be restarted or running for this check.

In **Windows PowerShell**, substitute your existing paths:

```powershell
& 'C:\AI-Lab\garak-env\Scripts\python.exe' `
  'D:\AI-Lab\projects\garak-playbook\playbook.py' kumu-validate `
  --run-dir 'D:\AI-Lab\evaluations\existing-run' `
  --graph-dir 'D:\AI-Lab\evaluations\existing-run\kumu-submissions\existing-graph' `
  --kumu-config 'D:\AI-Lab\projects\garak-playbook-private\kumu.private.json'
```

It verifies checksums, links to the saved ATLAS source, selected IDs, prompt/request/session consistency, the original graph reply, and any saved derived URL/iframe. It applies the same target-and-focus validation as new graph requests. It creates a separate `kumu-validations/<UTC>-<unique-id>/validation.json` and checksum index with pass/fail status, evidence hashes, expected target, rejection reason if any, and unchanged-source checks. Original files, raw replies, old statuses and previous validation records stay intact. It does not contact the discovery endpoint or require the old discovery JSON for this offline check.

## Validation and remaining acceptance

**151 offline tests passed** (144 existing + 7 new) in 22.901 seconds. The new Kumu tests use synthetic responses and local fake MCP servers; browser opening is mocked. No live model call was made during this correction.

- Focused regression checks cover: correct project/map passes; different project, different map and missing second focus ID fail.
- Synthetic MCP tests check that wrong targets preserve raw responses and reasons without opening or accepted-link files, and do not update private configuration.
- Tests cover missing/malformed configuration, configuration changes after confirmation, offline validation of a synthetic v0.4.1 archive, offline rejection against a different configured target, preserved evidence and CLI routing without network, key input, browser or scan calls.
- The exact URL supplied in the operator's successful v0.4.1 terminal output passes the new target/focus check with independently specified expected values. Mutated project/map and missing-ID variants fail. **This is a URL check, not a check of the full native saved response.**
- The actual graph `response.json` and its native archive were not supplied to the build environment. The operator's local `kumu-validate` result is still required to complete acceptance against that existing saved response. No paid call is necessary.

No scan profiles, generation settings, concise ATLAS handoff, Graph Generator prompt, one-hop focus policy or API-key handling are changed by this correction.
