"""Inspect a local MCP server without invoking tools or reading Garak evidence.

Python standard library only. Protocol references:
https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle
https://modelcontextprotocol.io/specification/2025-03-26/server/tools
"""
import argparse
from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import warnings


PROTOCOL = "2025-03-26"
VERSION = "0.2.0"
LIMIT = 1024 * 1024
ALLOWED_METHODS = {"initialize", "notifications/initialized", "tools/list"}


class DiscoveryError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DiscoveryError("Redirect refused; use the exact local MCP endpoint.")


def validate_url(url):
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != "http" or parts.hostname not in ("localhost", "127.0.0.1", "::1")
            or parts.username or parts.password or parts.query or parts.fragment):
        raise DiscoveryError("This inspection accepts a local HTTP URL without credentials or query parameters.")
    if not parts.port:
        raise DiscoveryError("Specify the port shown in the project's MCP connection JSON.")


def prompt_api_key():
    # Fail closed instead of allowing getpass to fall back to echoed input.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = getpass.getpass("Langflow API key (hidden; session only): ")
        except getpass.GetPassWarning:
            raise DiscoveryError("Hidden input is unavailable; run from an interactive PowerShell terminal.") from None
    if (not key or key != key.strip() or key in {"YOUR_API_KEY", "REDACTED"}
            or any(ord(char) < 33 or ord(char) > 126 for char in key)):
        raise DiscoveryError("Enter the actual API key without quotes, whitespace, or control characters.")
    return key


def redact(value, secrets):
    """Remove known credentials even when reflected in server metadata/errors."""
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, dict):
        return {redact(key, secrets): redact(item, secrets) for key, item in value.items()}
    return value


def read_rpc(response, expected_id):
    kind = response.headers.get_content_type()
    if kind == "application/json":
        raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise DiscoveryError("Discovery response exceeded 1 MiB.")
        message = json.loads(raw.decode("utf-8"))
    elif kind == "text/event-stream":
        data, total, deadline = [], 0, time.monotonic() + 30
        while True:
            if time.monotonic() > deadline:
                raise DiscoveryError("Discovery event stream exceeded its time limit.")
            raw = response.readline(LIMIT + 1)
            total += len(raw)
            if total > LIMIT:
                raise DiscoveryError("Discovery event stream exceeded 1 MiB.")
            if not raw:
                raise DiscoveryError("Event stream ended before the matching response.")
            line = raw.decode("utf-8").rstrip("\r\n")
            if line.startswith("data:"):
                value = line[5:]
                data.append(value[1:] if value.startswith(" ") else value)
            elif not line and data:
                message = json.loads("\n".join(data))
                data = []
                if not isinstance(message, dict):
                    raise DiscoveryError("MCP event was not a JSON object.")
                if "method" in message:
                    if "id" in message:
                        raise DiscoveryError("Unexpected server request; no client capabilities were offered.")
                    continue
                break
    else:
        raise DiscoveryError("Expected an MCP JSON or SSE response, received " + kind)
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or message.get("id") != expected_id:
        raise DiscoveryError("MCP response version or request ID did not match.")
    if "error" in message:
        raise DiscoveryError("MCP returned error: " + json.dumps(message["error"], ensure_ascii=True))
    if not isinstance(message.get("result"), dict):
        raise DiscoveryError("MCP response is missing its result object.")
    return message


def discover(url, record, api_key=None, secrets=None):
    validate_url(url)
    secrets = secrets if secrets is not None else set()
    if api_key:
        secrets.add(api_key)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    session = None
    initialized = False

    def post(method, request_id=None, params=None):
        nonlocal session
        if method not in ALLOWED_METHODS:
            raise DiscoveryError("Only initialization and tools/list are permitted.")
        message = {"jsonrpc": "2.0", "method": method}
        if request_id is not None:
            message["id"] = request_id
        if params is not None:
            message["params"] = params
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if api_key:
            headers["x-api-key"] = api_key
        if session:
            headers["Mcp-Session-Id"] = session
        if initialized:
            headers["MCP-Protocol-Version"] = PROTOCOL
        item = {"request": message}
        record["exchanges"].append(item)
        req = urllib.request.Request(url, data=json.dumps(message).encode("utf-8"), headers=headers, method="POST")
        try:
            record["authentication_sent"] = bool(api_key)
            with opener.open(req, timeout=30) as response:
                item["http_status"] = response.status
                if method == "initialize":
                    session = response.headers.get("Mcp-Session-Id")
                    if session:
                        secrets.add(session)
                if request_id is None:
                    if response.status != 202:
                        raise DiscoveryError("Initialized notification was not acknowledged with HTTP 202.")
                    return None
                item["response"] = read_rpc(response, request_id)
                return item["response"]["result"]
        except urllib.error.HTTPError as exc:
            item["http_status"] = exc.code
            exc.close()
            hint = ""
            if exc.code in (401, 403):
                hint = (" The supplied API key was not accepted or lacks access; no tool was invoked."
                        if api_key else " Authentication is required; no credential was sent.")
            raise DiscoveryError(f"HTTP {exc.code} during {method}.{hint}") from None

    try:
        init = post("initialize", 1, {"protocolVersion": PROTOCOL, "capabilities": {},
                    "clientInfo": {"name": "garak-playbook-mcp-inspection", "version": VERSION}})
        record["server_info"] = init.get("serverInfo")
        record["protocol_version"] = init.get("protocolVersion")
        if init.get("protocolVersion") != PROTOCOL:
            raise DiscoveryError("Server selected a different protocol version; stop and inspect before proceeding.")
        initialized = True
        post("notifications/initialized")
        if "tools" not in init.get("capabilities", {}):
            raise DiscoveryError("Server did not advertise tools capability.")
        cursor, seen_cursors, names = None, set(), set()
        for page in range(20):
            result = post("tools/list", page + 2, {"cursor": cursor} if cursor else {})
            rows = result.get("tools")
            if not isinstance(rows, list):
                raise DiscoveryError("tools/list did not return a tool list.")
            for tool in rows:
                if (not isinstance(tool, dict) or not isinstance(tool.get("name"), str)
                        or not isinstance(tool.get("inputSchema"), dict)):
                    raise DiscoveryError("Tool name or input schema is missing.")
                if tool["name"] in names:
                    raise DiscoveryError("Duplicate tool name in discovery results.")
                names.add(tool["name"])
                record["tools"].append(tool)
            cursor = result.get("nextCursor")
            if not cursor:
                record["status"] = "discovery_complete"
                return
            if not isinstance(cursor, str) or cursor in seen_cursors:
                raise DiscoveryError("Invalid or repeated discovery cursor.")
            seen_cursors.add(cursor)
        raise DiscoveryError("Discovery pagination exceeded 20 pages; inventory is incomplete.")
    finally:
        # Close only this inspection's temporary protocol session when supported.
        # Session identifiers remain in memory and are never written to the report.
        if session:
            headers = {"Mcp-Session-Id": session, "MCP-Protocol-Version": PROTOCOL}
            if api_key:
                headers["x-api-key"] = api_key
            try:
                with opener.open(urllib.request.Request(url, headers=headers, method="DELETE"), timeout=5) as response:
                    record["session_cleanup_http_status"] = response.status
            except urllib.error.HTTPError as exc:
                record["session_cleanup_http_status"] = exc.code
                exc.close()
            except Exception as exc:
                record["session_cleanup_error"] = type(exc).__name__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--api-key-prompt", action="store_true",
                        help="Prompt for a Langflow API key using hidden input; never accept the key as a CLI value.")
    args = parser.parse_args()
    # Validate before saving the URL or asking for any credential.
    try:
        validate_url(args.url)
    except (DiscoveryError, ValueError):
        print("ERROR: Supply the exact loopback HTTP endpoint with a port and no credentials, query, or fragment.")
        return 2
    directory = Path(args.output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = directory / ("atlas-mcp-discovery-" + stamp + "-" + uuid.uuid4().hex[:8] + ".json")
    record = {"inspection_version": VERSION, "created_at": datetime.now(timezone.utc).isoformat(),
              "endpoint": args.url, "transport": "streamable_http", "authentication_sent": False,
              "authentication_mode": "x-api-key" if args.api_key_prompt else "none",
              "status": "incomplete", "tool_invocations": 0, "exchanges": [], "tools": []}
    secrets = set()
    try:
        api_key = prompt_api_key() if args.api_key_prompt else None
        if api_key:
            secrets.add(api_key)
        discover(args.url, record, api_key, secrets)
    except (Exception, KeyboardInterrupt) as exc:
        record["error"] = type(exc).__name__ + ": " + str(exc)
    clean = redact(record, secrets)
    clean["credential_redaction_applied"] = clean != record
    record = clean
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    print("Discovery status:", record["status"])
    print("Tool invocations: 0; no Garak handoff submitted.")
    if "error" in record:
        print("ERROR:", record["error"])
    for tool in record["tools"]:
        print("Tool:", ascii(tool["name"]))
        print("Input schema:", json.dumps(tool["inputSchema"], ensure_ascii=True))
    print("Discovery report:", redact(str(destination), secrets))
    return 0 if record["status"] == "discovery_complete" else 2


if __name__ == "__main__":
    sys.exit(main())
