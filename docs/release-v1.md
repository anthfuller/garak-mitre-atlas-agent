# v1.0.0 candidate: changes and validation

Status: finalized for `anthfuller/garak-mitre-atlas-agent`, pending owner publication and tag approval. `git rev-parse HEAD` identifies the exact candidate; the private release check records its SHA and diff from reviewed `4fedd3f`. The displayed version is 1.0.0 so the approved commit can receive the v1.0.0 tag without another code/version change.

## Carried evidence

The original Windows receipt passed at **09e812807924e9c55c9d96a507fe0beac637f752** on November 26, 2026. Its eleven checks include clone/version, full offline suite, resolved test/scanner inventories, public quick start, installed catalog, synthetic Ollama/OpenAI integrations, and batch success/auth-failure handling. The successful run reused the recorded environments from the earlier fresh installations, with requirements and package inventories checked. It did not perform a new dependency installation or any paid call. Clipboard/editor/browser behavior remained mocked.

This checkpoint remains earned. It is not represented as a full Windows pass for every later commit. Original receipt, prior environment reference, hashes and logs remain private.

The targeted Windows delta passed at **4fedd3f008088a408825a39ec284c5b3bbcdaf7e**, also on November 26, 2026. All seven expected checks returned exit code 0: clone, unchanged requirements, test-package inventory, release-profile tests, headroom tests, OpenAI tests and public quick-start CLI. The receipt's candidate SHA, delivered-bundle hash and prior-receipt hash matched the retained artifacts. It records no live model calls, paid calls or dependency installation. This is native Windows evidence for the delta, not a repeat of the full scanner installation/validation. The receipt was inspected; its separate native log files were not uploaded for independent inspection.

The same candidate passed 242 offline tests on Linux with zero failures, errors or skips, including Chroma 1.5.9, plus synthetic Garak integrations. Synthetic results do not establish model security or replace live compatibility evidence.

The later 0.6.5 paired headroom diagnostic was exercised on the operator's Windows lab: 99 OpenAI requests including compatibility; 96/96 scorable test responses; 16 recovered gaps; no newly unscorable answers. The supplied comparison supports these counts and usage. That is live workflow evidence for this diagnostic, not a new full-suite Windows receipt or proof of broad model security.

## Changes after 09e8128

| Change | Validation |
|---|---|
| Opt-in paired headroom diagnostic, exact request guard, source-preserving comparison | Offline unit tests; real Garak/SDK with synthetic responses and network denied, including stop/error handling; operator-supplied Windows live comparison |
| Offline estimator additionally returns the constructed messages for comparison | Actual Garak synthetic headroom integration verifies the exact 96-input order; existing normal paths remain covered by the regression suite |
| Published price record reverified; date-dependent test fixture updated | Cost tests and arithmetic reconciliation; no price value changed; expiry remains explicit |
| Release defaults: 20000 only for gpt-5.6-sol with Ascii85/Base32/Base64 | New tests check all 14 probes, other model IDs, historical/explicit overrides, menu campaign planning, batch defaults and unchanged Ollama settings; quick-start CLI check |
| Version, compatibility table, worked example, release/privacy instructions | Documentation and data consistency review against the supplied comparison and consolidated evidence; source/history review |
| Optional AVID export smoke | One attempt on the existing synthetic fixture. Missing `avidtools`; export not created. Deferred without troubleshooting, dependency changes or model calls |

Underlying receipts and logs remain private. Both Windows checkpoints are complete for their stated scope. The historical full validator and targeted helper remain available for reproducibility; neither needs to be rerun for these documentation-only changes.

## Final documentation changes after 4fedd3f

The README now leads with the MITRE ATLAS Agent in Langflow and uses the approved repository name, description, clone URL and brief personal-capacity disclaimer. Public setup and maintainer guidance no longer require the private review package. Release records carry both Windows checkpoints and distinguish them from the final documentation-only diff. No-Git rules apply to the full reachable history and GitHub release attachments, with ignore rules as an additional guard.

The final diff and internal documentation links/anchors are checked, and final tracked files plus reachable commit trees, blobs and metadata are reviewed against the allowlist and privacy rules. The approved GitHub URL is not proof of public availability before publication. Runtime source, tests, model settings, dependency files and the MIT license are byte-identical to `4fedd3f`; no new live scan or claim of new runtime validation is made.

## Release scope and remaining limits

- Fourteen enabled probes. OpenAI: fourteen completed model/probe pairs at the documented mixed allowances. Ollama: thirteen completed and the documented failed/unscored DAN attempt, closed for v1 by operator direction.
- All 177 other inventory IDs remain outside v1 support. No new live scans are required by this release-preparation task.
- Garak evidence and handoffs, authenticated ATLAS MCP, separate Kumu, and optional Chroma/EmbeddingGemma stay in scope. Existing live integration evidence is limited to the saved runs already exercised; no new ATLAS/Kumu/Chroma call was made for this candidate.
- R-01 research failure receipts and the broader research-record/search-quality roadmap remain disclosed deferrals. The narrow headroom comparison does not complete a general baseline/retest research system.
- The worked example omits private transcripts and cannot establish a confirmed vulnerability. Detector flags and candidate mappings require analyst review.
- Transitive dependencies are not fully locked across platforms. Model access and pricing can change. Exact scanned model labels are not guarantees of access for another user.
- The owner directed retaining the MIT license and `Copyright (c) 2026 Garak Playbook contributors`; any replacement requires separate confirmation. No external source/corpora/models are bundled. Product names identify integrations and do not imply affiliation or endorsement.

Publication and the `v1.0.0` tag require the owner's explicit approval of the final candidate and its disclosed boundaries. The approved destination is `anthfuller/garak-mitre-atlas-agent`; start private and change visibility only after approval. Documentation preparation does not authorize a repository upload, visibility change or tag.
