"""Run the complete synthetic suite and retain a pass/fail receipt outside the checkout."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    if out.is_relative_to(ROOT):
        p.error("--out must be outside the source checkout")
    out.mkdir(parents=True, exist_ok=False)
    report = {"status": "incomplete", "started_at": datetime.now(timezone.utc).isoformat(),
              "platform": platform.platform(), "python": sys.version,
              "synthetic_evidence": True, "live_models": False, "paid_calls": False}
    try:
        report["chroma_version"] = importlib.metadata.version("chromadb")
        if report["chroma_version"] != "1.5.9":
            raise RuntimeError("Complete suite requires chromadb==1.5.9; no skipped Chroma tests accepted.")
        report["commit"] = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(ROOT / "tests"))
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        sys.dont_write_bytecode = True
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        with (out / "tests.log").open("w", encoding="utf-8") as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        report.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                      skipped=len(result.skipped), expected_failures=len(result.expectedFailures))
        report["status"] = "passed" if result.wasSuccessful() and not result.skipped and not result.expectedFailures else "failed"
    except Exception as exc:
        report.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (out / "test-result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Clean-checkout synthetic test status:", report["status"])
    print("Tests:", report.get("tests_run", 0), "Failures:", report.get("failures", 0), "Errors:", report.get("errors", 0), "Skipped:", report.get("skipped", 0))
    print("Receipt:", out / "test-result.json")
    print("Log:", out / "tests.log")
    if report.get("error"):
        print(report["error"])
    print("This test does not validate real models, native desktop behavior or fresh scanner dependency installation.")
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
