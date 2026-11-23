"""Create new private paths/configuration outside this checkout; no installs or network calls."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def configure(data_root, garak_python, research_python=None, ollama_model="llama3.2:3b", openai_model=None):
    data_root = Path(data_root).expanduser().resolve()
    if data_root.is_relative_to(ROOT):
        raise ValueError("Data root must be outside the source checkout.")
    for executable in (garak_python, research_python):
        if executable and not Path(executable).is_file():
            raise ValueError("Python executable does not exist: " + str(executable))
    targets = {"ollama-local": {"provider": "ollama", "model": ollama_model, "endpoint": "http://127.0.0.1:11434"}}
    if openai_model:
        targets["openai-reasoning"] = {"provider": "openai", "model": openai_model, "endpoint": "https://api.openai.com/v1"}
    private = data_root / "garak-playbook-private"
    files = {private / "config.private.json": {
        "schema_version": 1, "garak_python": str(Path(garak_python).absolute()),
        "evidence_root": str(data_root / "evidence"), "xdg_data_home": str(data_root / "artifacts"), "targets": targets}}
    if research_python:
        files[private / "research.private.json"] = {
            "schema_version": 1, "python": str(Path(research_python).absolute()), "storage_root": str(data_root / "research"),
            "ollama_endpoint": "http://127.0.0.1:11434", "embedding_model": "embeddinggemma:latest"}
    if any(path.exists() for path in files):
        raise ValueError("Configuration already exists; no existing file will be overwritten.")
    private.mkdir(parents=True, exist_ok=True)
    for path, value in files.items():
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, indent=2) + "\n")
        print("Created private configuration:", path)
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ["LOCALAPPDATA"]) / "GarakPlaybook" if os.environ.get("LOCALAPPDATA") else None
    p.add_argument("--data-root", type=Path, default=default, required=default is None)
    p.add_argument("--garak-python", type=Path, required=True)
    p.add_argument("--research-python", type=Path)
    p.add_argument("--ollama-model", default="llama3.2:3b")
    p.add_argument("--openai-model")
    args = p.parse_args()
    try:
        configure(args.data_root, args.garak_python, args.research_python, args.ollama_model, args.openai_model)
    except (ValueError, OSError) as exc:
        p.exit(2, "Configuration failed: " + str(exc) + "\n")
    print("No target requests or installations. Model access remains unverified.")


if __name__ == "__main__":
    main()
