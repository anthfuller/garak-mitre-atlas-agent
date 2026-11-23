# Probe compatibility for the public v1 candidate

Scope: Garak 0.17.0 on Windows. Model labels identify the configured targets in this lab. Each cell describes reviewed evidence for that pair. Source checks and offline workload construction do not establish live operation.

| Probe | Ollama · llama3.2:3b | OpenAI · gpt-5.6-sol |
| --- | --- | --- |
| `dan.DanInTheWild` | Live result unverified | Completed with gaps · 32 attempts, 31 evaluated, 28 flags, 1 unscorable (V1-02) |
| `encoding.InjectAscii85` | Live result unverified | Live result unverified |
| `encoding.InjectBase16` | Live result unverified | Live result unverified |
| `encoding.InjectBase32` | Live result unverified | Live result unverified |
| `encoding.InjectBase64` | Completed · 32 evaluated, 0 detector flags (V1-01) | Live result unverified |
| `encoding.InjectHex` | Live result unverified | Live result unverified |
| `encoding.InjectROT13` | Live result unverified | Live result unverified |
| `goodside.Davidjl` | Live result unverified | Live result unverified |
| `goodside.Tag` | Live result unverified | Live result unverified |
| `goodside.ThreatenJSON` | Live result unverified | Live result unverified |
| `goodside.WhoIsRiley` | Live result unverified | Live result unverified |
| `lmrc.Anthropomorphisation` | Live result unverified | Live result unverified |
| `lmrc.Deadnaming` | Live result unverified | Live result unverified |
| `lmrc.QuackMedicine` | Live result unverified | Live result unverified |

An Ascii85 execution was reported. Its provider-specific final summary needs reconciliation before assigning credit here. The maintainer should refresh this table from the private archive before tagging v1. A gap or an unverified cell must be disclosed in release notes.

The other 177 registry IDs are outside v1 scope. Planned v2 additions require their own model-specific evidence.
