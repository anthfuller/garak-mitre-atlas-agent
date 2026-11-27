"""Prepare a local import copy of the pinned MITRE flow; no network or model calls."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

UPSTREAM_COMMIT = "b2bca6438e99cb72752c27be1728f062b6f943ca"
UPSTREAM_SHA256 = "5cafce47d806100d80e76a1cf3390124e605183514e6ed22a3c8aaa385512f39"
OLD_PARAMETER = '"temperature": self.temperature if self.temperature is not None else 0.1,'
NEW_PARAMETERS = '"use_responses_api": True,\n            "reasoning_effort": "medium",'


def prepare(document):
    """Retain upstream tools/instructions/wires and apply the tested client edit."""
    flow = copy.deepcopy(document)
    models = [n for n in flow["data"]["nodes"] if n["data"]["type"] == "vLLMModel"]
    if len(models) != 1:
        raise ValueError("Expected one vLLM model component.")
    model = models[0]["data"]["node"]
    template = model["template"]
    code = template["code"]["value"]
    if code.count(OLD_PARAMETER) != 1:
        raise ValueError("The model component does not match the tested version.")
    template["code"]["value"] = code.replace(OLD_PARAMETER, NEW_PARAMETERS)
    template["model_name"]["value"] = "gpt-6.1-sol"
    template["api_base"]["value"] = "https://api.openai.com/v1"
    template["api_key"]["value"] = ""
    template["api_key"]["load_from_db"] = False
    template["model_kwargs"]["value"] = {}
    model["edited"] = True
    model.get("metadata", {}).pop("code_hash", None)
    # The original export's file bindings belong to its database, not this login.
    for node in flow["data"]["nodes"]:
        fields = node["data"]["node"].get("template", {})
        if node["data"]["type"] == "File":
            fields["path"]["file_path"] = []
            fields["path"]["value"] = ""
        elif node["data"]["type"] == "CSVPythonREPL":
            fields["csv_file"]["file_path"] = ""
            fields["csv_file"]["value"] = ""
    return flow


def prepare_file(source, output):
    raw = source.read_bytes()
    document = json.loads(raw)
    # Accept equivalent JSON indentation/line endings, but no changed values.
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != UPSTREAM_SHA256:
        raise ValueError(f"Source flow differs from MITRE revision {UPSTREAM_COMMIT}; no output written.")
    prepared = prepare(document)
    content = (json.dumps(prepared, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if output.exists():
        if output.read_bytes() != content:
            raise ValueError("Output already exists with different content; preserve it. No files replaced.")
    else:
        with output.open("xb") as stream:
            stream.write(content)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        output = prepare_file(args.source, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, "Flow preparation failed: " + str(error) + "\n")
    print("Ready to import:", output)
    print("Model: gpt-6.1-sol; OpenAI Responses API; medium reasoning; temperature omitted.")
    print("No API key stored. Select the three contract files and dataset CSV after import.")
    print("The upstream flow and any existing Langflow database are unchanged.")


if __name__ == "__main__":
    main()
