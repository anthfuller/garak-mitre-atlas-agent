# 0.6.4: Bounded recovery from Windows session-file replacement errors

**Historical version 0.6.4 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

Historical implementation note. Update: the complete Windows validator passed at commit `09e8128` on November 26, 2026. See [release validation](release-v1.md) for scope and later changes.

The supplied Windows synthetic integration log records `WinError 5: Access is
denied` while replacing `ollama-session.json`. The first Base64 case stopped
after 27 response records, before detector evaluation. This is a filesystem
failure, distinct from the real Ollama DAN server's HTTP 500. The log does not
identify the process or permission condition responsible for the denial.

## Correction

The local worker writes each session snapshot to a unique, closed UTF-8
temporary file in the destination directory. It attempts replacement at most
six times for Windows errors 5, 32 or 33. Five possible waits are 0.05, 0.10,
0.20, 0.40 and 0.80 seconds: 1.55 seconds of scheduled waiting per snapshot.
Retries and recovery are printed to the captured worker log. Other errors
propagate immediately. Persistent failure remains a nonzero failure; the
previous snapshot and pending temporary file are retained. A final failure
snapshot has its own bounded publication attempt.

Only file replacement is retried. No model or HTTP request is repeated by this
correction. Request bodies, generation settings, prompt selection, detector,
transport-error handling and timeout limits remain unchanged. The manifest
records the session-write policy and the worker hash. This changes runner I/O
behavior; it is not an exact reproduction of the previous execution path.

The correction does not delete the destination, modify access permissions,
disable security software, change installed dependencies or fix persistent
filesystem access problems. The OpenAI transport is unchanged.

## Verification and limits

Offline fault injection covers transient Windows errors 5/32/33, exact Unicode
snapshot preservation, bounded permanent failure, unrelated errors without
retry, one HTTP request during a recovered response write, and a permanent
write failure stopping before the next request. Existing HTTP 500/timeout
tests still require no error retry. These mocks do not reproduce the original
native Windows access denial or identify its cause.

Real Garak with synthetic local protocol responses checks successful execution
and HTTP-error handling separately. Packaged validation receipts name the
tested commit and platform. Windows acceptance requires the full validator to
finish on the corrected checkout. Reuse of the recorded validation environments
avoids reinstalling unchanged dependencies. No live model scan or paid call is
needed, and the closed live Ollama DAN investigation remains closed.
