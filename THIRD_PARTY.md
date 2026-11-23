# External components and publication status

The project orchestrates separately installed software. It does not bundle model weights, Garak payload datasets, Chroma binaries, Langflow flows or the ATLAS dataset.

| Component | Primary reference |
| --- | --- |
| Garak 0.17.0 | https://github.com/NVIDIA/garak/tree/v0.17.0 |
| OpenAI Python SDK | https://github.com/openai/openai-python |
| HTTPX | https://github.com/encode/httpx |
| Ollama | https://github.com/ollama/ollama |
| EmbeddingGemma | https://huggingface.co/google/embeddinggemma-300m |
| Chroma 1.5.9 | https://github.com/chroma-core/chroma/tree/1.5.9 |
| ATLAS Knowledge Base Agent | https://github.com/mitre-atlas/atlas-knowledge-base-agent |
| Langflow | https://github.com/langflow-ai/langflow |
| Kumu | https://kumu.io/ |

Source-audit hashes identify inspected external files; those source files and corpora are not copied into this repository. Synthetic test data are not real findings. Product names describe integrations, not endorsements.

Original project code and documentation use the [MIT License](LICENSE). External software, datasets, APIs and model weights remain subject to the terms of their respective providers. The project license does not grant trademark rights or override model or service terms. Before redistributing any external component, review the license for the exact version and retain its required notices.
