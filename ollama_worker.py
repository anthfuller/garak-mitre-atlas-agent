"""Run the unchanged Garak Ollama adapter with local HTTP evidence and error stops.

Only this scanner child replaces ollama.Client's factory. Installed packages are
never edited. HTTP failures/timeouts stop immediately; successful responses,
including Garak's existing bounded empty-response handling, are unchanged.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse


POLICY = "Stop on first HTTP error, transport error or timeout; no error retries. Garak may retry successful empty responses up to three total calls."


class AbortRun(BaseException):
    """Do not let Garak's exception/backoff wrappers repeat a failed request."""


def save(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def run(arguments, *, test_transport=None, scan=None):
    """The injected transport/scan are Python-only offline test seams, not CLI options."""
    import httpx
    import ollama

    folder = Path(arguments[arguments.index("--report_prefix") + 1]).parent
    config = json.loads(Path(arguments[arguments.index("--config") + 1]).read_text(encoding="utf-8"))
    settings = config["plugins"]["generators"]["ollama"]["OllamaGeneratorChat"]
    endpoint = settings["host"].rstrip("/")
    model = arguments[arguments.index("--target_name") + 1]
    parsed = urlparse(endpoint)
    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path):
        raise ValueError("Ollama worker requires the reviewed unauthenticated HTTP loopback endpoint.")
    if os.environ.get("OLLAMA_API_KEY"):
        raise ValueError("Authenticated Ollama profiles are not supported by this local worker.")

    session = {"status": "scanning", "endpoint": endpoint, "model": model, "http_requests": 0,
               "transport_policy": POLICY, "generation_settings_changed": False}
    original_client = ollama.Client
    transports = []

    def record(value):
        value["recorded_at"] = datetime.now(timezone.utc).isoformat()
        with (folder / "ollama-transport.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False) + "\n")
        save(folder / "ollama-session.json", session)

    class AuditedTransport(httpx.BaseTransport):
        def __init__(self):
            self.inner = test_transport if test_transport is not None else httpx.HTTPTransport(retries=0, trust_env=False)

        def handle_request(self, request):
            if request.method != "POST" or str(request.url) != endpoint + "/api/chat":
                raise AbortRun("Unexpected Ollama request destination/method; request blocked.")
            if request.headers.get("authorization"):
                raise AbortRun("Authorization header is not allowed by this unauthenticated local profile.")
            raw_request = request.read()
            payload = json.loads(raw_request)
            if payload.get("model") != model or payload.get("stream") is not False:
                raise AbortRun("Ollama request model/stream mode differs from the reviewed profile.")
            session["http_requests"] += 1
            sequence = session["http_requests"]
            record({"entry_type": "request", "stage": "scan", "sequence": sequence,
                    "body": payload, "body_base64": base64.b64encode(raw_request).decode("ascii")})
            started = time.monotonic()
            response = None
            try:
                response = self.inner.handle_request(request)
                raw = response.read()
            except Exception as exc:
                record({"entry_type": "transport_error", "sequence": sequence, "stage": "scan",
                        "error_type": type(exc).__name__, "error": str(exc),
                        "elapsed_seconds": round(time.monotonic() - started, 3)})
                raise AbortRun("Ollama transport failed (" + type(exc).__name__ + "); no retry sent. See ollama-transport.jsonl.") from None
            finally:
                if response is not None:
                    response.close()
            status = response.status_code
            text = raw.decode("utf-8", errors="replace")
            try:
                body = json.loads(text)
            except ValueError:
                body = {"non_json_response": text}
            record({"entry_type": "response", "stage": "scan", "sequence": sequence,
                    "http_status": status, "elapsed_seconds": round(time.monotonic() - started, 3),
                    "body": body, "body_base64": base64.b64encode(raw).decode("ascii")})
            if status != 200:
                # JSON-escape controls in untrusted server text before terminal display.
                error = body.get("error", body) if isinstance(body, dict) else body
                display = json.dumps(error, ensure_ascii=True)
                if len(display) > 1200:
                    display = display[:1200] + "... [full body saved]"
                session.update(http_status=status, error_sequence=sequence)
                raise AbortRun(f"Ollama returned HTTP {status}: {display}. No retry or next scan request sent.")
            # Preserve the original body bytes, including all generation metadata.
            return httpx.Response(status, content=raw, request=request,
                                  headers={"content-type": response.headers.get("content-type", "application/json")})

        def close(self):
            self.inner.close()

    def client(*args, **kwargs):
        # Ollama's public Client constructor forwards these HTTPX client options.
        # Retain host, timeout and every generation option supplied by Garak.
        if "transport" in kwargs:
            raise AbortRun("Unexpected preconfigured Ollama transport; scan stopped.")
        transport = AuditedTransport()
        transports.append(transport)
        return original_client(*args, **(kwargs | {"transport": transport, "trust_env": False, "follow_redirects": False}))

    try:
        save(folder / "ollama-session.json", session)
        ollama.Client = client
        if scan is None:
            from garak import cli
            scan = cli.main
        scan(arguments)
        session["status"] = "scan_returned"
        return 0
    except KeyboardInterrupt:
        session.update(status="interrupted", error="Operator interrupted local scan.")
        return 130
    except (Exception, AbortRun) as exc:
        session.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        print("Ollama worker stopped: " + session["error"], file=sys.stderr)
        return 2
    finally:
        ollama.Client = original_client
        try:
            save(folder / "ollama-session.json", session)
        finally:
            for transport in transports:
                transport.close()


def quality_gaps(folder):
    """Applied only to new runs whose manifest declares this transport policy."""
    folder = Path(folder)
    try:
        session = json.loads((folder / "ollama-session.json").read_text(encoding="utf-8"))
        path = folder / "ollama-transport.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        return ["Ollama session/transport evidence is missing or invalid; execution is unverified."]
    gaps = []
    if session.get("status") != "scan_returned":
        gaps.append("Ollama worker did not finish: " + session.get("error", session.get("status", "unknown")))
    requests = [r for r in rows if r.get("entry_type") == "request"]
    if len(requests) != session.get("http_requests"):
        gaps.append("Ollama request count differs from session record.")
    for request in requests:
        seq = request.get("sequence")
        outcomes = [r for r in rows if r.get("sequence") == seq and r.get("entry_type") in ("response", "transport_error")]
        if len(outcomes) != 1:
            gaps.append(f"Ollama request {seq} has no unique recorded outcome.")
        elif outcomes[0].get("entry_type") == "transport_error":
            gaps.append(f"Ollama request {seq} failed: " + outcomes[0].get("error_type", "unknown transport error"))
        elif outcomes[0].get("http_status") != 200:
            gaps.append(f"Ollama request {seq} returned HTTP {outcomes[0].get('http_status')}; error body saved in ollama-transport.jsonl.")
    return gaps


def main(arguments=None):
    try:
        return run(list(sys.argv[1:] if arguments is None else arguments))
    except Exception as exc:
        print("Ollama worker could not start: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
