# Public v1 release instructions

**Status: public-facing candidate on private `main`, awaiting approval of its exact SHA before public visibility or tagging.** The assisted Windows walkthrough passed. An independent guide-only install remains unverified.

## Repository identity

- Repository: `anthfuller/garak-mitre-atlas-agent`
- Clone URL: `https://github.com/anthfuller/garak-mitre-atlas-agent.git`
- README title: **Garak Evidence for the MITRE ATLAS Agent**
- GitHub description: Investigate Garak detector flags with the MITRE ATLAS Agent in Langflow. Review candidate technique mappings and search saved evidence locally with Chroma and EmbeddingGemma.
- License: MIT; retain `Copyright (c) 2026 Garak Playbook contributors` unless the owner explicitly approves a replacement.

Keep this repository private until owner approval of the exact release commit. The repository name identifies an integration, not an official MITRE project or endorsement. Private `main` must contain the same sanitized files intended for public release.

## What ships

Windows PowerShell operation; fourteen selectable Garak probes; optional batch execution; separate Ollama and OpenAI results; original evidence/settings and concise ATLAS handoffs; confirmed submission to the researcher's configured MITRE ATLAS Agent in Langflow over authenticated MCP; analysis and a checked full Kumu URL in the same reply; optional separate graph follow-up; and optional explicit Chroma indexing with local EmbeddingGemma. A setup helper prepares the separately downloaded MITRE flow with the tested Responses component. The agent, upstream flow, dataset and model credentials are not bundled. The 177 remaining installed probe IDs, AVID export/integration and broader research features are deferred.

For `gpt-5.6-sol`, Ascii85, Base32 and Base64 use a tested 20000-token allowance. Other probe/model defaults and explicit operator overrides retain their documented behavior. Historical 1500-token baselines remain gaps alongside the successful retests. The Ollama DAN failed attempt remains disclosed. See [compatibility](compatibility.md).

## No-Git and release-attachment boundary

Use `docs/public-file-list.txt` as the allowlist for the final tracked tree and every path in history reachable from the release branch. Review historical blob contents and commit metadata as well as current files. `.gitignore` cannot remove content already tracked.

Anything marked `NOGIT` or private must stay outside Git **and GitHub release attachments**, including:

- Outer candidate/review ZIPs, Git bundles and `PRIVATE-REVIEW/`.
- Raw receipts/logs, real prompts/responses, original comparisons, run/attempt IDs and private evidence references.
- Private configurations, credentials, private service/project endpoints and personal filesystem paths.
- Chroma databases, model weights/downloads and local environments.

Reviewed generic configuration examples, placeholder/loopback endpoints, synthetic fixtures and their identifiers, source/evidence hashes, approved cropped illustrations and the sanitized worked example are allowed. The default Kumu project and map are public values from MITRE's pinned flow, not private Langflow endpoints. Public validation summaries can identify the validated source commits and accurately report results; the underlying private receipts remain outside Git. Do not attach a private review package to a release. No custom release attachment is needed for v1; GitHub's source archive should contain only the approved tracked tree.

## Maintainer sequence

1. Prepare the candidate on private `main`; preserve the working lab and private evidence. Record its exact commit with `git rev-parse HEAD`. Use the [release record](release-v1.md) to reconcile the real code changes after `4fedd3f`: reply formatting, the prepared-flow helper, and inline Kumu submission/validation. Only this final documentation preparation is documentation-only relative to `373ba13`.
2. Carry forward the scoped Windows checks at `09e8128` and `4fedd3f`, the later targeted offline results, and the assisted Windows walkthrough including the observed inline Kumu finish line. State that an independent guide-only install remains unverified. Do not relabel an older full-suite pass as a pass for later code. No dependency reinstall, model scan or paid call is required for these documentation edits.
3. Check the final tracked tree and reachable history against the allowlist and privacy rules. Retain the check result privately and report any qualification. Preserve failures and baseline gaps in the published compatibility table.
4. Commit only the reviewed changes to the existing private `main`. Verify the exact head, tree and reachable refs before requesting public visibility. Do not push unrelated refs or use `--mirror`.
5. Return the exact candidate SHA, short diff summary and public-file/history check result. Stop for owner publication and tag approval.
6. Only after approval, make the reviewed repository public and tag the approved commit `v1.0.0`. Release notes must state the fourteen-probe scope, model-specific results, Ollama DAN limitation, validation boundaries and deferred features. Do not include excluded material in release attachments.

[Install on Windows and open your first ATLAS reply](install-and-verify.md) · [Release validation](release-v1.md) · [Maintainer Windows checks](clean-windows.md) · [Worked example](worked-example.md) · [Third-party notices](../THIRD_PARTY.md)
