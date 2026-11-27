# 0.6.3: Capture local Ollama failures and stop error retries

**Historical version 0.6.3 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

At the 0.6.3 build checkpoint, source implementation and offline tests were complete; native Windows validation followed in later records.

The failed DAN run returned repeated HTTP 500 errors. Garak 0.17.0's Ollama
adapter retried until the runner's 1,800-second wall-time limit. The supplied
HTTP and server-log excerpts did not contain the HTTP error body. The cause
inside Ollama remains unknown; this patch does not claim to fix that cause.

## Changed behavior

- The existing Garak CLI, probe, detector, Ollama chat adapter, model and
  generation settings remain in use. A separate runner-owned child adds HTTP
  transport capture; installed Garak and Ollama files are never modified.
- Stop on the first non-200 response or transport exception, including a
  timeout. HTTP error retries are disabled. The configured 120-second client
  timeout and 1,800-second total limit are unchanged.
- Successful responses are passed through with their original bytes. Garak's
  existing successful-empty-response handling remains: at most three calls.
- Save exact request/response body bytes as Base64, plus readable JSON, in
  `ollama-transport.jsonl`. Record request sequence, status and elapsed time.
  Save `ollama-session.json`, include both in the original run checksums and
  coverage evidence references, and print a bounded JSON-escaped error message.
- The affected scan remains incomplete; the batch stops. An HTTP error is not
  a detector pass, a confirmed vulnerability, or proof of broad incompatibility.
- Display this transport-policy change before RUN. New runs are modified
  experiments, not exact reproductions of historical retry behavior.

The local endpoint must remain unauthenticated HTTP loopback. Headers are not
archived. Full body records may contain sensitive test material and belong
with private evidence, not in a public repository. Provider-side hidden state,
GPU execution and cancellation of already accepted server work are not proven.

## Validation

The exact test receipt and logs were retained privately outside the source tree.
The native integration uses real Garak 0.17.0 and the Ollama SDK against a
synthetic HTTP server. It fails request 23 after 22 successes, verifies one
error request with no retry, preserves exact body bytes, and records an
incomplete run with a nonzero child exit. Separate success integrations verify
unchanged generation options and the existing evidence/handoff path.

These are Linux synthetic tests. They are not live-model or native Windows
validation. No cloud calls, scans against a real model, or configuration
changes on the operator's machine occurred while building the patch.

## Historical application

The original 0.6.3 launcher checked source hashes, backed up files, recorded an update receipt and rolled back failed replacements. Unknown local modifications stopped installation. Existing evidence, private configuration and databases were outside the replacement list.

Its diagnostic selected only the previously failed Ollama DAN pair and required `RUN`. The later attempt captured the HTTP error body and stopped without a retry; it did not establish a successful probe result. That investigation is closed for v1. Use the [compatibility table](compatibility.md) for the retained failure and evidence boundary; these notes are not an instruction to rerun the campaign.
