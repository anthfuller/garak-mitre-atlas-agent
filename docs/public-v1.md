# Public v1 release instructions

**Current status: private preparation.** This candidate packages the reviewed 0.5.0 interactive runner. A v1.0.0 tag belongs on the final validated commit. The Builder's proposed batch implementation requires its own source review and validation if included.

## What ships in v1

One Windows PowerShell entry point, 14 selectable Garak probes, separate Ollama and OpenAI results, original evidence and settings, an ATLAS handoff, and optional ATLAS, Kumu and local Chroma integrations. The other 177 Garak 0.17.0 registry entries are outside this release's support claim. Broader coverage is v2 work.

## Release sequence for the maintainer

1. Clone the supplied bundle into a new Windows folder using the clean-checkout guide. Preserve the working lab installation. Use a new test environment and a new scanner environment. Retain the commit, package versions, Windows test receipt and three scanner integration results outside the repository. Check the final git status.
2. Reconcile all 28 probe/model cells against the private run archive. Reuse matching evidence. Check model, settings, detector, execution status and actual evaluated, flagged and unscorable counts. Record a short public evidence alias for each reviewed result and keep its mapping to original files privately. Inspect gaps and failures. Obtain the owner's explicit decision on any limitation that will ship. A pair can have an honest failed result without earning a compatibility claim.
3. Update the public compatibility table and README for the final commit. Include the tested versions and limitations. If batch operation is added, record how skipped, incomplete and failed runs appear in the report. Verify clean Windows installation and tests on the resulting code. Make the software's displayed version and release notes agree with the tag.
4. Review the final tracked file list and Git history. Include source, synthetic fixtures and sanitized documentation only. Keep API keys, environment files, private endpoints, operator paths, original reports, run IDs and Chroma databases outside the repository. Confirm the right to distribute the included code, copyright holder line and third-party notices. Use the project independence statement in the README.
5. After the owner accepts the results, use the owner's personal GitHub account to create an empty private repository named **garak-playbook**. Leave the GitHub README, license and gitignore initialization boxes unchecked. Push only the approved main branch from the clean source checkout. If cloned from the bundle, its origin points to a file; add the owner's empty repository as a separate remote named github. Inspect the files online before changing visibility.
6. With the owner's publication approval, open repository **Settings → General → Danger Zone → Change repository visibility** and make it public. In **Releases → Draft a new release**, create tag **v1.0.0** at the accepted commit and publish the release notes. State which model/probe pairs completed, which had gaps and which were excluded. Link the compatibility table. Reserve broader probe support for later releases.

[Clean Windows checkout and scanner tests](clean-windows.md) · [Probe compatibility](compatibility.md) · [Third-party notices](../THIRD_PARTY.md)
