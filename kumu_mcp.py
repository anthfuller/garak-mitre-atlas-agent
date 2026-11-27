"""Explicit graph follow-up for one saved ATLAS submission. Standard library only.

The runner selects IDs from saved analysis; ATLAS verifies IDs and returns its
Graph Generator result. URLs are checked, never constructed or repaired here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.parse
import uuid
import webbrowser

import atlas_mcp as m

VERSION = "0.4.2"
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "garak-playbook-private" / "kumu.private.json"
GRAPH_SCOPE = "selected IDs plus one-hop research context"
ID = r"AML\.(?:TA\d{4}|T\d{4}(?:\.\d{3})?|M\d{4}|CS\d{4})"
ID_RE = re.compile(r"(?<![\w.])" + ID + r"(?!\w|\.\w)")
ARCHIVE_FILES = ("submission.json", "request.json", "response.json", "atlas_response.md",
                 "handoff.submitted.md", "mcp-exchanges.json", "checksums.json")


def load_target_config(path=None):
    """Read operator configuration only; never derive expectations from a reply."""
    path = Path(path or DEFAULT_CONFIG).expanduser().resolve()
    if not path.is_file():
        raise m.AtlasError("Kumu private configuration is required: " + str(path)
                           + ". Set expected_project_id and expected_map_name from your Graph Generator configuration.")
    before = m.file_hash(path)
    data = m.read_json(path, 16384)
    if not isinstance(data, dict) or set(data) != {"expected_project_id", "expected_map_name"}:
        raise m.AtlasError("Kumu config must contain only expected_project_id and expected_map_name.")
    if (not isinstance(data["expected_project_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", data["expected_project_id"])
            or not isinstance(data["expected_map_name"], str)
            or not re.fullmatch(r"[a-z0-9_.~-]{1,200}", data["expected_map_name"])):
        raise m.AtlasError("Use a Kumu project ID and lowercase map slug, not a URL, in the private configuration.")
    if m.file_hash(path) != before:
        raise m.AtlasError("Kumu configuration changed while reading.")
    return {**data, "path": str(path), "sha256": before, "provenance": "operator_private_configuration"}


def source_hashes(folder, names):
    hashes = {}
    for name in names:
        path = folder / name
        if not path.is_file() or path.resolve().parent != folder:
            raise m.AtlasError("Missing or redirected source evidence: " + name)
        hashes[name] = m.file_hash(path)
    return hashes


def choose_submission(run, supplied=None):
    parent = run / "atlas-submissions"
    if supplied:
        chosen = Path(supplied).expanduser().resolve(strict=True)
    else:
        if not parent.is_dir() or parent.resolve().parent != run:
            raise m.AtlasError("This run has no local ATLAS submissions. Send its handoff to ATLAS first.")
        choices = sorted(p for p in parent.iterdir() if p.is_dir() and (p / "submission.json").is_file())
        if not choices:
            raise m.AtlasError("No saved ATLAS submission is available for this run.")
        if len(choices) == 1:
            chosen = choices[0].resolve()
        else:
            print("\nSelect the saved ATLAS analysis for this run:")
            for i, path in enumerate(choices, 1):
                print(f"[{i}] {m.terminal_text(path.name)}")
            answer = input("Selection (Enter/B cancels): ").strip()
            if not answer or answer.upper() == "B":
                return None
            if not answer.isdecimal() or not 1 <= int(answer) <= len(choices):
                raise m.AtlasError("Invalid ATLAS submission selection; nothing sent.")
            chosen = choices[int(answer) - 1].resolve()
    if (not parent.is_dir() or parent.resolve() != parent or chosen.parent != parent
            or not chosen.is_dir()):
        raise m.AtlasError("Select a submission directly under this run's atlas-submissions folder.")
    return chosen


def load_submission(folder, run_summary, run_hashes):
    hashes = source_hashes(folder, ARCHIVE_FILES)
    index = m.read_json(folder / "checksums.json")
    if not isinstance(index, dict) or any(index.get(n) != h for n, h in hashes.items() if n != "checksums.json"):
        raise m.AtlasError("ATLAS archive checksums differ; stopped before any request.")
    record = m.read_json(folder / "submission.json")
    request = m.read_json(folder / "request.json")
    response = m.read_json(folder / "response.json", 64 * 1024 * 1024)
    if (record.get("status") != "response_received_unreviewed"
            or record.get("run_id") != run_summary["garak_run_id"]
            or record.get("source_files_unchanged") is not True):
        raise m.AtlasError("The selected ATLAS analysis is incomplete or belongs to another run.")
    for name in ("summary.json", "manifest.json", "scan.report.jsonl"):
        if record.get("source_files_sha256", {}).get(name) != run_hashes[name]:
            raise m.AtlasError("The selected ATLAS analysis does not match this run's original evidence.")
    args = request.get("params", {}).get("arguments", {})
    if (request.get("jsonrpc") != "2.0" or request.get("method") != "tools/call"
            or request.get("params", {}).get("name") != m.TOOL
            or set(args) != {"input_value", "session_id"}
            or args.get("session_id") != record.get("conversation_id")
            or not isinstance(args.get("input_value"), str)):
        raise m.AtlasError("The saved ATLAS request is inconsistent with its submission record.")
    handoff = (folder / "handoff.submitted.md").read_bytes()
    if m.digest(handoff) != record.get("source_files_sha256", {}).get("atlas_handoff.md"):
        raise m.AtlasError("The saved ATLAS input does not match its original handoff hash.")
    if record.get("request_format"):
        import atlas_graph as graph
        if record["request_format"] != graph.REQUEST_FORMAT:
            raise m.AtlasError("Unknown ATLAS request format.")
        prompt_hashes = source_hashes(folder, ("request_prompt.md",))
        prompt = (folder / "request_prompt.md").read_bytes()
        expected = graph.build_prompt(run_summary["garak_run_id"], handoff.decode("utf-8"), record["expected_kumu_target"])
        if (prompt_hashes["request_prompt.md"] != index.get("request_prompt.md")
                or m.digest(prompt) != record.get("request_prompt_sha256")
                or prompt != args["input_value"].encode("utf-8") or prompt != expected.encode("utf-8")):
            raise m.AtlasError("Saved analysis/graph request differs from its preserved prompt and handoff.")
        hashes.update(prompt_hashes)
        status, text, _, _, _ = graph.extract_analysis(response)
    else:
        if handoff != args["input_value"].encode("utf-8"):
            raise m.AtlasError("The saved ATLAS input does not match its original handoff hash.")
        status, text, _ = m.describe_result(response)
    if status != "response_received_unreviewed":
        raise m.AtlasError("No usable ATLAS analysis is present in the selected submission.")
    if source_hashes(folder, tuple(hashes)) != hashes:
        raise m.AtlasError("ATLAS evidence changed while reading.")
    return record, text, hashes


def mentioned_ids(text):
    """Syntax-based inventory only; operator must exclude rejected/background IDs."""
    ids = list(dict.fromkeys(ID_RE.findall(text)))
    if len(ids) > 200:
        raise m.AtlasError("More than 200 unique IDs were mentioned; review this analysis separately.")
    rows = text.splitlines()
    contexts = {}
    for value in ids:
        snippets = []
        for i, line in enumerate(rows):
            if value not in ID_RE.findall(line):
                continue
            # Show qualification/rationale beside each occurrence, not just the ID.
            excerpt = " ".join(x.strip() for x in rows[max(0, i - 1):i + 4] if x.strip())
            if excerpt not in snippets:
                snippets.append(excerpt)
        contexts[value] = snippets
    return ids, contexts


def choose_ids(text, source):
    ids, contexts = mentioned_ids(text)
    if not ids:
        print("No canonical AML IDs appear in this analysis. No graph request will be made.")
        return []
    print("\nIDs mentioned in this saved ATLAS analysis (not automatically accepted mappings):")
    print("Analysis:", source / "atlas_response.md")
    for i, value in enumerate(ids, 1):
        print(f"\n[{i}] {value}")
        for snippet in contexts[value][:3]:
            print("  " + m.terminal_text(snippet[:650]) + (" [cut]" if len(snippet) > 650 else ""))
        if len(contexts[value]) > 3:
            print(f"  {len(contexts[value]) - 3} additional contexts in the saved analysis.")
    print("Select only IDs proposed as mappings for this run; exclude rejected mappings and background examples.")
    answer = input("Numbers in anchor-first order (e.g. 1,2), A for all shown, Enter/B to cancel: ").strip()
    if not answer or answer.upper() == "B":
        return []
    if answer.upper() == "A":
        selected = ids
    else:
        parts = [part.strip() for part in answer.split(",")]
        if any(not part.isdecimal() or not 1 <= int(part) <= len(ids) for part in parts):
            raise m.AtlasError("Invalid ID selection; no request was made.")
        selected = list(dict.fromkeys(ids[int(part) - 1] for part in parts))
    if len(selected) > 50:
        raise m.AtlasError("Select at most 50 focus IDs; no request was made.")
    return selected


def build_graph_prompt(run_id, ids):
    # The saved analysis and attack excerpts are deliberately not replayed.
    payload = json.dumps({"run_id": run_id, "ids": ids}, ensure_ascii=True)
    return (
        "Generate a focused Kumu graph for the following Garak run and operator-selected candidate mappings.\n"
        "Scope data: " + payload + "\n"
        "The ids list is complete and ordered; the first ID is the anchor. Do not use earlier conversation history. "
        "Do not reassess the scan, add IDs, omit IDs, or reinterpret these candidates as confirmed findings.\n"
        "Verify that EVERY requested ID exists using ATLAS Dataset Sandbox. If any cannot be verified, return "
        "an error and do not generate a partial graph. After verification, call ATLAS Graph Generator with "
        "exactly the ordered ids list. Use its configured Kumu project/map and its normal focus behavior. "
        "Do not construct, shorten, repair or rewrite the returned URL or iframe. Neighboring nodes are context, "
        "not additional mappings for this run.\n"
        "Return only one JSON object, with keys run_id, verified_ids, graph_result. "
        "run_id must equal the supplied run_id; verified_ids must list the IDs you verified in the same order. "
        "graph_result must be the complete unmodified Graph Generator result (status, ids, anchor, focus_mode, "
        "duplicates_removed, invalid_ids, url, iframe). If verification or the tool fails, use "
        'graph_result={"status":"error","url":"","iframe":"","error":{"message":"reason"}}. '
        "Do not invent a successful tool result or claim verification if the tools were unavailable.\n"
    )


def parse_envelope(response):
    if response.get("isError"):
        raise m.AtlasError("ATLAS reported a tool error.")
    blocks = response.get("content")
    if not isinstance(blocks, list) or not blocks:
        raise m.AtlasError("ATLAS returned no graph result.")
    objects = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "text" or not isinstance(block.get("text"), str):
            raise m.AtlasError("Unexpected non-text graph response; retained without execution.")
        text = block["text"].strip()
        if text.startswith("```"):
            match = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, re.S)
            if not match:
                raise m.AtlasError("Graph reply is not a complete JSON object.")
            text = match.group(1)
        try:
            obj = json.loads(text)
            m.canonical(obj)  # Reject non-finite JSON numbers.
        except (ValueError, TypeError):
            raise m.AtlasError("ATLAS did not return the requested graph JSON. Raw reply is preserved; no automatic retry.") from None
        if not isinstance(obj, dict):
            raise m.AtlasError("Graph reply is not a JSON object.")
        if obj not in objects:
            objects.append(obj)
    if len(objects) != 1:
        raise m.AtlasError("ATLAS returned conflicting graph results; none selected automatically.")
    return objects[0], len(blocks) - 1


def check_url(url, ids, *, target):
    """Bind to independently configured project/map, then verify focus/anchor."""
    if (not isinstance(url, str) or not url or len(url) > 8000
            or any(ord(c) < 33 or ord(c) > 126 for c in url) or "\\" in url):
        raise m.AtlasError("Kumu URL is empty, oversized or contains unencoded characters.")
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "embed.kumu.io"
            or not re.fullmatch(r"/[A-Za-z0-9_-]+", parts.path) or parts.query):
        raise m.AtlasError("Unexpected Kumu host, project path or URL parameters.")
    if parts.path[1:] != target["expected_project_id"]:
        raise m.AtlasError("Returned Kumu project differs from the independently configured expected project.")
    fragment_path, separator, query = parts.fragment.partition("?")
    path = fragment_path.split("/")
    slugs = [value.lower().replace(".", "-") for value in ids]
    if not separator or len(path) != 2 or not path[0] or path[1] != slugs[0]:
        raise m.AtlasError("Kumu anchor does not match the first selected ID.")
    if path[0] != target["expected_map_name"]:
        raise m.AtlasError("Returned Kumu map differs from the independently configured expected map.")
    params = urllib.parse.parse_qs(query, keep_blank_values=True)
    if set(params) != {"focus"} or len(params["focus"]) != 1:
        raise m.AtlasError("Kumu URL has missing or ambiguous focus parameters.")
    focus = params["focus"][0]
    expected = "1" if len(ids) == 1 else ", ".join("#" + slug + " out 1" for slug in slugs)
    if focus != expected:
        raise m.AtlasError("Kumu focus does not contain exactly all selected IDs in order with the documented focus depth.")
    return {"project": parts.path[1:], "map": urllib.parse.unquote(path[0]),
            "anchor": ids[0], "focus_ids": ids, "focus": focus}


class IframeCheck(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.starts, self.ends, self.unexpected = [], [], False

    def handle_starttag(self, tag, attrs):
        self.starts.append((tag, attrs))

    def handle_endtag(self, tag):
        self.ends.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.unexpected = True

    def handle_data(self, data):
        if data.strip():
            self.unexpected = True

    def handle_comment(self, data):
        self.unexpected = True

    def handle_decl(self, decl):
        self.unexpected = True

    def handle_pi(self, data):
        self.unexpected = True


def check_iframe(iframe, url):
    if not isinstance(iframe, str) or not iframe or len(iframe) > 16000:
        raise m.AtlasError("Graph tool iframe is missing or oversized.")
    parser = IframeCheck()
    parser.feed(iframe)
    parser.close()
    allowed = {"src", "width", "height", "frameborder", "loading", "referrerpolicy", "title"}
    if parser.unexpected or len(parser.starts) != 1 or parser.ends != ["iframe"]:
        raise m.AtlasError("Unexpected iframe markup; preserved only in the raw reply.")
    tag, pairs = parser.starts[0]
    attrs = dict(pairs)
    if tag != "iframe" or len(attrs) != len(pairs) or not set(attrs).issubset(allowed) or attrs.get("src") != url:
        raise m.AtlasError("Iframe source/attributes do not match the returned Kumu URL.")


def validate_graph(response, run_id, ids, *, target):
    obj, duplicate_blocks = parse_envelope(response)
    if obj.get("run_id") != run_id:
        raise m.AtlasError("Graph reply belongs to another run.")
    graph = obj.get("graph_result")
    if not isinstance(graph, dict) or graph.get("status") != "success":
        raise m.AtlasError("ATLAS did not report successful graph generation. See the saved response.")
    if (obj.get("verified_ids") != ids or graph.get("ids") != ids or graph.get("anchor") != ids[0]
            or graph.get("invalid_ids") != [] or graph.get("duplicates_removed") != []):
        raise m.AtlasError("Returned/verified IDs or anchor differ from the approved selection.")
    mode = "single_anchor" if len(ids) == 1 else "multi_anchor_outbound_one_hop"
    if graph.get("focus_mode") != mode:
        raise m.AtlasError("Returned graph focus mode differs from the requested selection.")
    inspected = check_url(graph.get("url"), ids, target=target)
    check_iframe(graph.get("iframe"), graph["url"])
    return obj, {"url_focus_check": inspected, "duplicate_response_blocks": duplicate_blocks,
                 "target_binding": "matched_independent_private_configuration",
                 "expected_target": target,
                 "dataset_verification": "reported_by_ATLAS_agent_not_independently_traced",
                 "graph_tool_execution": "reported_by_ATLAS_agent_not_independently_traced",
                 "browser_rendering": "not_verified", "mapping_status": "candidate_pending_analyst_review"}


def offer_open(url):
    try:
        answer = input("\n[1] Open Kumu view and return to PowerShell\n[2] Return to PowerShell\nSelection (Enter to return): ").strip()
        if answer == "1":
            if not webbrowser.open(url, new=2):
                print("Browser did not report accepting the URL. Copy the printed URL to your browser.")
            else:
                print("Browser launch requested. Rendering still requires visual review.")
    except (Exception, KeyboardInterrupt):
        print("Browser action cancelled or failed; saved graph and scan outcome are unchanged.")


def generate(run_folder, *, analyze, submission=None, discovery_path=None, timeout=300, config_path=None):
    if not sys.stdin.isatty():
        raise m.AtlasError("Kumu generation requires interactive ID review and explicit GRAPH confirmation.")
    if type(timeout) is not int or not 30 <= timeout <= 1800:
        raise m.AtlasError("Kumu timeout must be 30–1800 seconds.")
    target = load_target_config(config_path)
    run, _, _, summary, run_hashes = m.load_run(run_folder, analyze)
    try:
        source = choose_submission(run, submission)
        if source is None:
            return 3
        saved, text, hashes = load_submission(source, summary, run_hashes)
        ids = choose_ids(text, source)
        if not ids:
            print("No Kumu request made.")
            return 3
        connection = m.load_discovery(discovery_path or saved["connection"]["path"])
        if connection["project_id"] != saved["connection"]["project_id"]:
            raise m.AtlasError("Select discovery for the same ATLAS project that produced this analysis.")
        prompt = build_graph_prompt(summary["garak_run_id"], ids)
        print("\nKumu request review")
        print("Run ID:", summary["garak_run_id"])
        print("Source submission:", source)
        print("Focus IDs (anchor first):", ", ".join(ids))
        print("Graph scope:", GRAPH_SCOPE)
        print("Expected Kumu project/map:", target["expected_project_id"], "/", target["expected_map_name"])
        print("Expected-target configuration:", target["path"])
        print("Endpoint:", connection["endpoint"], "\nTool:", m.TOOL)
        print("Last recorded ATLAS provider/model:", m.terminal_text(saved.get("agent_provider", "unknown")),
              "/", m.terminal_text(saved.get("agent_model", "unknown")))
        print("Provider/model are from the prior submission, not freshly inspected. Flow settings remain unchanged.")
        print("One additional ATLAS MCP call can cause multiple paid model/tool calls; cost is not measured.")
        print("The prompt below sends only the run ID and approved IDs. Mappings remain candidates.")
        print("\n" + m.terminal_text(prompt))
        if input("Type GRAPH to request this view, or Enter to cancel: ").strip() != "GRAPH":
            print("Cancelled. No MCP request was made.")
            return 3
        key = m.api_key_prompt()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled. No MCP request was made.")
        return 3
    if key in prompt:
        raise m.AtlasError("Credential found in graph prompt; blocked.")

    def unchanged():
        return (source_hashes(run, m.SOURCE_FILES) == run_hashes
                and source_hashes(source, tuple(hashes)) == hashes
                and m.file_hash(Path(connection["path"])) == connection["sha256"]
                and m.file_hash(Path(target["path"])) == target["sha256"])

    if not unchanged():
        raise m.AtlasError("Source/discovery evidence changed after review; nothing sent.")
    parent = run / "kumu-submissions"
    if parent.exists() and parent.resolve() != parent:
        raise m.AtlasError("Kumu archive directory redirects outside the run.")
    graph_id, conversation = str(uuid.uuid4()), str(uuid.uuid4())
    archive = parent / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + graph_id[:8])
    archive.mkdir(parents=True, exist_ok=False)
    client = m.Client(connection, key, timeout)
    record = {"schema_version": 1, "runner_version": VERSION, "action": "kumu", "graph_submission_id": graph_id,
              "created_at": m.now(), "run_id": summary["garak_run_id"], "source_submission": str(source),
              "source_submission_id": saved["submission_id"], "source_files_sha256": hashes,
              "expected_target": target, "graph_scope": GRAPH_SCOPE,
              "run_files_sha256": run_hashes, "connection": connection, "selected_ids": ids, "anchor": ids[0],
              "selection_method": "operator_selected_from_ID_mentions_in_saved_analysis",
              "agent_provider": saved.get("agent_provider"), "agent_model": saved.get("agent_model"),
              "model_provenance": "previous_submission_operator_observation_not_rechecked",
              "upstream_usage_and_cost": "not_measured", "conversation_id": conversation,
              "new_conversation_requested": True, "status": "prepared", "automatic_retries": 0,
              "tool_call_dispatch_attempts": 0, "confirmed_by_operator_at": m.now(), "timeout_seconds": timeout,
              "review_status": "unreviewed", "mapping_status": "candidate_pending_analyst_review"}
    result, graph = None, None
    try:
        (archive / "graph_prompt.md").write_bytes(prompt.encode("utf-8"))
        m.atomic_json(archive / "submission.json", m.clean(record, client.secrets))
        print("Checking the authenticated endpoint and tool schema...")
        client.initialize_and_check()
        if not unchanged():
            raise m.AtlasError("Evidence changed before dispatch; graph request was not sent.")
        request = {"jsonrpc": "2.0", "id": client.next_id, "method": "tools/call",
                   "params": {"name": m.TOOL, "arguments": {"input_value": prompt, "session_id": conversation}}}
        m.atomic_json(archive / "request.json", request)
        record.update(status="dispatch_started", dispatched_at=m.now(), tool_call_dispatch_attempts=1)
        m.atomic_json(archive / "submission.json", m.clean(record, client.secrets))
        print("Requesting the Kumu view from ATLAS. Waiting for its reply...")
        result = client.message("tools/call", request["params"])
        safe = m.clean(result, client.secrets)
        m.atomic_json(archive / "response.json", safe)
        record["credential_redaction_applied_to_response"] = safe != result
        try:
            if not unchanged():
                raise m.AtlasError("Evidence or expected-target configuration changed while waiting; graph was not accepted.")
            obj, record["validation"] = validate_graph(safe, summary["garak_run_id"], ids, target=target)
        except (m.AtlasError, ValueError, TypeError) as error:
            record.update(status="graph_reply_not_validated", validation_error=m.clean(str(error), client.secrets))
        else:
            graph = obj["graph_result"]
            m.atomic_json(archive / "kumu_result.json", obj)
            (archive / "kumu_url.txt").write_bytes(graph["url"].encode("utf-8"))
            (archive / "kumu_iframe.txt").write_bytes(graph["iframe"].encode("utf-8"))
            record["status"] = "graph_received_target_and_focus_checked"
    except (Exception, KeyboardInterrupt) as error:
        record["status"] = ("archive_incomplete_after_response" if result is not None else
                            "execution_unknown" if client.call_attempted else "failed_before_tool_call")
        record["error"] = m.clean(type(error).__name__ + ": " + str(error), client.secrets)
        if client.call_attempted and result is None:
            record["uncertainty"] = "ATLAS may have executed or may still be running. No automatic retry was made."
    finally:
        client.close()
        record["ended_at"], record["session_cleanup"] = m.now(), client.cleanup
        try:
            record["source_files_unchanged"] = unchanged()
        except (OSError, m.AtlasError):
            record["source_files_unchanged"] = None
        record["recorded_tool_call_attempts"] = sum(x["request"]["method"] == "tools/call" for x in client.exchanges)
        try:
            m.atomic_json(archive / "mcp-exchanges.json", m.clean(client.exchanges, client.secrets))
            m.atomic_json(archive / "submission.json", m.clean(record, client.secrets))
            m.atomic_json(archive / "checksums.json", {p.name: m.file_hash(p) for p in archive.iterdir()
                                                      if p.is_file() and p.name != "checksums.json"})
        except OSError:
            print("ERROR: Kumu archive could not be fully saved. Remote execution may have occurred.")
            print("Kumu archive:", archive)
            return 2
    print("Kumu status:", record["status"])
    print("Kumu archive:", archive)
    for field in ("validation_error", "error", "uncertainty"):
        if record.get(field):
            print(m.terminal_text(record[field]))
    if record["status"] != "graph_received_target_and_focus_checked" or record["source_files_unchanged"] is not True:
        print("Graph was not accepted for opening. Original scan and ATLAS analysis were not rewritten.")
        return 2
    print("Focus IDs:", ", ".join(ids))
    print("Kumu URL:", graph["url"])
    print("URL file:", archive / "kumu_url.txt", "\nIframe file:", archive / "kumu_iframe.txt")
    print("Expected project/map and all selected focus IDs match. Dataset/tool verification is agent-reported; rendering is unverified.")
    offer_open(graph["url"])
    return 0


def validate_saved(run_folder, graph_folder, *, analyze, config_path=None):
    """Recheck a saved reply offline. Preserve its original status and all files."""
    target = load_target_config(config_path)
    run, _, _, summary, run_hashes = m.load_run(run_folder, analyze)
    graph_folder = Path(graph_folder).expanduser().resolve(strict=True)
    parent = run / "kumu-submissions"
    if parent.resolve() != parent or graph_folder.parent != parent or not graph_folder.is_dir():
        raise m.AtlasError("Select a graph archive directly under this run's kumu-submissions folder.")
    names = ["submission.json", "request.json", "response.json", "graph_prompt.md", "mcp-exchanges.json", "checksums.json"]
    names += [name for name in ("kumu_result.json", "kumu_url.txt", "kumu_iframe.txt") if (graph_folder / name).exists()]
    hashes = source_hashes(graph_folder, names)
    report = {"schema_version": 1, "runner_version": VERSION, "action": "offline_kumu_validation",
              "checked_at": m.now(), "run_id": summary["garak_run_id"], "graph_archive": str(graph_folder),
              "graph_files_sha256": hashes, "run_files_sha256": run_hashes, "expected_target": target,
              "graph_scope": GRAPH_SCOPE, "network_requests": 0, "original_graph_status_changed": False}
    saved_analysis, analysis_hashes = None, None
    try:
        index = m.read_json(graph_folder / "checksums.json")
        if not isinstance(index, dict) or any(index.get(n) != h for n, h in hashes.items() if n != "checksums.json"):
            raise m.AtlasError("Saved graph checksum verification failed.")
        record = m.read_json(graph_folder / "submission.json")
        report["original_graph_status"] = record.get("status")
        if record.get("action") != "kumu" or record.get("run_id") != summary["garak_run_id"]:
            raise m.AtlasError("Saved graph record is not bound to this Garak run.")
        ids = record.get("selected_ids")
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 50
                or any(not isinstance(x, str) or not re.fullmatch(ID, x) for x in ids)
                or len(set(ids)) != len(ids)):
            raise m.AtlasError("Saved selected IDs are missing, invalid or duplicated.")
        report["selected_ids"] = ids
        saved_analysis = choose_submission(run, record["source_submission"])
        saved, analysis, analysis_hashes = load_submission(saved_analysis, summary, run_hashes)
        if (record.get("source_submission_id") != saved["submission_id"]
                or record.get("source_files_sha256") != analysis_hashes
                or any(value not in mentioned_ids(analysis)[0] for value in ids)):
            raise m.AtlasError("Saved graph selection does not match its preserved ATLAS source.")
        request = m.read_json(graph_folder / "request.json")
        args = request.get("params", {}).get("arguments", {})
        prompt = (graph_folder / "graph_prompt.md").read_bytes()
        if (request.get("jsonrpc") != "2.0" or request.get("method") != "tools/call"
                or request.get("params", {}).get("name") != m.TOOL
                or set(args) != {"input_value", "session_id"}
                or args.get("session_id") != record.get("conversation_id")
                or not isinstance(args.get("input_value"), str)
                or args["input_value"].encode("utf-8") != prompt):
            raise m.AtlasError("Saved graph request differs from its prompt or conversation record.")
        scopes = [line[len("Scope data: "):] for line in args["input_value"].splitlines() if line.startswith("Scope data: ")]
        if len(scopes) != 1 or json.loads(scopes[0]) != {"run_id": summary["garak_run_id"], "ids": ids}:
            raise m.AtlasError("Saved graph prompt scope differs from the approved selection.")
        response = m.read_json(graph_folder / "response.json", 64 * 1024 * 1024)
        obj, report["validation"] = validate_graph(response, summary["garak_run_id"], ids, target=target)
        graph = obj["graph_result"]
        if ((graph_folder / "kumu_result.json").exists()
                and m.read_json(graph_folder / "kumu_result.json") != obj):
            raise m.AtlasError("Saved derived graph result differs from the original response.")
        for name, field in [("kumu_url.txt", "url"), ("kumu_iframe.txt", "iframe")]:
            if (graph_folder / name).exists() and (graph_folder / name).read_bytes() != graph[field].encode("utf-8"):
                raise m.AtlasError("Saved derived graph file differs from the original response: " + name)
        report["status"] = "validation_passed"
    except (m.AtlasError, OSError, ValueError, TypeError, KeyError) as error:
        report.update(status="validation_failed", rejection_reason=type(error).__name__ + ": " + str(error))
    try:
        unchanged = (source_hashes(run, m.SOURCE_FILES) == run_hashes
                     and source_hashes(graph_folder, names) == hashes
                     and m.file_hash(Path(target["path"])) == target["sha256"]
                     and (analysis_hashes is None or source_hashes(saved_analysis, tuple(analysis_hashes)) == analysis_hashes))
    except (OSError, m.AtlasError):
        unchanged = False
    report["source_files_unchanged"] = unchanged
    if not unchanged:
        report.update(status="validation_failed", rejection_reason="Evidence or expected configuration changed during validation.")
    output_parent = run / "kumu-validations"
    if output_parent.exists() and output_parent.resolve() != output_parent:
        raise m.AtlasError("Validation output directory redirects outside the selected run.")
    output = output_parent / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    m.atomic_json(output / "validation.json", report)
    m.atomic_json(output / "checksums.json", {"validation.json": m.file_hash(output / "validation.json")})
    print("Offline Kumu validation:", "PASSED" if report["status"] == "validation_passed" else "FAILED")
    print("Expected project/map:", target["expected_project_id"], "/", target["expected_map_name"])
    print("Graph scope:", GRAPH_SCOPE)
    if report.get("rejection_reason"):
        print("Reason:", m.terminal_text(report["rejection_reason"]))
    print("Validation record:", output / "validation.json")
    print("Zero network requests. Original evidence unchanged:", unchanged)
    print("URL validation does not verify browser rendering, internal tool execution or candidate mappings.")
    return 0 if report["status"] == "validation_passed" else 2
