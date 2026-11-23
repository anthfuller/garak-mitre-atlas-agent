# 0.3.0 — available probes and OpenAI

This cumulative update hides unavailable probes before search/pagination, retains review Back state, and adds OpenAI as target option 2 with multiple probe choices. No scan starts by selecting a target or probe.

## OpenAI review controls

- `L`: set `max_completion_tokens` (1–128000; default 1500). This includes reasoning and visible output. The actual SDK request is checked before dispatch.
- `R`: set, raise or remove an optional HTTP request cap; `0` removes it. Default OFF. The counter includes the compatibility check and every dispatch, including a retry if one occurs. SDK retries are disabled and HTTP errors abort.
- `A`: set or remove an optional USD spending alert. Default OFF. At the threshold, choose Continue for one more request, Raise alert, or Stop before another request. Missing usage can understate the total.
- `P`: enter optional input/output rates per million tokens. They are labeled operator-supplied, not independently verified.
- `B`: same search results/page. Enter/Ctrl+C: cancel. Only `RUN` authorizes the compatibility generation and selected scan.

At a configured request cap the operator can raise it, remove it, or stop. The original logical workload and wall-time controls are unchanged. No balance lookup, $200-derived limit or automatic spending alert is present.

Cost estimation uses the longest offline sampled input's UTF-8 JSON bytes plus 64 planning units per request and the full completion limit. This is conservative planning, not a tokenizer or a billing guarantee. With no request cap it uses planned requests plus one compatibility call. The review shows the assumptions, rates and verification date. Unverified pricing or unavailable input estimation displays **Estimate unavailable** without blocking RUN. Running estimates use reported usage and include compatibility and retry responses when present.

Published pricing source: https://developers.openai.com/api/docs/models/gpt-5.6-sol — checked November 22, 2026: $4/M uncached input, $0.40/M cached input, $20/M output. Promotional rates expire November 30, 2026. These estimates assume standard short-context text service; actual billing may differ. The model page documents a 128000 output-token maximum. The active API model and account access remain unverified until the operator's live check.

Token semantics: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create — max_completion_tokens includes reasoning tokens. Garak 0.17.0 suppresses max_tokens for its reasoning generator. This patch explicitly suppresses other sampling parameters, forwards the chosen max_completion_tokens and checks the outgoing parameter set. Sampling seed 42 affects probe selection; it is not sent as an OpenAI generation seed.

## Credential and evidence handling

The scanner child prompts through hidden terminal input after RUN and local preflight. Echo fallback is rejected. The key is held only for that child process, never in command arguments, files or the parent shell environment. Child stdout/diagnostic exceptions are redacted; native response bodies are scrubbed before Garak receives them. Error message bodies are omitted to avoid key-fragment disclosure. This is process-memory handling, not a claim of secure memory erasure or protection against privileged local inspection.

One compatibility generation confirms API access when it returns complete nonempty text. Probe execution follows separately; native counts and transport quality are checked. No claim is made that one API check validates every probe. Full requests/responses, usage, settings and run identifiers remain in evidence; the concise ATLAS handoff and Copy/Notepad actions remain unchanged. Existing-run handoff regeneration does not call OpenAI.

OpenAI requires interactive RUN and hidden input in this release. OpenAI --yes is rejected before any call; existing Ollama/handoff unattended behavior is unchanged. Windows console, key entry and live API validation remain pending.

## Apply in Windows PowerShell

Save `Garak_Playbook_0_3_0_OpenAI.zip` beside the existing `garak-playbook` folder. From that parent directory:

```powershell
Expand-Archive -LiteralPath .\Garak_Playbook_0_3_0_OpenAI.zip -DestinationPath . -Force -ErrorAction Stop
```

Launch the same `playbook.py menu --config <private-config-path>` command. This ZIP alone applies over the existing working installation; no previous ZIP stack is needed. It contains no private configuration, campaigns file, environment, model, database or previous scan evidence. No dependency installation or paid request is performed by extraction.

## Validation

103 standard-library offline tests pass. Real installed-registry validation sees 191 probes and displays only the 14 reviewed workloads. All 14 workload/detector pairs were instantiated offline. Six real Garak CLI tests against a synthetic Ollama endpoint pass, preserving the existing local path.

Fifteen OpenAI integration cases use real Garak 0.17.0, OpenAI SDK 2.54.0 and HTTPX 0.28.1 with an in-memory MockTransport and a socket-denial audit hook. They cover two probe paths (WhoIsRiley and Base32), exact max_completion_tokens forwarding, authentication/rate/transport errors, check/scan truncation, credential echoes, cap stop/raise/remove, alert stop/raise/continue, and missing pricing. Compatibility requests are separate from evaluated probe counts. Dummy credentials were absent from captured stdout, stderr and all generated files. These are synthetic integration results, not live API/model validation.
