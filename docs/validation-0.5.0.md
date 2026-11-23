# 0.5.0 build validation

Historical build record, not the current candidate's test result. The new candidate's exact-commit receipt is supplied outside the source bundle; later operator reports and release gates are tracked separately.

**165 automated tests passed**, including 14 research-index tests, in 27.319 seconds on Linux/Python 3.12. The complete suite ran in an isolated interpreter with real `chromadb==1.5.9`. The operator's environments were not modified.

Command:

```text
python -m unittest discover -s tests -v
```

Chroma tests use synthetic native Garak evidence, synthetic ATLAS/Kumu archives and deterministic synthetic embedding vectors. They exercise real database persistence, exact document/metadata read-back, repeat indexing without duplicates or a second embedding call, retained revisions, separate and combined metadata filters, mismatched source/graph rejection, model-digest mismatch, missing evidence, and refusal to adopt a preexisting unowned directory. The actual runner/worker CLI subprocess path passed against a fake loopback Ollama HTTP server. This is not a real EmbeddingGemma retrieval-quality test.

The synthetic incomplete run retained its exact 31 evaluated responses, 28 flags and one unscorable response. Its execution remained `complete_with_gaps`; attack success stayed unverified. No synthetic result is reported as a real model finding.

Notepad opening and Windows process flags are mocked. Native Windows validation and real local EmbeddingGemma indexing/search remain pending. The full native operator run, graph response and validation archive were not available in the build environment; the index performs their reconciliation on the operator's machine. No paid API request or real model scan occurred in these tests.

Source comparison confirmed byte-identical ATLAS/MCP, Kumu, OpenAI helpers, campaign settings and probe policy. AST comparison confirmed unchanged scan execution, preflight, native analysis, handoff rendering/regeneration, result menu, target menu and probe browser functions. Runner changes add the optional research import/CLI dispatch and version label.

Public-source packaging excludes private configuration, credentials, original evidence, databases and environment directories. Historical patch instructions containing lab-specific paths were replaced with generic examples. A complete clean Windows checkout deployment test and public GitHub release remain pending.
