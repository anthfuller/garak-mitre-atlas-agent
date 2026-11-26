# Public v1 release instructions

**Current status: unpublished v1.0.0 candidate.** No v1.0.0 tag exists. The accompanying candidate receipt names the exact commit and bundle hash. See [changes and validation](release-v1.md) for the carried Windows pass at `09e8128`, later diagnostic evidence and candidate-specific checks.

## What ships

Windows PowerShell operation; fourteen selectable Garak probes; optional batch execution; separate Ollama and OpenAI results; preserved evidence/settings and concise ATLAS handoffs; optional confirmed ATLAS MCP submission; separate Kumu requests; and optional explicit Chroma indexing with local EmbeddingGemma. The 177 remaining installed probe IDs, live AVID integration and broader research features are deferred.

For `gpt-5.6-sol`, Ascii85, Base32 and Base64 use a tested 20000-token allowance. Other probe/model defaults and explicit operator overrides retain their documented behavior. Historical 1500-token baselines remain gaps, alongside the successful retests. The Ollama DAN failed attempt remains disclosed. See [compatibility](compatibility.md).

## Maintainer sequence

1. Review the candidate receipt, source and private validation evidence. Carry forward the earned Windows installation/checkout checkpoint; do not rerun installations solely to repeat evidence. Use the targeted delta helper when confirming the new profile/CLI changes on Windows. Its receipt is distinct from the original full validation.
2. Confirm the final compatibility table against the private alias map, preserving failed executions, baseline gaps and retest settings. The current task authorizes this fourteen-probe v1 scope and retains the Ollama DAN exception.
3. Review tracked source and reachable Git history. Only source, explicitly synthetic fixtures and sanitized examples/documentation belong in Git. Keep the package's `PRIVATE-REVIEW` directory, real evidence, keys, endpoints, local paths and original IDs outside the checkout and repository.
4. Confirm the MIT license copyright attribution, third-party notices, repository owner/name and publication approval. The candidate displays `1.0.0`; the eventual tag must point to the approved commit with matching version.
5. After authorization, create the agreed empty repository, push only the reviewed branch and inspect it before public visibility. The local bundle contains that branch and its reviewed ancestors; it is not a published GitHub repository. Do not push private package folders or `--mirror` unrelated refs.
6. Publish and tag `v1.0.0` only after the owner's explicit publication approval. Release notes must state the fourteen-probe support scope, model-specific results, Ollama DAN limitation, carried versus new validation, and deferred features.

[Windows quick start](../README.md#windows-quick-start) · [Clean Windows validation](clean-windows.md) · [Worked example](worked-example.md) · [Third-party notices](../THIRD_PARTY.md)
