# Public v1 release instructions

**Status: finalized candidate awaiting publication and tag approval.** No public release or tag is authorized by document preparation.

## Repository identity

- Repository: `anthfuller/garak-mitre-atlas-agent`
- Clone URL: `https://github.com/anthfuller/garak-mitre-atlas-agent.git`
- README title: **Garak Evidence for the MITRE ATLAS Agent**
- GitHub description: Investigate Garak detector flags with the MITRE ATLAS Agent in Langflow. Review candidate technique mappings and search saved evidence locally with Chroma and EmbeddingGemma.
- License: MIT; retain `Copyright (c) 2026 Garak Playbook contributors` unless the owner explicitly approves a replacement.

Begin with a private repository. Visibility becomes public only after owner approval of the exact release commit. The repository name identifies an integration, not an official MITRE project or endorsement. A private staging upload, if authorized, must contain exactly the same sanitized files intended for public release.

## What ships

Windows PowerShell operation; fourteen selectable Garak probes; optional batch execution; separate Ollama and OpenAI results; original evidence/settings and concise ATLAS handoffs; confirmed submission to the researcher's configured MITRE ATLAS Agent in Langflow over authenticated MCP; separate Kumu requests; and optional explicit Chroma indexing with local EmbeddingGemma. The agent, flow and model credentials are supplied separately by the researcher. The 177 remaining installed probe IDs, AVID export/integration and broader research features are deferred.

For `gpt-5.6-sol`, Ascii85, Base32 and Base64 use a tested 20000-token allowance. Other probe/model defaults and explicit operator overrides retain their documented behavior. Historical 1500-token baselines remain gaps alongside the successful retests. The Ollama DAN failed attempt remains disclosed. See [compatibility](compatibility.md).

## No-Git and release-attachment boundary

Use `docs/public-file-list.txt` as the allowlist for the final tracked tree and every path in history reachable from the release branch. Review historical blob contents and commit metadata as well as current files. `.gitignore` cannot remove content already tracked.

Anything marked `NOGIT` or private must stay outside Git **and GitHub release attachments**, including:

- Outer candidate/review ZIPs, Git bundles and `PRIVATE-REVIEW/`.
- Raw receipts/logs, real prompts/responses, original comparisons, run/attempt IDs and private evidence references.
- Private configurations, credentials, private service/project endpoints and personal filesystem paths.
- Chroma databases, model weights/downloads and local environments.

Reviewed generic configuration examples, placeholder/loopback endpoints, synthetic fixtures, source hashes and the sanitized worked example are allowed. Public validation summaries can identify the validated source commits and accurately report results; the underlying private receipts remain outside Git. Do not attach a private review package to a release. No custom release attachment is needed for v1; GitHub's source archive should contain only the approved tracked tree.

## Maintainer sequence

1. Start from reviewed `4fedd3f` in a separate checkout; preserve the working lab and private evidence. Record the final commit using `git rev-parse HEAD` and review the diff. The finalization changes documentation and ignore rules only; runtime code, tests, profiles, dependencies and the MIT license text remain unchanged.
2. Carry forward the full Windows pass at `09e8128` and all seven delta checks at `4fedd3f`. Verify documentation links and the final diff. No dependency reinstall, model scan or paid call is required for these edits.
3. Check the final tracked tree and reachable history against the allowlist and privacy rules. Retain the check result privately and report any qualification. Preserve failures and baseline gaps in the published compatibility table.
4. If the owner authorizes private staging, create/use the agreed empty private repository and push only the reviewed release branch. Verify its exact head and tree before requesting public visibility. Do not push unrelated refs or use `--mirror`.
5. Return the exact candidate SHA, short diff summary and public-file/history check result. Stop for owner publication and tag approval.
6. Only after approval, make the reviewed repository public and tag the approved commit `v1.0.0`. Release notes must state the fourteen-probe scope, model-specific results, Ollama DAN limitation, validation boundaries and deferred features. Do not include excluded material in release attachments.

[Windows quick start](../README.md#windows-quick-start) · [Release validation](release-v1.md) · [Maintainer Windows checks](clean-windows.md) · [Worked example](worked-example.md) · [Third-party notices](../THIRD_PARTY.md)
