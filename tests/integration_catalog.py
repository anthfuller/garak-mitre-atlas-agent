"""Optional offline integration using installed Garak, without model generation.

Checks full registry coverage and constructs only the reviewed probe/detector
pairs to validate their actual prompt counts. Network access is denied.
"""
import contextlib
import io
import json
from pathlib import Path
import random
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p
import probe_catalog as c


def main():
    with tempfile.TemporaryDirectory() as temp:
        cfg = {"garak_python": sys.executable, "xdg_data_home": str(Path(temp) / "data")}
        catalog = p.installed_inventory(cfg)
        # Second, direct enumeration is the comparison source, not a bundled list.
        def deny_network(event, args):
            if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto"):
                raise AssertionError("No network during catalog/workload checks")
        sys.addaudithook(deny_network)
        from garak import _plugins, _config
        native_names = {name for name, active in _plugins.enumerate_plugins("probes")}
        assert {row["name"] for row in catalog["probes"]} == native_names
        displayed = []
        available = c.supported_rows(catalog, {"provider": "ollama"})
        pages = c.page_rows(available)[3]
        for page in range(pages):
            displayed.extend(row["name"] for row in c.page_rows(available, page=page)[0])
        assert len(displayed) == len(set(displayed)) == len(c.policy()["probes"])
        assert set(displayed).issubset(native_names)
        assert set(displayed) == {r["name"] for r in c.supported_rows(catalog, {"provider": "openai"})}
        settings = Path(temp) / "config.json"
        settings.write_text(json.dumps({"run": {"soft_probe_prompt_cap": 32, "generations": 1, "seed": 42}}))
        _config.load_config(site_config_filename="isolated-nonexistent-site.yaml", run_config_filename=str(settings))
        target = {"provider": "ollama"}
        counts = {}
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            for row in catalog["probes"]:
                supported, reason = c.assess(row, target, catalog)
                assert reason
                if not supported:
                    continue
                profile = c.campaign_for(row, target, catalog)
                random.seed(42)
                probe = _plugins.load_plugin(row["name"])
                detector = _plugins.load_plugin("detectors." + profile["detector"])
                count = len(probe.prompts)
                assert 0 < count <= profile["workload"]["attempt_cap"], (row["name"], count)
                expected = profile["workload"]["expected_attempts"]
                assert expected is None or expected == count, (row["name"], count, expected)
                assert probe.primary_detector == profile["detector"]
                assert detector is not None
                counts[row["name"]] = count
        assert set(counts) == set(c.policy()["probes"]), "Every enabled probe must be exercised"
        print(f"PASS catalog: {len(native_names)} installed probes; {len(displayed)} available displayed across {pages} page(s), other entries excluded; {len(counts)} reviewed workloads and detectors constructed. Zero generation requests.")
        print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
