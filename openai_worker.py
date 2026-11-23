"""Isolated OpenAI worker: audited Garak generator, transport controls and secret handling.

The CLI reads the key through a hidden terminal prompt. Tests inject a transport in memory;
there is no test endpoint or credential argument exposed by the runner.
"""
from __future__ import annotations
import contextlib
from datetime import datetime, timezone
import inspect
import json
import logging
import os
from pathlib import Path
import re
import sys
import time

import openai_profile as profile
import openai_cost


class AbortRun(BaseException):
    """Bypass SDK/Garak exception retry wrappers after an intentional stop."""
    pass


def scrub(text, key):
    text = str(text).replace(json.dumps(key)[1:-1], "[REDACTED_API_KEY]").replace(key, "[REDACTED_API_KEY]")
    return re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED_API_KEY]", text)


class SecretStream:
    """Hold a possible split credential until the following write arrives."""
    def __init__(self, stream, key):
        self.stream, self.key, self.pending = stream, key, ""
    def write(self, text):
        self.pending = (self.pending + text).replace(self.key, "[REDACTED_API_KEY]")
        cut = max(0, len(self.pending) - len(self.key) + 1)
        self.stream.write(self.pending[:cut])
        self.pending = self.pending[cut:]
        return len(text)
    def flush(self):
        # Only retain a suffix that could be the beginning of a split key.
        hold = max((i for i in range(1, min(len(self.key), len(self.pending) + 1))
                    if self.pending.endswith(self.key[:i])), default=0)
        cut = len(self.pending) - hold
        self.stream.write(self.pending[:cut])
        self.pending = self.pending[cut:]
        self.stream.flush()
    def finish(self):
        self.stream.write(scrub(self.pending, self.key))
        self.pending = ""
        self.stream.flush()
    def isatty(self):
        return False
    @property
    def encoding(self):
        return "utf-8"


@contextlib.contextmanager
def secret_output(key):
    stdout, stderr = SecretStream(sys.stdout, key), SecretStream(sys.stderr, key)
    original_format = logging.Formatter.format
    def safe_format(formatter, record):
        return scrub(original_format(formatter, record), key)
    logging.Formatter.format = safe_format
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            yield
    finally:
        logging.Formatter.format = original_format
        stdout.finish()
        stderr.finish()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(arguments, key, *, test_transport=None):
    """Actual Garak execution; test_transport is available only to offline Python tests."""
    import httpx
    import openai
    folder = Path(arguments[arguments.index("--report_prefix") + 1]).parent
    config = json.loads(Path(arguments[arguments.index("--config") + 1]).read_text(encoding="utf-8"))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    model = arguments[arguments.index("--target_name") + 1]
    limit = config["plugins"]["generators"]["openai"]["OpenAIReasoningGenerator"]["max_completion_tokens"]
    ceiling = manifest["campaign"]["workload"].get("http_request_limit")
    costs = openai_cost.Tracker(folder, manifest["campaign"])
    session = {"model_requested": model, "model_access": "unverified", "probe_compatibility": "not yet exercised",
               "max_completion_tokens": limit, "http_request_limit": ceiling,
               "sdk_retries": 0, "status": "checking", "http_requests": 0, "credential_echo_redacted": False}
    stage = "compatibility"
    original_client = openai.OpenAI
    transports = []

    def record(value):
        value["recorded_at"] = datetime.now(timezone.utc).isoformat()
        with (folder / "openai-transport.jsonl").open("a", encoding="utf-8") as file:
            file.write(scrub(json.dumps(value, ensure_ascii=False), key) + "\n")

    class AuditedTransport(httpx.BaseTransport):
        def __init__(self):
            self.inner = test_transport if test_transport is not None else httpx.HTTPTransport(retries=0, trust_env=False)
        def handle_request(self, request):
            nonlocal ceiling
            if request.method != "POST" or str(request.url) != "https://api.openai.com/v1/chat/completions":
                raise AbortRun("Unapproved OpenAI request destination or method; request blocked.")
            while ceiling is not None and session["http_requests"] >= ceiling:
                print(f"Optional request cap reached: {session['http_requests']}/{ceiling}. No next request sent.")
                print("[1] Raise request cap\n[2] Remove request cap\n[3] Stop")
                try:
                    choice = input("Selection (Enter stops): ").strip()
                    if choice == "1":
                        value = input("New request cap: ").strip()
                        if not value.isascii() or not value.isdigit() or int(value) <= session["http_requests"]:
                            print("Enter a whole number above the number of requests already sent.")
                            continue
                        ceiling = int(value)
                    elif choice == "2":
                        ceiling = None
                    elif choice in ("", "3"):
                        raise AbortRun("Operator stopped at the optional request cap.")
                    else:
                        continue
                except (EOFError, KeyboardInterrupt):
                    raise AbortRun("Operator stopped at the optional request cap.") from None
                session["http_request_limit"] = ceiling
                record({"entry_type": "request_cap_change", "request_count": session["http_requests"], "new_cap": ceiling})
            try:
                costs.before_request()
            except openai_cost.StopRequested as exc:
                raise AbortRun(str(exc)) from None
            payload = json.loads(request.read())
            if set(payload) != {"model", "messages", "max_completion_tokens"} or payload["model"] != model or payload["max_completion_tokens"] != limit:
                raise AbortRun("Effective OpenAI request parameters differ from the reviewed plan; request blocked.")
            session["http_requests"] += 1
            seq = session["http_requests"]
            record({"entry_type": "request", "sequence": seq, "stage": stage, "body": payload})
            started = time.monotonic()
            try:
                response = self.inner.handle_request(request)
                raw = response.read()
                status, headers = response.status_code, dict(response.headers)
                response.close()
            except Exception as exc:
                record({"entry_type": "transport_error", "sequence": seq, "stage": stage, "error_type": type(exc).__name__})
                costs.after_response({}, seq, stage)
                raise AbortRun("OpenAI transport failed; scan stopped. See the transport record.") from None
            text = raw.decode("utf-8", errors="replace")
            clean = scrub(text, key)
            session["credential_echo_redacted"] |= clean != text
            try:
                body = json.loads(clean)
            except ValueError:
                body = {"non_json_response": clean}
            if status >= 400:
                # API error text can quote a partial credential. Never retain it.
                body = {"error": "Provider error body omitted to prevent credential disclosure.", "usage": body.get("usage") if isinstance(body, dict) else None}
            record({"entry_type": "response", "sequence": seq, "stage": stage,
                    "http_status": status, "request_id": scrub(headers.get("x-request-id", ""), key),
                    "elapsed_seconds": round(time.monotonic() - started, 3), "body": body})
            costs.after_response(body, seq, stage)
            if status != 200:
                raise AbortRun(f"OpenAI returned HTTP {status}; no retries or further scan requests sent.")
            return httpx.Response(status, content=clean.encode("utf-8"),
                                  headers={"content-type": "application/json"}, request=request)
        def close(self):
            self.inner.close()

    def client(*args, **kwargs):
        transport = AuditedTransport()
        transports.append(transport)
        return original_client(api_key=key, base_url=profile.TARGET["endpoint"], max_retries=0,
            http_client=httpx.Client(transport=transport, timeout=120, trust_env=False, follow_redirects=False))

    with secret_output(key):
        try:
            os.environ["OPENAI_API_KEY"] = key  # child-only, removed before exit
            openai.OpenAI = client
            from garak import _config
            from garak.attempt import Conversation, Turn, Message
            from garak.generators.openai import OpenAIReasoningGenerator
            _config.load_config(site_config_filename="isolated-nonexistent-site.yaml",
                                run_config_filename=arguments[arguments.index("--config") + 1])
            generator = OpenAIReasoningGenerator(model, config_root=_config)
            try:
                if "max_completion_tokens" not in inspect.signature(generator.generator.create).parameters:
                    raise RuntimeError("Installed SDK cannot forward max_completion_tokens; no API request sent.")
                reply = generator.generate(Conversation([Turn("user", Message("Reply with exactly OK."))]), 1)
            finally:
                generator.close()
            rows = [json.loads(line) for line in (folder / "openai-transport.jsonl").read_text().splitlines()]
            last = next(row for row in reversed(rows) if row["entry_type"] == "response")
            choices = last["body"].get("choices", [])
            if len(choices) != 1 or choices[0].get("finish_reason") != "stop" or not reply or not reply[0].text or not reply[0].text.strip():
                raise RuntimeError("Compatibility request did not produce a complete nonempty response; no probe started. Review the saved response and completion limit.")
            session.update({"model_access": "confirmed by this request", "status": "scanning",
                            "model_returned": last["body"].get("model"),
                            "probe_compatibility": "unverified; selected probe now being exercised"})
            save(folder / "openai-session.json", session)
            print("Model API access confirmed. This does not validate the selected probe; starting its separate execution.")
            stage = "scan"
            from garak import cli
            cli.main(arguments)
            session.update({"status": "scan_returned", "probe_compatibility": "Inspect native report and summary for selected-probe execution and coverage; no broad compatibility claim."})
            return 0
        except (Exception, AbortRun) as exc:
            session.update({"status": "failed", "error_type": type(exc).__name__, "error": scrub(str(exc), key)})
            print("OpenAI worker stopped: " + session["error"], file=sys.stderr)
            return 2
        finally:
            save(folder / "openai-session.json", session)
            openai.OpenAI = original_client
            os.environ.pop("OPENAI_API_KEY", None)
            for transport in transports:
                transport.close()


def quality_gaps(folder):
    """Keep transport failures, absent/truncated outputs and unfinished calls visible."""
    folder = Path(folder)
    if not (folder / "openai-session.json").is_file():
        return ["OpenAI session record missing; model access and transport completion unverified."]
    session = json.loads((folder / "openai-session.json").read_text(encoding="utf-8"))
    gaps = []
    if session.get("status") != "scan_returned":
        gaps.append("OpenAI compatibility check or scan did not finish successfully.")
    path = folder / "openai-transport.jsonl"
    if not path.is_file():
        return gaps + ["OpenAI transport records missing."]
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except ValueError:
        return gaps + ["OpenAI transport record incomplete or invalid."]
    requests = {r["sequence"] for r in rows if r["entry_type"] == "request"}
    responses = {r["sequence"] for r in rows if r["entry_type"] == "response"}
    if not requests or len(requests) != session.get("http_requests"):
        gaps.append("OpenAI transport request count is missing or differs from the session record.")
    if session.get("model_access") != "confirmed by this request":
        gaps.append("OpenAI model access was not confirmed by a successful compatibility response.")
    checks = [r for r in rows if r["entry_type"] == "response" and r.get("stage") == "compatibility"]
    if len(checks) != 1:
        gaps.append("Expected one recorded compatibility response, separate from probe results.")
    if requests != responses:
        gaps.append("OpenAI request has no recorded response; coverage incomplete.")
    report = folder / "scan.report.jsonl"
    if report.is_file():
        try:
            attempts = {r["uuid"] for line in report.read_text(encoding="utf-8").splitlines()
                        if (r := json.loads(line)).get("entry_type") == "attempt" and r.get("status") == 2}
            scan_responses = [r for r in rows if r["entry_type"] == "response" and r.get("stage") == "scan" and r["http_status"] == 200]
            if len(attempts) != len(scan_responses):
                gaps.append("OpenAI scan-response count differs from completed native attempts; review retries or missing records.")
        except (ValueError, KeyError):
            gaps.append("Could not reconcile OpenAI transport with native attempts.")
    for row in rows:
        if row["entry_type"] != "response":
            continue
        if row["http_status"] != 200:
            gaps.append(f"OpenAI request {row['sequence']} returned HTTP {row['http_status']}.")
            continue
        choices = row["body"].get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") != "stop" or not (choices[0].get("message", {}).get("content") or "").strip():
            gaps.append(f"OpenAI request {row['sequence']} ({row['stage']}) lacks one complete nonempty text response; inspect finish reason and token limit.")
    return gaps


if __name__ == "__main__":
    # Read directly from the inherited terminal; neither parent nor logs see the key.
    session_key = profile.read_session_key()
    if session_key is None:
        raise SystemExit("No key entered; no OpenAI API check or scan started.")
    try:
        raise SystemExit(run(sys.argv[1:], session_key))
    finally:
        session_key = None
