"""Explicit, single-invocation ATLAS handoff over the discovered local MCP endpoint.

Standard library only. No scan, prompt regeneration, model-selected routing,
server-request execution, resource fetching or automatic retry. The confirmed
analysis request includes a graph; kumu_mcp also reuses this transport explicitly.
Protocol: https://modelcontextprotocol.io/specification/2025-03-26/server/tools
"""
from __future__ import annotations

from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import warnings

PROTOCOL = "2025-03-26"
TOOL = "atlas_agent_v110"
VERSION = "0.4.2"
MAX_HANDOFF = 256 * 1024
MAX_RESPONSE = 8 * 1024 * 1024
SOURCE_FILES = ("atlas_handoff.md", "summary.json", "manifest.json", "scan.report.jsonl", "checksums.json")


class AtlasError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def read_json(path, limit=2 * 1024 * 1024):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise AtlasError("Configuration/summary exceeds the supported size: " + str(path))
    return json.loads(raw.decode("utf-8-sig"))


def clean(value, secrets):
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            # Include escaped representations in captured JSON/SSE wire text.
            for representation in {secret, json.dumps(secret)[1:-1], urllib.parse.quote(secret, safe="")}:
                value = value.replace(representation, "[REDACTED]")
        return value
    if isinstance(value, list):
        return [clean(item, secrets) for item in value]
    if isinstance(value, dict):
        return {clean(key, secrets): clean(item, secrets) for key, item in value.items()}
    return value


def terminal_text(value):
    """Show evidence without interpreting terminal controls or bidi formatting."""
    return "".join(char if char in "\n\t" or unicodedata.category(char) not in {"Cc", "Cf", "Cs"}
                   else "\\u%04x" % ord(char) for char in str(value))


def validate_endpoint(endpoint):
    try:
        parts = urllib.parse.urlsplit(endpoint)
        match = re.fullmatch(r"/api/v1/mcp/project/([0-9a-fA-F-]{36})/streamable/?", parts.path)
        if (parts.scheme != "http" or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
                or not parts.port or parts.username or parts.password or parts.query or parts.fragment or not match):
            raise ValueError()
        return str(uuid.UUID(match.group(1)))
    except (ValueError, TypeError, AttributeError):
        raise AtlasError("Use the discovered loopback HTTP project endpoint with an explicit port and no credentials/query.") from None


def select_tool(tools):
    if not isinstance(tools, list):
        raise AtlasError("MCP inventory is missing.")
    matches = [tool for tool in tools if isinstance(tool, dict) and tool.get("name") == TOOL]
    if len(matches) != 1:
        raise AtlasError("Expected exactly one tool named " + TOOL)
    tool = matches[0]
    schema = tool.get("inputSchema", {})
    if not isinstance(schema, dict):
        raise AtlasError("ATLAS input schema is not an object.")
    properties = schema.get("properties", {})
    if (schema.get("type") != "object" or not isinstance(properties, dict)
            or set(properties) != {"input_value", "session_id"}
            or any(not isinstance(properties[name], dict) or properties[name].get("type") != "string" for name in properties)
            or not set(schema.get("required", [])).issubset(properties)):
        raise AtlasError("The ATLAS input schema needs review before this client can call it.")
    return tool


def load_discovery(path):
    path = Path(path).expanduser().resolve(strict=True)
    data = read_json(path)
    project = validate_endpoint(data.get("endpoint"))
    if (data.get("status") != "discovery_complete" or data.get("tool_invocations") != 0
            or data.get("protocol_version") != PROTOCOL or data.get("transport") != "streamable_http"
            or data.get("authentication_mode") != "x-api-key" or data.get("authentication_sent") is not True):
        raise AtlasError("A completed API-key-authenticated discovery report is required.")
    if data.get("server_info", {}).get("name") != "langflow-mcp-project-" + project:
        raise AtlasError("Discovery server identity does not match the endpoint project.")
    tool = select_tool(data.get("tools"))
    return {"path": str(path), "sha256": file_hash(path), "endpoint": data["endpoint"],
            "project_id": project, "server_info": data["server_info"], "tool": tool,
            "schema_sha256": digest(canonical(tool["inputSchema"]).encode())}


def load_run(folder, analyze):
    folder = Path(folder).expanduser().resolve(strict=True)
    for name in SOURCE_FILES:
        path = folder / name
        if not path.is_file() or path.resolve().parent != folder:
            raise AtlasError("Required run evidence is missing or redirects outside the run: " + name)
    hashes = {name: file_hash(folder / name) for name in SOURCE_FILES}
    index = read_json(folder / "checksums.json", 8 * 1024 * 1024)
    if any(index.get(name) != hashes[name] for name in SOURCE_FILES if name != "checksums.json"):
        raise AtlasError("Saved source checksums differ; no handoff will be sent.")
    summary = read_json(folder / "summary.json")
    manifest = read_json(folder / "manifest.json")
    recomputed, _ = analyze(folder / "scan.report.jsonl", manifest)
    if summary != recomputed:
        raise AtlasError("Saved summary differs from native evidence; no handoff will be sent.")
    with (folder / "atlas_handoff.md").open("rb") as stream:
        raw = stream.read(MAX_HANDOFF + 1)
    if len(raw) > MAX_HANDOFF or not raw.strip():
        raise AtlasError("The saved handoff is empty or exceeds 256 KiB.")
    text = raw.decode("utf-8")  # Preserve CR/LF and all submitted characters.
    run_id = summary.get("garak_run_id")
    if not run_id or [line for line in text.splitlines() if line.startswith("Run ID:")] != ["Run ID: " + run_id]:
        raise AtlasError("The handoff does not identify the saved run exactly once.")
    if hashes != {name: file_hash(folder / name) for name in SOURCE_FILES}:
        raise AtlasError("Run evidence changed while reading; stopped.")
    return folder, raw, text, summary, hashes


def api_key_prompt():
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = getpass.getpass("Langflow API key (hidden; session only): ")
        except getpass.GetPassWarning:
            raise AtlasError("Hidden input is unavailable; use an interactive PowerShell terminal.") from None
    if not key or key in {"YOUR_API_KEY", "REDACTED"} or any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise AtlasError("Enter the actual API key without whitespace or control characters.")
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AtlasError("MCP redirect refused. No redirect destination was contacted.")


class Client:
    def __init__(self, connection, key, timeout):
        validate_endpoint(connection["endpoint"])
        self.connection, self.key, self.timeout = connection, key, timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.session = None
        self.secrets = {key}
        self.exchanges = []
        self.initialized = False
        self.call_attempted = False
        self.next_id = 1
        self.cleanup = None

    def message(self, method, params=None):
        if method not in {"initialize", "notifications/initialized", "tools/list", "tools/call"}:
            raise AtlasError("MCP method is outside this client's allowlist.")
        if method == "tools/call":
            if self.call_attempted or not self.initialized or params.get("name") != TOOL:
                raise AtlasError("Only one explicit ATLAS invocation is permitted.")
            if set(params.get("arguments", {})) != {"input_value", "session_id"}:
                raise AtlasError("Unexpected ATLAS arguments.")
            self.call_attempted = True
        request = {"jsonrpc": "2.0", "method": method}
        if method != "notifications/initialized":
            request["id"] = self.next_id
            self.next_id += 1
        if params is not None:
            request["params"] = params
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "x-api-key": self.key}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        if self.initialized:
            headers["MCP-Protocol-Version"] = PROTOCOL
        exchange = {"started_at": now(), "request": request}
        self.exchanges.append(exchange)
        req = urllib.request.Request(self.connection["endpoint"], method="POST", headers=headers,
                                     data=json.dumps(request, ensure_ascii=False).encode("utf-8"))
        deadline = time.monotonic() + self.timeout
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                exchange["http_status"] = response.status
                if method == "initialize":
                    self.session = response.headers.get("Mcp-Session-Id")
                    if self.session:
                        self.secrets.add(self.session)
                if method == "notifications/initialized":
                    if response.status != 202:
                        raise AtlasError("Initialization notification did not receive HTTP 202.")
                    return {}
                result = self.read_response(response, request["id"], exchange, deadline)
                exchange["response"] = result
                if "error" in result:
                    raise AtlasError("MCP returned a protocol error; the response is retained.")
                if not isinstance(result.get("result"), dict):
                    raise AtlasError("MCP response has no result object.")
                return result["result"]
        except urllib.error.HTTPError as error:
            exchange["http_status"] = error.code
            exchange["response_body_omitted_reason"] = "HTTP error body omitted to avoid persisting reflected authentication material."
            # Auth error bodies can contain credentials; retain status, not that body.
            error.close()
            raise AtlasError(f"MCP returned HTTP {error.code}; no automatic retry.") from None
        finally:
            exchange["ended_at"] = now()

    def read_response(self, response, expected_id, exchange, deadline):
        kind = response.headers.get_content_type()
        wire = bytearray()
        complete = False
        try:
            if kind == "application/json":
                wire.extend(response.read(MAX_RESPONSE + 1))
                if len(wire) > MAX_RESPONSE:
                    raise AtlasError("MCP response exceeded 8 MiB; coverage is incomplete.")
                message = json.loads(wire.decode("utf-8"))
            elif kind == "text/event-stream":
                data = []
                while True:
                    if time.monotonic() > deadline:
                        raise AtlasError("MCP response processing exceeded the configured time limit.")
                    line = response.readline(MAX_RESPONSE + 1)
                    wire.extend(line)
                    if len(wire) > MAX_RESPONSE:
                        raise AtlasError("MCP stream exceeded 8 MiB; coverage is incomplete.")
                    if not line:
                        raise AtlasError("MCP stream ended before a matching response.")
                    text = line.decode("utf-8").rstrip("\r\n")
                    if text.startswith("data:"):
                        data.append(text[5:].removeprefix(" "))
                    elif not text and data:
                        message = json.loads("\n".join(data))
                        data = []
                        if not isinstance(message, dict):
                            raise AtlasError("Unsupported MCP stream payload.")
                        if "method" in message:
                            if "id" in message:
                                raise AtlasError("Server-initiated requests are unsupported and were not executed.")
                            continue
                        break
            else:
                raise AtlasError("Expected an MCP JSON or SSE response.")
            if (not isinstance(message, dict) or message.get("jsonrpc") != "2.0"
                    or message.get("id") != expected_id or "method" in message):
                raise AtlasError("MCP response ID or version does not match.")
            complete = True
            return message
        finally:
            exchange["response_body_utf8"] = bytes(wire[:MAX_RESPONSE]).decode("utf-8", errors="replace")
            exchange["response_body_complete"] = complete

    def initialize_and_check(self):
        info = self.message("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                          "clientInfo": {"name": "garak-playbook-atlas-handoff", "version": VERSION}})
        if info.get("protocolVersion") != PROTOCOL or info.get("serverInfo") != self.connection["server_info"]:
            raise AtlasError("MCP server identity/version changed. Obtain a new discovery report before sending.")
        if "tools" not in info.get("capabilities", {}):
            raise AtlasError("MCP server does not advertise tools.")
        self.initialized = True
        self.message("notifications/initialized")
        rows, cursor, cursors = [], None, set()
        for _ in range(20):
            result = self.message("tools/list", {"cursor": cursor} if cursor else {})
            if not isinstance(result.get("tools"), list):
                raise AtlasError("MCP tools/list is incomplete.")
            rows.extend(result["tools"])
            cursor = result.get("nextCursor")
            if not cursor:
                tool = select_tool(rows)
                if tool != self.connection["tool"]:
                    raise AtlasError("ATLAS tool metadata/schema changed. Obtain a new discovery report before sending.")
                return
            if not isinstance(cursor, str) or cursor in cursors:
                raise AtlasError("MCP discovery pagination is incomplete.")
            cursors.add(cursor)
        raise AtlasError("MCP discovery exceeded 20 pages.")

    def close(self):
        if not self.session:
            return
        headers = {"x-api-key": self.key, "Mcp-Session-Id": self.session, "MCP-Protocol-Version": PROTOCOL}
        try:
            with self.opener.open(urllib.request.Request(self.connection["endpoint"], method="DELETE", headers=headers), timeout=5) as response:
                self.cleanup = {"http_status": response.status}
        except urllib.error.HTTPError as error:
            self.cleanup = {"http_status": error.code}
            error.close()
        except (Exception, KeyboardInterrupt) as error:
            self.cleanup = {"error_type": type(error).__name__}


def atomic_json(path, data):
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def markdown_comparison_text(text):
    """Ignore only extra blank lines inside simple pipe tables for comparison.

    Keep paragraph boundaries, nonblank whitespace, and code/HTML untouched.
    This is a deliberately narrow match for Langflow's two table renderings,
    not general Markdown normalization or a rewrite of the raw response.
    """
    lines = text.split("\n")
    if any(line.strip() and line.startswith((" ", "\t", "```", "~~~", "<")) for line in lines):
        return text
    output = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("|") and line.endswith("|"):
            rows, end, last_row = [], index, index
            while end < len(lines):
                candidate = lines[end]
                if candidate.startswith("|") and candidate.endswith("|"):
                    rows.append(candidate)
                    last_row = end
                elif candidate.strip():
                    break
                end += 1
            if len(rows) >= 2 and re.fullmatch(r"\|(?:[ \t]*:?-{3,}:?[ \t]*\|)+", rows[1]):
                output.extend(rows)
                index = last_row + 1
            else:
                output.extend(lines[index:end])
                index = end
            continue
        output.append(line)
        index += 1
    return "\n".join(output)


def markdown_text_blocks(texts):
    """Render equivalent whole blocks once without mutating the response."""
    unique, positions = [], {}
    for text in texts:
        key = markdown_comparison_text(text)
        if key not in positions:
            positions[key] = len(unique)
            unique.append(text)
        else:
            index = positions[key]
            # Prefer the existing compact table rendering, in first-seen order.
            if len(text) < len(unique[index]):
                unique[index] = text
    return "\n\n".join(unique), len(texts) - len(unique)


def describe_result(result, *, markdown=False):
    contents = result.get("content")
    if not isinstance(contents, list):
        return "response_without_analysis_text", "", ["Missing content list."]
    texts = [item["text"] for item in contents if isinstance(item, dict)
             and item.get("type") == "text" and isinstance(item.get("text"), str)]
    text, collapsed = markdown_text_blocks(texts) if markdown else ("\n\n".join(texts), 0)
    notes = []
    if collapsed:
        notes.append(f"Collapsed {collapsed} duplicate text block(s) in Markdown; all blocks retained in response.json.")
    if len(texts) != len(contents):
        notes.append("Non-text or invalid blocks are retained in response.json, not rendered or fetched.")
    # These prefixes are emitted by Langflow 1.10.2 even when isError is absent.
    reported_error = any(value.startswith("Flow build blocked:")
                         or re.match(r"Error Executing the .+ tool\. Error:", value) for value in texts)
    if result.get("isError") is True or reported_error:
        return "tool_error_returned", text, notes
    if not text.strip():
        return "response_without_analysis_text", text, notes
    return "response_received_unreviewed", text, notes


def send_saved_run(folder, *, analyze, discovery_path=None, provider=None, model=None, timeout=300,
                   kumu_config=None, include_graph=True):
    """Interactive command/menu action. Returns 0 received, 2 failure, 3 cancelled."""
    if not sys.stdin.isatty():
        raise AtlasError("ATLAS submission requires an interactive terminal and explicit SEND confirmation.")
    if type(timeout) is not int or not 30 <= timeout <= 1800:
        raise AtlasError("ATLAS timeout must be 30–1800 seconds.")
    folder, raw, text, summary, hashes = load_run(folder, analyze)
    import atlas_graph as graph
    target = graph.load_target(kumu_config) if include_graph else None
    prompt = graph.build_prompt(summary["garak_run_id"], text, target) if include_graph else text
    try:
        discovery_path = discovery_path or input("Full path to the completed MCP discovery JSON (Enter cancels): ").strip().strip('"')
        if not discovery_path:
            return 3
        connection = load_discovery(discovery_path)
        provider = provider or input("ATLAS model provider shown in Langflow (Enter cancels): ").strip()
        if not provider:
            return 3
        model = model or input("ATLAS model name shown in Langflow (Enter cancels): ").strip()
        if not model:
            return 3
        if any(len(value) > 200 or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value) for value in (provider, model)):
            raise AtlasError("Provider/model labels must be short names without control characters.")
        print("\nATLAS submission review")
        print("Run ID:", summary["garak_run_id"])
        print("Scan execution:", summary["execution_status"])
        print("Endpoint:", connection["endpoint"])
        print("Tool:", TOOL)
        print("ATLAS provider/model (operator supplied):", provider, "/", model)
        print("Handoff:", folder / "atlas_handoff.md")
        print("Handoff SHA-256:", hashes["atlas_handoff.md"])
        print("One MCP tool invocation. ATLAS may make multiple model/tool calls; upstream cost/usage is not measured.")
        if include_graph:
            print("SEND includes analysis, dataset verification and Graph Generator for every AML ID discussed.")
            print("Expected Kumu project/map:", target["expected_project_id"], "/", target["expected_map_name"])
            print("Destination source:", target["provenance"])
            print("The full returned URL is saved with the analysis; no separate GRAPH action or browser launch.")
        print("A fresh conversation ID will be used. ATLAS flow settings are not changed by this command.")
        print("Socket timeout/response processing limit (seconds):", timeout)
        print("\n----- Existing handoff (untrusted evidence; terminal controls escaped for display) -----")
        print(terminal_text(text))
        print("----- End of handoff -----")
        if input("Type SEND to submit this handoff to the displayed ATLAS provider, or Enter to cancel: ").strip() != "SEND":
            print("Cancelled. No MCP request was made.")
            return 3
        key = api_key_prompt()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. No MCP request was made.")
        return 3
    if key in prompt:
        raise AtlasError("The handoff contains the supplied credential; sending was blocked.")
    if hashes != {name: file_hash(folder / name) for name in SOURCE_FILES}:
        raise AtlasError("Run evidence changed after review; nothing was sent.")
    if connection["sha256"] != file_hash(Path(connection["path"])):
        raise AtlasError("Discovery evidence changed after review; nothing was sent.")
    if target is not None and not graph.target_unchanged(target):
        raise AtlasError("Expected Kumu destination changed after review; nothing was sent.")
    submission_id = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    parent = folder / "atlas-submissions"
    if parent.exists() and parent.resolve().parent != folder:
        raise AtlasError("ATLAS archive directory redirects outside the selected run.")
    archive = parent / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + submission_id[:8])
    archive.mkdir(parents=True, exist_ok=False)
    client = Client(connection, key, timeout)
    record = {"schema_version": 1, "runner_version": VERSION, "submission_id": submission_id,
              "created_at": now(), "run_id": summary["garak_run_id"], "run_folder": str(folder),
              "source_files_sha256": hashes, "scan_execution_status": summary["execution_status"],
              "scan_detectors": summary["detectors"], "connection": connection,
              "agent_provider": provider, "agent_model": model, "model_provenance": "operator_supplied_flow_configuration",
              "authentication": {"mode": "x-api-key", "principal_id": "not_exposed_by_MCP_discovery",
                                 "credential_permissions": "not_independently_verified"},
              "effective_model_settings": "not_independently_captured", "upstream_usage_and_cost": "not_measured",
              "conversation_id": conversation_id, "new_conversation_requested": True,
              "status": "prepared", "review_status": "unreviewed", "mapping_verification_status": "candidate_pending_review",
              "tool_call_dispatch_attempts": 0, "automatic_retries": 0, "timeout_seconds": timeout,
              "scan_outcome_changed": False, "confirmed_by_operator_at": now()}
    if include_graph:
        record.update(request_format=graph.REQUEST_FORMAT, expected_kumu_target=target,
                      request_prompt_sha256=digest(prompt.encode("utf-8")))
    result = None
    try:
        # All source files remain read-only. Verify archive writes before any remote call.
        (archive / "handoff.submitted.md").write_bytes(raw)
        if include_graph:
            (archive / "request_prompt.md").write_bytes(prompt.encode("utf-8"))
        atomic_json(archive / "submission.json", clean(record, client.secrets))
        print("Checking the authenticated endpoint and tool schema...")
        client.initialize_and_check()
        if hashes != {name: file_hash(folder / name) for name in SOURCE_FILES}:
            raise AtlasError("Run evidence changed before dispatch; handoff was not sent.")
        if target is not None and not graph.target_unchanged(target):
            raise AtlasError("Expected Kumu destination changed before dispatch; nothing was sent.")
        arguments = {"input_value": prompt, "session_id": conversation_id}
        request = {"jsonrpc": "2.0", "id": client.next_id, "method": "tools/call",
                   "params": {"name": TOOL, "arguments": arguments}}
        atomic_json(archive / "request.json", request)
        record.update(status="dispatch_started", tool_call_dispatch_attempts=1, dispatched_at=now())
        atomic_json(archive / "submission.json", clean(record, client.secrets))
        print("Sending the saved handoff to ATLAS. Waiting for its reply...")
        result = client.message("tools/call", request["params"])
        safe_result = clean(result, client.secrets)
        atomic_json(archive / "response.json", safe_result)
        record["credential_redaction_applied_to_response"] = safe_result != result
        if include_graph:
            record["status"], response_text, record["response_notes"], record["graph"] = graph.describe_response(
                safe_result, summary["garak_run_id"], target)
            response_text += graph.render_graph(record["graph"])
        else:
            record["status"], response_text, record["response_notes"] = describe_result(safe_result, markdown=True)
        (archive / "atlas_response.md").write_text(
            "# ATLAS analysis — UNREVIEWED\n\nRun ID: " + summary["garak_run_id"]
            + "\n\nProposed mappings are candidates pending analyst review and official-source verification."
            + "\n\n" + response_text + "\n", encoding="utf-8", newline="")
    except (Exception, KeyboardInterrupt) as error:
        record["status"] = ("archive_incomplete_after_response" if result is not None else
                            "execution_unknown" if client.call_attempted else "failed_before_tool_call")
        record["error"] = clean(type(error).__name__ + ": " + str(error), client.secrets)
        if client.call_attempted and result is None:
            record["uncertainty"] = "The server may have executed or may still be running. Do not infer cancellation or retry automatically."
    finally:
        client.close()
        record["ended_at"] = now()
        record["session_cleanup"] = client.cleanup
        try:
            record["source_files_unchanged"] = all((folder / name).is_file() and file_hash(folder / name) == value
                                                   for name, value in hashes.items())
        except OSError:
            record["source_files_unchanged"] = None
            record["source_verification_error"] = "Could not read all original evidence after submission."
        record["recorded_tool_call_attempts"] = sum(item["request"]["method"] == "tools/call" for item in client.exchanges)
        try:
            atomic_json(archive / "mcp-exchanges.json", clean(client.exchanges, client.secrets))
            atomic_json(archive / "submission.json", clean(record, client.secrets))
            atomic_json(archive / "checksums.json", {p.name: file_hash(p) for p in archive.iterdir()
                                                     if p.is_file() and p.name != "checksums.json"})
        except OSError:
            print("ERROR: ATLAS evidence could not be fully saved. Remote execution may have occurred.")
            print("ATLAS archive:", clean(str(archive), client.secrets))
            return 2
    print("ATLAS status:", record["status"])
    print("ATLAS archive:", clean(str(archive), client.secrets))
    if record.get("error"):
        print("ERROR:", terminal_text(record["error"]))
    if record.get("uncertainty"):
        print(record["uncertainty"])
    if (archive / "atlas_response.md").is_file():
        print("Unreviewed ATLAS reply:", archive / "atlas_response.md")
    if record.get("graph"):
        print("Kumu status:", record["graph"]["status"])
        if record["graph"].get("error"):
            print("Kumu error:", terminal_text(record["graph"]["error"]))
        else:
            print("Kumu URL:", record["graph"]["url"])
    print("Recorded Garak scan outcome is unchanged.")
    graph_ok = not include_graph or record.get("graph", {}).get("status") == "graph_received_target_and_coverage_checked"
    return 0 if record["status"] == "response_received_unreviewed" and record["source_files_unchanged"] and graph_ok else 2
