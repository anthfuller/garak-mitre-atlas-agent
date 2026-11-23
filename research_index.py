"""Optional local research index. Originals remain outside Chroma; no scanning or MCP calls."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit
import uuid

import atlas_mcp as a
import kumu_mcp as k

VERSION = "0.5.0"
COLLECTION = "garak_research_runs_v1"
OWNER = {"application": "garak-playbook-research", "schema_version": 1}
ROOT = Path(__file__).resolve().parent
LIMITATIONS = [
    "Detector flags are observations, not confirmed attack success; gaps are not passes.",
    "ATLAS analysis is unreviewed. Mentioned IDs may include rejected/background examples.",
    "Graph-selected mappings remain candidates. Internal ATLAS tool verification is agent-reported.",
    "The search document is a bounded sample, not the full transcripts or ATLAS analysis.",
    "Similarity and metadata filters are research conveniences, not authorization enforcement.",
    "Retrieval from one indexed run establishes connectivity, not ranking quality.",
]


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def save_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = encoded(value)
    try:
        with path.open("xb") as f:
            f.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError("Existing immutable research revision differs: " + str(path))


def load_config(path):
    cfg = a.read_json(path)
    if set(cfg) != {"schema_version", "python", "storage_root", "ollama_endpoint", "embedding_model"} or cfg["schema_version"] != 1:
        raise ValueError("Research config requires schema_version, python, storage_root, ollama_endpoint, embedding_model.")
    for field in ("python", "storage_root"):
        if not isinstance(cfg[field], str) or not cfg[field]:
            raise ValueError("Missing research config field: " + field)
        expanded = Path(os.path.expandvars(cfg[field])).expanduser()
        if not expanded.is_absolute():
            raise ValueError(field + " must resolve to an absolute path.")
        # Preserve a virtual environment interpreter symlink: resolving it can
        # select the system Python and lose that environment's dependencies.
        cfg[field] = str(expanded.absolute() if field == "python" else expanded.resolve())
        if "%" in cfg[field] or "$" in cfg[field]:
            raise ValueError("Unresolved environment variable in " + field)
    if not Path(cfg["python"]).is_file():
        raise ValueError("Configured Chroma Python does not exist: " + cfg["python"])
    storage = Path(cfg["storage_root"])
    if storage.is_relative_to(ROOT) or ROOT.is_relative_to(storage):
        raise ValueError("Research storage must be separate from the public source directory.")
    u = urlsplit(cfg["ollama_endpoint"])
    if (u.scheme != "http" or u.hostname not in ("localhost", "127.0.0.1", "::1")
            or u.username or u.password or u.path not in ("", "/") or u.query or u.fragment):
        raise ValueError("Embedding endpoint must be HTTP loopback without credentials, path or query.")
    cfg["ollama_endpoint"] = cfg["ollama_endpoint"].rstrip("/")
    if cfg["embedding_model"] != "embeddinggemma:latest":
        raise ValueError("This release supports the explicit embeddinggemma:latest tag; its digest is pinned per collection.")
    return cfg


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Local embedding endpoint attempted a redirect; stopped.")


class Ollama:
    def __init__(self, cfg):
        self.endpoint = cfg["ollama_endpoint"]
        self.model = cfg["embedding_model"]
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.requests = []
        self.version = None

    def call(self, route, body=None):
        data = encoded(body) if body is not None else None
        request = urllib.request.Request(self.endpoint + route, data=data, headers={"Content-Type": "application/json"})
        with self.opener.open(request, timeout=180) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Ollama response exceeds size limit.")
        result = json.loads(raw)
        self.requests.append({"route": route, "prompt_eval_count": result.get("prompt_eval_count")})
        return result

    def identity(self):
        if self.version is None:
            self.version = self.call("/api/version").get("version")
            if not isinstance(self.version, str) or not self.version:
                raise ValueError("Ollama version could not be recorded.")
        tags = self.call("/api/tags")
        matches = [x for x in tags.get("models", []) if x.get("name") == self.model or x.get("model") == self.model]
        if len(matches) != 1 or not re.fullmatch(r"[a-fA-F0-9]{64}", matches[0].get("digest", "")):
            raise ValueError("Installed EmbeddingGemma tag/digest could not be established. No model will be downloaded.")
        return {"model": self.model, "digest": matches[0]["digest"], "endpoint": self.endpoint, "ollama_version": self.version,
                "embedding_policy": "explicit_api_embed_raw_text_truncate_false_v1"}

    def embed(self, text):
        # Never permit silent truncation or implicit Chroma embedding downloads.
        result = self.call("/api/embed", {"model": self.model, "input": text, "truncate": False})
        vectors = result.get("embeddings")
        if (result.get("model") != self.model or not isinstance(vectors, list) or len(vectors) != 1
                or not isinstance(vectors[0], list) or not vectors[0]
                or any(type(x) not in (int, float) or not math.isfinite(x) for x in vectors[0])
                or not any(x != 0 for x in vectors[0])):
            raise ValueError("Invalid embedding model, dimensions or values returned by Ollama.")
        return vectors[0]


@contextmanager
def owned_store(root, create=False):
    marker = root / "research-store.json"
    if not marker.exists():
        if not create:
            raise ValueError("Research store has not been initialized by an index command.")
        if root.exists() and any(root.iterdir()):
            raise ValueError("Refusing to adopt a nonempty directory. Select a NEW dedicated research storage path.")
        root.mkdir(parents=True, exist_ok=True)
        save_new(marker, OWNER)
    if a.read_json(marker) != OWNER:
        raise ValueError("Unrecognized research-store ownership marker.")
    for name in ("chroma", "records", "receipts", "research-store.json", ".research.lock"):
        if (root / name).is_symlink():
            raise ValueError("Research storage contains a redirected path: " + name)
    lock = root / ".research.lock"
    try:
        handle = lock.open("x")
    except FileExistsError:
        raise ValueError("Research store is busy (or a previous process left .research.lock); do not run concurrent index/search commands.") from None
    try:
        with handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def ref(path, kind):
    path = Path(path).resolve(strict=True)
    return {"kind": kind, "path": str(path), "sha256": a.file_hash(path)}


def archive_refs(folder, kind):
    index = a.read_json(folder / "checksums.json", 8 * 1024 * 1024)
    if not isinstance(index, dict) or not index:
        raise ValueError("Missing archive checksum inventory.")
    refs = []
    for name, digest in sorted(index.items()):
        if Path(name).is_absolute() or ".." in Path(name).parts or name in (".", "..") or not (folder / name).resolve().is_relative_to(folder):
            raise ValueError("Invalid archive file reference.")
        item = ref(folder / name, kind)
        if item["sha256"] != digest:
            raise ValueError("Archive checksum mismatch: " + name)
        refs.append(item)
    refs.append(ref(folder / "checksums.json", kind))
    return refs


def unchanged(refs):
    return all(Path(x["path"]).is_file() and a.file_hash(Path(x["path"])) == x["sha256"] for x in refs)


def prepare_record(args):
    import playbook as p
    run, _, _, summary, hashes = a.load_run(args.run_dir, p.analyze)
    _, observations = p.analyze(run / "scan.report.jsonl", a.read_json(run / "manifest.json"))
    probes = list(dict.fromkeys(row["probe"] for row in summary["detectors"]))
    if len(probes) != 1:
        raise ValueError("This research release indexes one-probe runner reports; no probe was selected or multiple probes were found.")
    refs = archive_refs(run, "garak_original")
    atlas = None
    graph = None
    candidate_context = ""
    if args.atlas_submission:
        folder = k.choose_submission(run, args.atlas_submission)
        saved, text, _ = k.load_submission(folder, summary, hashes)
        mentioned, contexts = k.mentioned_ids(text)
        atlas = {"submission_id": saved["submission_id"], "folder": str(folder), "status": saved["status"],
                 "review_status": "unreviewed", "mentioned_ids": mentioned,
                 "mapping_status": "mentions_not_automatically_accepted_mappings"}
        refs += archive_refs(folder, "atlas_unreviewed")
        candidate_context = "\nATLAS unreviewed mention excerpts (first five IDs, first context, 240 characters each; may include rejected mappings):\n" + "\n".join(
            x + ": " + contexts[x][0][:240] for x in mentioned[:5])
    if args.graph_dir:
        if not atlas or not args.graph_validation:
            raise ValueError("A graph link requires --atlas-submission and its existing --graph-validation file.")
        folder = Path(args.graph_dir).resolve(strict=True)
        if folder.parent != run / "kumu-submissions":
            raise ValueError("Graph archive is outside the selected run.")
        gr = a.read_json(folder / "submission.json")
        validation_path = Path(args.graph_validation).resolve(strict=True)
        if validation_path.parent.parent != run / "kumu-validations":
            raise ValueError("Graph validation is outside the selected run.")
        validation = a.read_json(validation_path)
        refs += archive_refs(folder, "kumu_archive") + archive_refs(validation_path.parent, "kumu_validation")
        if (gr.get("run_id") != summary["garak_run_id"] or gr.get("source_submission_id") != atlas["submission_id"]
                or validation.get("run_id") != summary["garak_run_id"]
                or Path(validation.get("graph_archive", "")).resolve() != folder
                or validation.get("status") != "validation_passed" or validation.get("source_files_unchanged") is not True
                or validation.get("selected_ids") != gr.get("selected_ids")):
            raise ValueError("Graph/validation is not a passing, preserved reference for this run and ATLAS submission.")
        for name, digest in validation.get("graph_files_sha256", {}).items():
            if Path(name).name != name or a.file_hash(folder / name) != digest:
                raise ValueError("Graph changed since its recorded offline validation.")
        obj, _ = k.validate_graph(a.read_json(folder / "response.json", 64 * 1024 * 1024),
                                  summary["garak_run_id"], gr["selected_ids"], target=validation["expected_target"])
        graph = {"url": obj["graph_result"]["url"], "selected_ids": gr["selected_ids"],
                 "mapping_status": "candidate_pending_analyst_review", "scope": k.GRAPH_SCOPE,
                 "url_validation": "matches_expected_target_recorded_in_saved_validation",
                 "browser_rendering": "not_independently_verified_by_indexer",
                 "internal_tool_verification": "agent_reported"}
    elif args.graph_validation:
        raise ValueError("--graph-validation requires --graph-dir.")
    for image in args.screenshot or []:
        path = Path(image).resolve(strict=True)
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError("Screenshot references must use PNG/JPEG/WebP files.")
        refs.append(ref(path, "operator_supplied_screenshot_not_analyzed"))
    document = p.build_atlas_handoff(summary, observations) + candidate_context
    # Prevent unpredictable overlong embeddings; original evidence is never shortened.
    if len(document) > 12000:
        raise ValueError("Research search document exceeds 12,000 characters; needs an explicit future chunking policy.")
    evaluated = sum(any(v["disposition"] in ("flagged", "not_flagged") for v in o["detector_results"].values()) for o in observations)
    record = {"schema_version": 1, "record_type": "research_run", "run_id": summary["garak_run_id"],
              "run_directory": str(run), "model": summary["target_model"], "probe": probes[0],
              "execution_status": summary["execution_status"], "summary": summary,
              "evaluated_response_count": evaluated, "flagged_response_count": summary["flagged_response_count"],
              "review_status": "unreviewed", "attack_success": "unverified", "legitimate_task_completion": "not_assessed",
              "atlas": atlas, "graph": graph, "evidence_references": refs, "limitations": LIMITATIONS,
              "search_document": document, "document_policy": "existing_handoff_plus_bounded_unreviewed_ATLAS_mentions_v1"}
    if not unchanged(refs):
        raise ValueError("Evidence changed during preparation; no index write.")
    return record


def client(cfg):
    if importlib.metadata.version("chromadb") != "1.5.9":
        raise ValueError("This release requires chromadb==1.5.9 in the configured research interpreter; no automatic upgrade.")
    import chromadb
    from chromadb.config import Settings
    return chromadb.PersistentClient(path=str(Path(cfg["storage_root"]) / "chroma"),
                                     settings=Settings(anonymized_telemetry=False, allow_reset=False))


def collection(db, identity, create):
    names = [c.name for c in db.list_collections()]
    expected = {"application": OWNER["application"], "schema_version": 1, "embedding_model": identity["model"],
                "embedding_digest": identity["digest"], "embedding_policy": identity["embedding_policy"]}
    if COLLECTION not in names:
        if not create:
            raise ValueError("Research collection does not exist; index one run first.")
        return db.create_collection(COLLECTION, embedding_function=None, metadata=expected,
                                    configuration={"hnsw": {"space": "cosine"}})
    c = db.get_collection(COLLECTION, embedding_function=None)
    if c.metadata != expected:
        raise ValueError("Collection ownership or embedding digest/policy differs. Use a new dedicated store; no automatic migration.")
    return c


def receipt(root, value):
    folder = root / "receipts"
    path = folder / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8] + ".json")
    save_new(path, {"runner_version": VERSION, "created_at": a.now(), "python_version": sys.version,
                    "chroma_version": importlib.metadata.version("chromadb"), **value})
    print("Research receipt:", path)
    return path


def index(args, cfg):
    record = prepare_record(args)
    root = Path(cfg["storage_root"])
    run = Path(record["run_directory"])
    if root.is_relative_to(run) or run.is_relative_to(root):
        raise ValueError("Research storage and original run evidence must be separate directories.")
    ollama = Ollama(cfg)
    with owned_store(root, create=True):
        identity = ollama.identity()
        db = client(cfg)
        c = collection(db, identity, True)
        revision = a.digest(encoded(record))
        row_id = "run:" + record["run_id"]
        record_folder = root / "records" / a.digest(record["run_id"].encode())
        snapshot = record_folder / (revision + ".json")
        meta = {"run_id": record["run_id"], "model": record["model"], "probe": record["probe"],
                "execution_status": record["execution_status"], "evaluated": record["evaluated_response_count"],
                "flags": record["flagged_response_count"], "review_status": "unreviewed",
                "revision": revision, "record_path": str(snapshot), "embedding_digest": identity["digest"]}
        previous = c.get(ids=[row_id], include=["documents", "metadatas"])
        before = c.count()
        status = "unchanged"
        vector = None
        if previous["ids"]:
            old = previous["metadatas"][0]
            old_path = Path(old["record_path"])
            if old_path.parent != record_folder or a.file_hash(old_path) != old["revision"]:
                raise ValueError("Previous research revision is missing or changed; no replacement.")
        same = previous["ids"] and previous["metadatas"][0] == meta and previous["documents"][0] == record["search_document"]
        if not same:
            vector = ollama.embed(record["search_document"])
            if ollama.identity() != identity or not unchanged(record["evidence_references"]):
                raise ValueError("Embedding model or evidence changed before insertion; stopped.")
            save_new(snapshot, record)
            c.upsert(ids=[row_id], documents=[record["search_document"]], embeddings=[vector], metadatas=[meta])
            status = "updated_revision" if previous["ids"] else "indexed"
        check = c.get(ids=[row_id], include=["documents", "metadatas"])
        if check["ids"] != [row_id] or check["documents"] != [record["search_document"]] or check["metadatas"] != [meta]:
            raise ValueError("Chroma exact read-back failed.")
        preserved = unchanged(record["evidence_references"])
        after = c.count()
        expected = before + int(not previous["ids"])
        value = {"action": "research-index", "status": status if preserved and after == expected else "verification_failed",
                 "run_id": record["run_id"], "record_id": row_id, "revision": revision,
                 "record_path": str(snapshot), "collection": COLLECTION, "collection_count_before": before,
                 "collection_count_after": after, "expected_count_after": expected, "exact_read_back": True,
                 "original_evidence_unchanged": preserved, "embedding": identity,
                 "embedding_dimensions": len(vector) if vector else None, "local_requests": ollama.requests,
                 "cloud_requests": 0, "new_scans": 0}
        receipt(root, value)
        if value["status"] == "verification_failed":
            raise ValueError("Post-index preservation/count check failed; inspect receipt before trusting this index entry.")
        print("Research index:", status)
        print("Run ID:", record["run_id"])
        print(f"Evaluated responses: {meta['evaluated']}; detector-flagged responses: {meta['flags']}; execution: {meta['execution_status']}")
        print(f"Collection records: {before} -> {after}; exact read-back: PASSED; original evidence unchanged: {preserved}")
        print("Review status: unreviewed; attack success: unverified. No new scan or cloud request.")
    return 0


def filters(args):
    terms = [{name: {"$eq": value}} for name, value in (("model", args.model), ("probe", args.probe)) if value]
    return {"$and": terms} if len(terms) > 1 else (terms[0] if terms else None)


def read_record(root, metadata):
    path = Path(metadata["record_path"]).resolve(strict=True)
    if not path.is_relative_to(root / "records") or a.file_hash(path) != metadata["revision"]:
        raise ValueError("Research record path/hash verification failed.")
    return a.read_json(path, 32 * 1024 * 1024)


def search(args, cfg):
    root = Path(cfg["storage_root"])
    if not args.query.strip() or len(args.query) > 4000 or not 1 <= args.limit <= 20:
        raise ValueError("Use a nonempty query up to 4,000 characters and a result limit from 1 to 20.")
    ollama = Ollama(cfg)
    with owned_store(root):
        identity = ollama.identity()
        c = collection(client(cfg), identity, False)
        where = filters(args)
        matching = c.get(where=where, include=[])["ids"]
        result = {"ids": [[]], "metadatas": [[]], "distances": [[]]}
        if matching:
            vector = ollama.embed(args.query)
            if ollama.identity() != identity:
                raise ValueError("Embedding model changed during query.")
            result = c.query(query_embeddings=[vector], where=where, n_results=min(args.limit, len(matching)),
                             include=["metadatas", "distances"])
        output = []
        for row_id, meta, distance in zip(result["ids"][0], result["metadatas"][0], result["distances"][0]):
            record = read_record(root, meta)
            available = unchanged(record["evidence_references"])
            print(f"\nRun: {a.terminal_text(meta['run_id'])}; model: {a.terminal_text(meta['model'])}; probe: {a.terminal_text(meta['probe'])}")
            print(f"Execution: {meta['execution_status']}; evaluated: {meta['evaluated']}; flags: {meta['flags']}; cosine distance: {distance:.6f}")
            print("Review: unreviewed; attack success: unverified; evidence hashes match:", available)
            print("Evidence folder:", record["run_directory"])
            for item in record["evidence_references"]:
                if Path(item["path"]).name in ("summary.json", "scan.report.jsonl", "atlas_response.md", "kumu_url.txt") or item["kind"].startswith("operator_"):
                    print("  " + a.terminal_text(item["kind"] + ": " + item["path"]))
            output.append({"record_id": row_id, "revision": meta["revision"], "distance": distance,
                           "source_hashes_match": available, "run_id": meta["run_id"]})
        print(f"\nFound {len(output)} of {len(matching)} matching indexed runs. Similarity is not a security verdict.")
        receipt(root, {"action": "research-search", "query": args.query, "filters": where, "results": output,
                       "embedding": identity, "local_requests": ollama.requests, "cloud_requests": 0, "new_scans": 0})
    return 0


def open_evidence(args, cfg):
    root = Path(cfg["storage_root"])
    with owned_store(root):
        db = client(cfg)
        c = db.get_collection(COLLECTION, embedding_function=None)
        found = c.get(ids=["run:" + args.run_id], include=["metadatas"])
        if not found["ids"]:
            raise ValueError("Run ID not indexed.")
        record = read_record(root, found["metadatas"][0])
        names = {"summary": "summary.json", "report": "scan.report.jsonl", "atlas": "atlas_response.md", "kumu-url": "kumu_url.txt"}
        matches = [x for x in record["evidence_references"] if Path(x["path"]).name == names[args.evidence]]
        if len(matches) != 1 or not unchanged(matches):
            raise ValueError("Requested evidence is missing, ambiguous or changed; no editor opened.")
        if os.name != "nt":
            raise ValueError("Notepad opening requires Windows. Evidence: " + matches[0]["path"])
        editor = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "notepad.exe"
        subprocess.Popen([str(editor), matches[0]["path"]], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        print("Opened original evidence in Notepad:", matches[0]["path"])
    return 0


def add_parsers(sub):
    for name in ("research-index", "research-search", "research-open"):
        p = sub.add_parser(name, help="Optional local Chroma research operation; no scan or cloud request.")
        p.add_argument("--research-config", type=Path, required=True)
        if name == "research-index":
            p.add_argument("--run-dir", type=Path, required=True)
            p.add_argument("--atlas-submission", type=Path)
            p.add_argument("--graph-dir", type=Path)
            p.add_argument("--graph-validation", type=Path)
            p.add_argument("--screenshot", type=Path, action="append")
        elif name == "research-search":
            p.add_argument("--query", required=True)
            p.add_argument("--model")
            p.add_argument("--probe")
            p.add_argument("--limit", type=int, default=5)
        else:
            p.add_argument("--run-id", required=True)
            p.add_argument("--evidence", choices=("summary", "report", "atlas", "kumu-url"), default="summary")


def launch(args, argv):
    cfg = load_config(args.research_config)
    env = os.environ.copy()
    for key in list(env):
        if key.upper().startswith(("OPENAI_", "ANTHROPIC_", "LANGFLOW_")) or key.upper() in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            env.pop(key)
    env.update(PYTHONIOENCODING="utf-8", ANONYMIZED_TELEMETRY="False")
    return subprocess.run([cfg["python"], str(Path(__file__).resolve()), *argv], env=env, check=False).returncode


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    p = argparse.ArgumentParser(description=__doc__)
    add_parsers(p.add_subparsers(dest="action", required=True))
    args = p.parse_args()
    try:
        cfg = load_config(args.research_config)
        return {"research-index": index, "research-search": search, "research-open": open_evidence}[args.action](args, cfg)
    except (ValueError, OSError, a.AtlasError, importlib.metadata.PackageNotFoundError) as exc:
        print("Research operation failed: " + a.terminal_text(str(exc)), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Research operation interrupted. Check the next exact read-back before treating indexing as complete.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
