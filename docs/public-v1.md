# Maintainer release procedure

This page defines the source, evidence and decision boundaries for maintaining a release.

## Repository identity

- Repository: `anthfuller/garak-mitre-atlas-agent`
- Clone URL: `https://github.com/anthfuller/garak-mitre-atlas-agent.git`
- README title: **Garak Evidence for the MITRE ATLAS Agent**
- GitHub description: Investigate Garak detector flags with the MITRE ATLAS Agent in Langflow. Review candidate technique mappings and search saved evidence locally with Chroma and EmbeddingGemma.
- License: MIT; retain `Copyright (c) 2026 Garak Playbook contributors` with the full warranty disclaimer and limitation of liability.

The repository name identifies an integration, not an official MITRE project or endorsement.

## What ships

Windows PowerShell operation; fourteen selectable Garak probes; optional batch execution; separate Ollama and OpenAI results; original evidence/settings and concise ATLAS handoffs; operator-confirmed submission to the researcher's configured MITRE ATLAS Agent in Langflow over authenticated MCP; analysis and a checked full Kumu URL in the same reply; optional separate graph follow-up; and optional explicit Chroma indexing with local EmbeddingGemma. A setup helper prepares the separately downloaded MITRE flow with the tested Responses component. The agent, upstream flow, dataset and model credentials are not bundled. The 177 remaining installed probe IDs, AVID export/integration and broader research features are deferred.

For `gpt-5.6-sol`, Ascii85, Base32 and Base64 use a tested 20000-token allowance. Other probe/model defaults and explicit operator overrides retain their documented behavior. Historical 1500-token baselines remain gaps alongside the successful retests. The Ollama DAN failed attempt remains disclosed. See [compatibility](compatibility.md).

## No-Git and release-attachment boundary

Use `docs/public-file-list.txt` as the allowlist for the final tracked tree and every path in history reachable from the release branch. Review historical blob contents and commit metadata as well as current files. `.gitignore` cannot remove content already tracked.

Anything marked `NOGIT` or private must stay outside Git **and GitHub release attachments**, including:

- Outer candidate/review ZIPs, Git bundles and `PRIVATE-REVIEW/`.
- Raw receipts/logs, real prompts/responses, original comparisons, run/attempt IDs, actual submission archive identifiers (including those created from synthetic handoffs), and private evidence references.
- Private configurations, credentials, private service/project endpoints and personal filesystem paths.
- Chroma databases, model weights/downloads and local environments.

Reviewed generic configuration examples, placeholder/loopback endpoints, synthetic fixtures and their deliberately invented identifiers, source/evidence hashes, approved cropped illustrations and the sanitized worked example are allowed. The default Kumu project and map are public values from MITRE's pinned flow, not private Langflow endpoints. Public validation summaries can identify the validated source commits and accurately report results; the underlying private receipts remain outside Git. Do not attach a private review package to a release. No custom release attachment is needed for v1; GitHub's source archive should contain only the approved tracked tree.

## Maintainer sequence

1. Reconcile the actual code changes and evidence in the [release record](release-v1.md). Identify exactly which source commit each test covered. The assisted Windows walkthrough passed; an independent guide-only installation remains unverified. Do not relabel an older Windows pass as a pass for later code.
2. Inspect the final tracked tree, every reachable historical path/blob and commit metadata against the allowlist and privacy rules. Report exceptions rather than treating a current-file deletion as removal from history. Preserve the baseline gaps, failed probes and research deferrals.
3. Commit the intended changes to `main`, preserving intervening work. Record the exact SHA with `git rev-parse HEAD` and verify the tree and reachable refs. Keep private receipts, evidence and review artifacts outside Git; do not push unrelated refs or use `--mirror`.
4. Provide the exact SHA, change summary and tree/history check result to the repository owner. Public visibility and version tagging are separate owner decisions: obtain explicit approval of the exact SHA for each action before performing it. Keep the repository private until visibility is approved; create a version tag only when tagging is approved. A Git history rewrite also requires separate owner approval.
5. Release notes must state the fourteen-probe scope, model-specific results, Ollama DAN limitation, validation boundaries and deferred features. GitHub's source archive must contain only the intended tracked files; excluded evidence must not appear in release attachments.

[Install on Windows and open your first ATLAS reply](install-and-verify.md) · [Release validation](release-v1.md) · [Maintainer Windows checks](clean-windows.md) · [Worked example](worked-example.md) · [Third-party notices](../THIRD_PARTY.md)
