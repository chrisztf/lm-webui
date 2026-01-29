# LM WebUI

<p align="center">
  <img src="./assets/demo.png" width="1080" />
</p>

<p align="center">
  <a href="https://github.com/lm-webui/lm-webui/actions">
    <img src="https://img.shields.io/badge/development-active-green" />
  </a>
  <a href="https://github.com/lm-webui/lm-webui/releases">
    <img src="https://img.shields.io/badge/release-v0.1.0-blue" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-black" />
  </a>
  <a href="https://lmwebui.com">
    <img src="https://img.shields.io/badge/Website-lmwebui.com-orange" />
  </a>
</p>

<p align="center">
  <b>Run AI on your control</b>
</p>

---

> ⚠️ **Work in Progress (WIP)**
> lm-webui is under active development. Features, APIs, and architecture may change as the project evolves. Contributions, feedback, and early testing are welcome, but expect breaking changes.

**lm-webui** is a multimodal LLM interface and orchestration platform designed for **privacy-first, fully offline AI workflows**.

It unifies local and API-based models, RAG pipelines, and multimodal inputs under a single control plane—while keeping data ownership, performance, and deployment flexibility firmly in the user’s hands.

Built for developers, system integrators, and organizations that require **local inference, reproducibility, and infrastructure-level control**, lm-webui bridges the gap between experimental LLM tooling and production-ready AI systems.

---
## Core Features of LM WebUI ⚡ 

| Feature                   | Capabilities                                                                                 |
| -------------------------- | -------------------------------------------------------------------------------------------- |
| ✨ **Multimodal Interface**   | Create Image, process docs, and text input, easily handling under a unified chat               |
| 🔒 **Privacy-first by design** | prompts, documents, embeddings, and outputs remain local by default                  |
| 🔗 **RAG Engine**             | Configurable retrieval pipelines with local vector stores and source attribution             |
| 🤝 **Model‑Agnostic** | Run local models or API-based LLMs through a smart model selector                  |
| 🤗 **GGUF Loader Engine**   | Built‑in model deployment engine for GGUF-based local models, including quantized variants   |
| 🛠️ **Hardware Acceleration**  | Automatic hardware detection and optimized execution on CPU, GPU, and supported accelerators |
| ⚙️ **Workflow Orchestration** | Chain prompts, tools, retrieval, and models into reproducible workflows                      |
| 🏠 **Self‑Hosted Ready**      | Efortless on‑prem, private cloud, and isolated network deployments                        |

---

## Roadmap & Known Limitations

This project is evolving toward a stable release. The following outlines current limitations and planned improvements.

### Known Limitations

* Some multimodal pipelines are still experimental
* Some multimodal conversation are still buggy and under improvement
* Hardware acceleration behavior may vary across GPU vendors and driver versions
* RAG source attribution and metadata handling are functional but not yet fully standardized
* Limited validation and guardrails for misconfigured local models or incompatible GGUF variants
* Documentation and deployment examples are incomplete and actively expanding

### Roadmap (High-Level)

**Near-term**

* Stabilize core orchestration APIs and configuration schema
* Improve GGUF deployment automation and quantization presets
* Expand hardware detection and backend fallback logic

**Mid-term**

* Add stronger RAG governance (source versioning, metadata filters, audit-friendly outputs)
* Introduce model bundle validation and optional signature checks
* Improve workflow reproducibility and export/import support

**Long-term**

* Advanced scheduling for multi-GPU and multi-model workloads
* Adapter / LoRA management for task-specific fine-tuning
* More Enterprise-oriented features (audit logs, policy controls, etc)

---

lm-webui focuses on **operational clarity over abstraction**—providing the building blocks required to deploy, govern, and scale local AI systems without surrendering control to opaque cloud platforms.
