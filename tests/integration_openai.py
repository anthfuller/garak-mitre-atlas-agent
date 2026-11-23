"""Offline integration: real Garak/OpenAI SDK, dummy key, HTTPX MockTransport.

All socket connections are denied. Run each case in its own process because
Garak's configuration and report handles are process-global. Never calls OpenAI.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p
import openai_worker as worker
import openai_cost


def main(case):
    def deny_network(event, args):
        if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto"):
            raise AssertionError("Offline integration prohibits network access")
    sys.addaudithook(deny_network)
    import httpx
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        os.environ["XDG_DATA_HOME"] = str(root / "data")
        os.environ["XDG_CONFIG_HOME"] = str(root / "config")
        os.environ["XDG_CACHE_HOME"] = str(root / "cache")
        cfg = {"schema_version": 1, "garak_python": sys.executable,
               "evidence_root": str(root / "evidence"), "xdg_data_home": str(root / "data"),
               "targets": {"openai-reasoning": dict(p.openai_profile.TARGET)}}
        inventory = p.installed_inventory(cfg)
        name = "probes.encoding.InjectBase32" if case == "base32" else "probes.goodside.WhoIsRiley"
        row = next(row for row in inventory["probes"] if row["name"] == name)
        campaign = p.probe_catalog.campaign_for(row, cfg["targets"]["openai-reasoning"], inventory)
        campaign["max_completion_tokens"] = 777
        campaign["input_estimate"] = p.estimate_cloud_workload(cfg, campaign)
        assert campaign["input_estimate"] is not None
        campaign["pricing"] = openai_cost.published_rates("gpt-5.6-sol")
        assert campaign["pricing"] is not None
        choices = []
        if case.startswith("cap_"):
            campaign["workload"]["http_request_limit"] = 1
            choices = {"cap_stop": ["3"], "cap_raise": ["1", "7"], "cap_remove": ["2"]}[case]
        if case.startswith("alert_"):
            campaign["spending_alert_usd"] = "0.000001"
            choices = {"alert_stop": ["3"], "alert_raise": ["2", "1"], "alert_continue": ["1"] * 6}[case]
        if case == "no_rates":
            campaign["pricing"] = None
        folder = p.new_folder(cfg, "synthetic")
        manifest = p.plan(cfg, "openai-reasoning", campaign, folder)
        manifest.update({"process_status": "running", "exit_code": None})
        p.write_json(folder / "manifest.json", manifest)
        p.write_json(folder / "garak-config.json", manifest["resolved_garak_config"])
        p.preflight(cfg, "openai-reasoning", campaign, folder)  # local source/SDK checks only
        key = "sk-DUMMY-INTEGRATION-NOT-A-REAL-CREDENTIAL-030"
        requests = []
        def response(request):
            assert str(request.url) == "https://api.openai.com/v1/chat/completions"
            assert request.headers["authorization"] == "Bearer " + key
            body = json.loads(request.content)
            assert set(body) == {"model", "messages", "max_completion_tokens"}, body
            assert body["model"] == "gpt-5.6-sol" and body["max_completion_tokens"] == 777
            requests.append(body)
            count = len(requests)
            if case in ("auth_failure", "rate_failure"):
                status = 401 if case == "auth_failure" else 429
                return httpx.Response(status, json={"error": {"message": "bad key " + key, "type": "synthetic"}, "usage": {"prompt_tokens": 10, "completion_tokens": 0}})
            if case == "transport_failure":
                raise httpx.ReadTimeout("SYNTHETIC " + key)
            finish = "length" if (case == "check_truncated" and count == 1) or (case == "scan_truncated" and count == 2) else "stop"
            content = "SYNTHETIC reply" + (" " + key if case == "echo_key" else "")
            return httpx.Response(200, headers={"x-request-id": f"SYNTHETIC-{count}"}, json={
                "id": f"SYNTHETIC-{count}", "object": "chat.completion", "created": 1, "model": "gpt-5.6-sol",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}})
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), patch("builtins.input", side_effect=choices):
            code = worker.run(manifest["command_argv"][2:], key, test_transport=httpx.MockTransport(response))
        manifest.update({"process_status": "exited", "exit_code": code,
                         "transport_coverage_gaps": worker.quality_gaps(folder)})
        p.write_json(folder / "manifest.json", manifest)
        summary = p.render_outputs(folder / "scan.report.jsonl", folder, manifest)
        p.checksums(folder)
        failed = case in ("auth_failure", "rate_failure", "transport_failure", "check_truncated", "cap_stop", "alert_stop")
        expected = 1 if failed else 33 if case == "base32" else 7
        assert len(requests) == expected, (case, len(requests), err.getvalue())
        if failed:
            assert code == 2 and summary["execution_status"] == "incomplete", (case, code, summary, err.getvalue())
        elif case == "scan_truncated":
            assert code == 0 and summary["execution_status"] == "complete_with_gaps", summary
        else:
            assert code == 0 and summary["execution_status"] == "completed", (case, code, summary, err.getvalue())
            assert summary["attempts"] == expected - 1
            assert f"evaluated responses: {expected - 1}" in (folder / "atlas_handoff.md").read_text()
            native = (folder / "scan.report.jsonl").read_bytes()
            p.regenerate_handoff(folder)
            assert (folder / "scan.report.jsonl").read_bytes() == native
        assert key not in out.getvalue() + err.getvalue()
        for file in root.rglob("*"):
            if file.is_file():
                assert key.encode() not in file.read_bytes(), str(file)
        assert "OPENAI_API_KEY" not in os.environ
        costs = p.read_json(folder / "openai-cost.json") if (folder / "openai-cost.json").exists() else None
        if case == "no_rates":
            assert costs["estimated_reported_usage_usd"] is None
        elif case != "transport_failure":
            assert costs is not None and costs["events"][0]["stage"] == "compatibility"
        print(f"PASS {case}: {len(requests)} synthetic requests; {summary['execution_status']}; dummy key absent from stdout, stderr and all artifacts.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "normal")
