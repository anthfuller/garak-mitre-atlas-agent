"""Installed Garak 0.17.0 inventory and reviewed local probe capabilities.

Only the --collect child imports Garak. Inventory never constructs a probe,
detector or generator. Network connections are denied in that child.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import re
import sys
import openai_profile

ROOT = Path(__file__).resolve().parent
PAGE_SIZE = 20


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def policy():
    return json.loads((ROOT / "probe-support.json").read_text(encoding="utf-8"))


def collect():
    """Use the audited Garak enumeration API, including inactive probes."""
    version = importlib.metadata.version("garak")
    if version != "0.17.0":
        raise ValueError("Probe inventory requires the configured Garak 0.17.0 installation.")
    def deny_network(event, args):
        if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto"):
            raise RuntimeError("Network access is disabled during probe inventory.")
    sys.addaudithook(deny_network)
    from garak import _plugins
    dist = importlib.metadata.distribution("garak")
    rules = policy()
    files = set(rules["common_source_checks"])
    for checks in rules.get("provider_source_checks", {}).values():
        files.update(checks)
    for rule in rules["probes"].values():
        files.update(rule["source_checks"])
    hashes = {}
    for name in sorted(files):
        path = Path(dist.locate_file(name))
        hashes[name] = digest(path) if path.is_file() else None
    rows = []
    # This is the same registry used by --list_probes, with no active-only filter.
    for name, active in _plugins.enumerate_plugins("probes"):
        info = dict(_plugins.plugin_info(name))
        rows.append({"name": name, "active": active, "metadata": info})
    return {"garak_version": version, "probes": rows, "source_sha256": hashes,
            "inventory_method": "garak._plugins.enumerate_plugins('probes') + plugin_info",
            "generation_requests": 0}


def assess(row, target, inventory, rules=None):
    """Runner support is independent of Garak's default-active flag."""
    rules = rules if rules is not None else policy()
    info = row["metadata"]
    if target.get("provider") not in ("ollama", "openai"):
        return False, "This runner supports Ollama and OpenAI text targets only."
    if inventory.get("garak_version") != rules["garak_version"]:
        return False, "Installed Garak version differs from the reviewed 0.17.0 release."
    if set(info.get("modality", {}).get("in", [])) != {"text"}:
        return False, "Requires a non-text or unspecified input modality; this runner uses text chat."
    rule = rules["probes"].get(row["name"])
    if rule is None:
        deps = info.get("extra_dependency_names") or []
        if deps:
            return False, "Extra dependencies/workload not configured: " + ", ".join(deps)
        return False, "Probe/detector workload has not been validated for this runner."
    if info.get("primary_detector") != rule["detector"]:
        return False, "Installed primary detector differs from the reviewed pairing."
    expected = rules["common_source_checks"] | rule["source_checks"] | rules.get("provider_source_checks", {}).get(target["provider"], {})
    for name, value in expected.items():
        if inventory.get("source_sha256", {}).get(name) != value:
            return False, "Installed source differs or is missing: " + name
    return True, "Reviewed text workload and local detector; no auxiliary model/API. Target API compatibility requires a live check." if target["provider"] == "openai" else "Supported: reviewed text workload and local detector; no auxiliary model/API."


def campaign_for(row, target, inventory, rules=None):
    rules = rules if rules is not None else policy()
    supported, reason = assess(row, target, inventory, rules)
    if not supported:
        raise ValueError(reason)
    rule = rules["probes"][row["name"]]
    # These are explicit new-experiment settings, not inherited from an old run.
    result = {
        "spec": row["name"], "detector": rule["detector"],
        "detector_selection": rule.get("detector_selection", "explicit"),
        "prompt_cap": 32, "seed": 42, "temperature": 0.0, "max_tokens": 256,
        "wall_time_seconds": 1800,
        "objective": row["metadata"].get("goal") or row["metadata"].get("description", ""),
        "analyst_success_criterion": "Confirm only behavior violating a stated model-use requirement; review flags and legitimate-task completion separately.",
        "scope": "One explicitly selected installed text probe, one response per attempt, one primary detector.",
        "experimental_effect": "New experiment with seed 42, temperature 0, 256 output tokens and sequential requests; not an exact reproduction.",
        "limitations": rule["detector_limitations"],
        "workload": {"attempt_cap": 32, "expected_attempts": rule["expected_attempts"],
                     "validation_basis": rule["workload_basis"], "enforcement": rule["enforcement"],
                     "generations_per_attempt": 1, "http_request_limit": None},
        "extra_dependencies": [], "auxiliary_models": [],
        "api_use": "Local Ollama target only; no paid API or auxiliary service.",
        "source_checks": rules["common_source_checks"] | rule["source_checks"] | rules.get("provider_source_checks", {}).get(target["provider"], {}),
        "catalog_selection": {"name": row["name"], "active_by_default": row["active"],
                              "metadata": row["metadata"], "inventory_method": inventory["inventory_method"],
                              "inventory_count": len(inventory["probes"]),
                              "inventory_sha256": hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()},
    }
    return openai_profile.campaign_settings(result) if target["provider"] == "openai" else result


def supported_rows(inventory, target, rules=None):
    """Filter before search/pagination so unavailable rows never affect counts."""
    rules = rules if rules is not None else policy()
    return [row for row in inventory["probes"] if assess(row, target, inventory, rules)[0]]


def page_rows(rows, query="", page=0):
    """Stable, case-insensitive name/family search with twenty results per page."""
    found = sorted((r for r in rows if query.casefold() in r["name"].casefold()), key=lambda r: r["name"])
    pages = max(1, (len(found) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    return found[page * PAGE_SIZE:(page + 1) * PAGE_SIZE], len(found), page, pages


def terminal_text(value):
    # Metadata is display data. Remove terminal controls; no ANSI interpretation.
    return " ".join(re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(value)).split())


def estimate_probe(name):
    """Construct one reviewed workload offline; never instantiate a generator."""
    import random
    import tempfile
    import openai_cost
    inventory = collect()
    row = next((r for r in inventory["probes"] if r["name"] == name), None)
    if row is None or not assess(row, openai_profile.TARGET, inventory)[0]:
        raise ValueError("Selected workload is unavailable in this installed source.")
    from garak import _config, _plugins
    with tempfile.TemporaryDirectory() as temp:
        settings = Path(temp) / "estimate.json"
        settings.write_text(json.dumps({"run": {"seed": 42, "soft_probe_prompt_cap": 32, "generations": 1}}))
        _config.load_config(site_config_filename="isolated-nonexistent-site.yaml", run_config_filename=str(settings))
        random.seed(42)
        probe = _plugins.load_plugin(name)
        if not 0 < len(probe.prompts) <= 32 or any(not isinstance(p, str) for p in probe.prompts):
            raise ValueError("Workload cannot be estimated by this text-input estimator.")
        prompts = list(probe.prompts) + ["Reply with exactly OK."]
        maximum = max(openai_cost.input_units([{"role": "user", "content": p}]) for p in prompts)
        if maximum >= 272000:
            raise ValueError("Input estimate exceeds this profile's short-context pricing boundary.")
        return {"probe": name, "sampled_prompt_count": len(probe.prompts),
                "scan_messages": [[{"role": "user", "content": p}] for p in probe.prompts],
                "max_input_units_per_request": maximum,
                "sample_sha256": hashlib.sha256(json.dumps(prompts, ensure_ascii=False).encode()).hexdigest(),
                "method": "UTF-8 JSON bytes plus 64 units per request; conservative proxy, not actual tokenization. No API requests."}


if __name__ == "__main__":
    if sys.argv[1:] != ["--collect"] and not (len(sys.argv) == 3 and sys.argv[1] == "--estimate"):
        raise SystemExit("This helper is invoked by playbook.py, not as a scanner.")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = collect() if sys.argv[1] == "--collect" else estimate_probe(sys.argv[2])
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    except Exception as exc:
        print("Inventory failed: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
