# VLM Model Selection for Industrial Visual Inspection
## Frontier Open-Source Models — Mid-2026

---

## 1. Model Landscape Overview

The VLM space moved fast between late 2024 and mid-2026. The meaningful frontier models for local deployment are now:

| Model | Release | Sizes | VRAM (4-bit) | Ollama | vLLM | llama.cpp |
|---|---|---|---|---|---|---|
| **Qwen3-VL** | Sep–Oct 2025 | 4B, 8B, 30B-A3B, 235B-A22B | 6GB (4B), 8–10GB (8B) | ✅ (≥0.12.7) | ✅ | ✅ |
| **InternVL3 / 3.5** | Apr 2025 / Aug 2025 | 1B, 2B, 8B, 14B, 38B, 78B | ~10GB (8B), ~20GB (14B) | Partial | ✅ | ✅ |
| **DeepSeek-VL2** | Late 2024 | Multiple (MoE) | Varies (MoE efficient) | ❌ | ✅ | Limited |
| **GLM-4.6V** | 2025 | 9B Flash | 6–8GB (Q4) | Pending | Partial | Draft PR |
| **SmolVLM2** | Early 2025 | 256M, 500M, 2.2B | <4GB | ✅ | ✅ | ✅ |
| **Molmo2** | 2025 | 7B, 72B | ~10GB (7B Q4) | Partial | ✅ (new arch) | Limited |

---

## 2. Model-by-Model Analysis

### Qwen3-VL — **Top Recommendation for RTX Deployment**

Released in phases: 235B-A22B (Sep 23 2025), 4B/8B (Oct 15 2025), 2B/32B (Oct 21 2025).

**Architecture:** Dense (4B, 8B) and MoE (30B-A3B = 30B total, only 3B active per token). The MoE variant gives near-14B reasoning quality at 3B compute cost.

**VRAM requirements:**
- 4B at Q4_K_M: ~6 GB — fits RTX 3060 / 4060 8GB
- 8B at Q4_K_M: ~8–10 GB — fits RTX 3080/4070 10–12GB
- 30B-A3B at Int4: ~24 GB — needs RTX 3090/4090

**Ollama:** Full support in Ollama ≥0.12.7. Model available at `ollama pull qwen3-vl:8b`.

**Tool calling:** Native. Tops OSWorld benchmark for GUI agent tasks — can navigate interfaces, call tools, complete multi-step workflows. Best tool-calling VLM available locally.

**Industrial relevance:** Strong OCR, document understanding, and visual reasoning. Recommended as primary model for inspection pipelines.

**Sources:**
- [Qwen3-VL GitHub](https://github.com/QwenLM/Qwen3-VL)
- [Ollama Library: qwen3-vl](https://ollama.com/library/qwen3-vl)
- [VRAM + benchmark guide](https://ghost.codersera.com/blog/qwen3-vl-4b-vs-qwen3-vl-8b-benchmarks-vram-guide/)

---

### InternVL3 / InternVL3.5 — **Best for Document/OCR Tasks**

Released April 2025 (InternVL3), August 2025 (InternVL3.5). Developed by OpenGVLab.

**Benchmark scores (InternVL3):**

| Model | MMMU | OCRBench | DocVQA | ChartQA |
|---|---|---|---|---|
| InternVL3-8B | 62.7 | 880 | — | — |
| InternVL3-38B | 70.1 | — | 95.4 | 89.2 |
| InternVL3-78B | **72.2** | **906** | — | — |

The 78B model sets new open-source SOTA on MMMU. The 38B model is the practical sweet spot for document/inspection work: 95.4 on DocVQA is exceptional.

**Architecture:** ViT-MLP-LLM with Variable Visual Position Encoding and dynamic resolution tiling. Image is tiled at multiple scales — higher accuracy on documents and charts but inflates visual token count. Encoder adds 2–4 GB VRAM overhead for high-resolution inputs.

**Sizes for RTX deployment:**
- InternVL3-8B: ~12–14 GB at BF16, ~7–8 GB at Q4 — fits RTX 3090/4090
- InternVL3-2B: fits 8GB VRAM comfortably

**Tool calling:** Explicitly supports tool usage, GUI agents, industrial image analysis, and 3D vision perception.

**Industrial relevance:** Best open-source model for OCR on nameplates, engineering drawings, P&ID diagrams, and technical documentation. The dynamic tiling architecture is specifically designed for high-resolution document images.

**Sources:**
- [InternVL3 Blog Post](https://internvl.github.io/blog/2025-04-11-InternVL-3.0/)
- [InternVL3.5 Paper (arxiv)](https://arxiv.org/abs/2508.18265)
- [InternVL GitHub](https://github.com/opengvlab/internvl)

---

### DeepSeek-VL2 — **Best Throughput-per-VRAM**

**Architecture:** Mixture-of-experts decoder. Cuts inference latency 50–70% compared to dense models of equivalent capability while maintaining accuracy.

**Strengths:** Broad multimodal capabilities, highest efficiency for server-side batch processing. Added as supported architecture in vLLM.

**Limitations for local use:** No Ollama support. Requires vLLM or direct Transformers inference. Not ideal for single-GPU developer workflows.

**When to use:** If you're running a production inference server (not Ollama), DeepSeek-VL2 is the most cost-efficient option per token.

---

### GLM-4.6V — **Watch List**

Released mid-2025 by Zhipu AI. The Flash variant (9B) delivers ~55–58 tok/s on 8GB VRAM systems.

**VRAM:** ~18–20 GB in FP16. Quantized to Q4_K_M: ~6–8 GB — fits RTX 3060/4060.

**Ollama/llama.cpp status (as of April 2026):** Text-only support available via workaround (PR #16600 in llama.cpp). Full vision GGUF support is in draft — expected to land within weeks of this report. Ollama support will follow immediately after llama.cpp merges.

**Recommendation:** Hold — revisit when llama.cpp vision support merges. Performance looks competitive with Qwen3-VL-8B.

**Sources:**
- [GLM-4.6V Review and Benchmarks](https://binaryverseai.com/glm-4-6v-review-benchmarks-pricing-local-install/)
- [llama.cpp GLM-4.1V issue #14495](https://github.com/ggml-org/llama.cpp/issues/14495)

---

### SmolVLM2 — **Edge/Embedded Only**

Sizes: 256M, 500M, 2.2B. The 500M is the recommended trade-off point.

**Primary use case:** Video understanding at minimal compute. Runs on mobile hardware. Not suitable for high-accuracy industrial inspection — use for lightweight anomaly flagging on constrained edge devices only.

**Sources:**
- [VLMs 2025 — Hugging Face Blog](https://huggingface.co/blog/vlms-2025)

---

### Molmo2

Added as a new supported architecture in vLLM. Strong grounding/localization capabilities — can output spatial coordinates for objects. Relevant for pointing at defects in images. Still maturing in the Ollama/llama.cpp ecosystem.

---

## 3. Quantization Tradeoffs for Visual Inspection

GGUF quantization affects both text generation quality and visual token interpretation. Recommendations specific to inspection workloads:

| Quant | File Size (7–9B) | VRAM | Perplexity Impact | Visual Accuracy | Recommendation |
|---|---|---|---|---|---|
| Q4_K_M | ~4.8 GB | ~6–8 GB | +0.054 ppl | Slight degradation on fine detail | **Daily use — good balance** |
| Q5_K_M | ~5.5 GB | ~7–9 GB | +0.020 ppl | Near-full quality | **Recommended for inspection** |
| Q8_0 | ~8.5 GB | ~10–12 GB | ~0 | Essentially lossless | Use only if VRAM allows |
| F16 | ~14 GB | ~16–18 GB | Baseline | Baseline | Dev/benchmarking only |

**Key insight for VLMs specifically:** The vision encoder (ViT) is typically more sensitive to quantization than the text decoder. Models like InternVL3 that tile high-resolution images have more visual tokens in flight, making Q5_K_M the practical minimum for reliable defect detection on small features. For nameplate OCR or reading serial numbers, Q8_0 is worth the VRAM cost.

**Sources:**
- [llama.cpp quantization README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)
- [Unified evaluation of llama.cpp quantization (arxiv)](https://arxiv.org/html/2601.14277v1)
- [AI Model Quantization 2025 Guide](https://local-ai-zone.github.io/guides/what-is-ai-quantization-q4-k-m-q8-gguf-guide-2025.html)

---

## 4. Fine-Tuning with LoRA/QLoRA (2026 Best Practices)

### LlamaFactory — Recommended Tool

[LlamaFactory](https://github.com/hiyouga/LlamaFactory) (ACL 2024, 100+ models) is the current best-in-class unified fine-tuning framework. It supports:

- **Qwen3-VL** (all sizes), **InternVL 2.5–3.5** (up to 241B), **GLM-4.5V**, **Kimi-VL**, **Pixtral**, **Llama 3.2 Vision**, **DeepSeek-VL2**
- LoRA, QLoRA, DoRA, LoRA+, PiSSA
- 2/3/4/5/6/8-bit quantization via AQLM/AWQ/GPTQ/LLM.int8/HQQ
- FSCP+QLoRA: fine-tunes a **70B model on 2×24GB GPUs**
- Unsloth integration: 170% faster LoRA training, 50% less memory vs FlashAttention-2

### Industrial Defect Detection: PLG-DINO Approach

A 2025 paper introduced PLG-DINO — LoRA modules injected into self- and cross-attention layers of Grounding DINO. Key findings:
- **Consistently outperforms full fine-tuning** in low-data industrial defect scenarios
- Achieves competitive localization precision and semantic alignment with only a few hundred labeled samples per class
- Soft prompt learning combined with LoRA = state of the art for small manufacturing datasets

### Practical Recipe for Manufacturing LoRA Fine-Tuning

1. Start with **Qwen3-VL-8B** or **InternVL3-8B** as base
2. Collect 200–500 labeled defect images per category (bounding boxes + text descriptions)
3. Use LlamaFactory with QLoRA (4-bit) — fits on single RTX 3090 24GB
4. Fine-tune only on defect classification and OCR tasks (not general vision)
5. Evaluate on held-out inspection images before deployment

**Sources:**
- [LlamaFactory GitHub](https://github.com/hiyouga/LlamaFactory)
- [PLG-DINO Paper (OpenReview)](https://openreview.net/pdf?id=Ze3diyHxr9)
- [Fine-tuning VLM for object detection — Hugging Face cookbook](https://huggingface.co/learn/cookbook/fine_tuning_vlm_object_detection_grounding)
- [VLM-R1 GitHub](https://github.com/om-ai-lab/VLM-R1)

---

## 5. Vision-Language-Action (VLA) Models

VLA models add action prediction on top of visual understanding — relevant for robotic inspection arms and automated reject mechanisms.

| Model | Parameters | Status | Use Case |
|---|---|---|---|
| **π0 / π0-FAST** | ~7B | Production (physical robotics) | 7 robot platforms, 68 tasks |
| **NVIDIA GR00T N1** | 2B | Production | Humanoid robot foundation model |
| **OpenVLA** | 7B | Research | Robot manipulation |

**Assessment for manufacturing:** π0 and GR00T N1 are the only VLAs that have been demonstrated on real hardware at scale. Neither is designed for visual inspection reporting — they output robot actions, not defect classifications. For a pure inspection tool (camera → defect report → human decision), a standard VLM is the right choice. VLAs become relevant when you want the system to trigger physical responses (e.g., reject arm, conveyor stop) based on visual inspection output.

**Sources:**
- [VLMs 2025 — Hugging Face Blog](https://huggingface.co/blog/vlms-2025)
- [NVIDIA GR00T N1](https://developer.nvidia.com/blog/visual-language-intelligence-and-edge-ai-2-0/)

---

## 6. Industrial/Technical Imagery Specialists

### Models with Explicit Industrial/OCR Capabilities

**InternVL3** is the strongest open-source model for:
- PDF layout understanding
- OCR on scanned documents and nameplates
- Table and chart extraction
- Engineering drawing interpretation

**NVIDIA Cosmos Nemotron** (VILA family, Jan 2025) was specifically trained for visual monitoring of physical environments. Uses 4-bit AWQ quantization with negligible accuracy loss. Part of the Jetson Platform Services stack.

**VLM-R1** (GitHub: om-ai-lab/VLM-R1): Uses reinforcement learning to train VLMs for visual understanding tasks. A GUI defect detection model trained with VLM-R1 outperforms both base and SFT models on defect/clean screen discrimination.

**IAD-GPT:** 2025 paper specifically targeting industrial anomaly detection with VLMs. Demonstrated on MVTec and VisA benchmarks.

### Benchmark Reference: VLMEvalKit

[VLMEvalKit](https://github.com/open-compass/VLMEvalKit) supports 220+ models and 80+ benchmarks. As of mid-2026: supports InternVL3 series, SmolVLM2, and industrial-relevant benchmarks including OCRBench, DocVQA, TextVQA, ChartQA, and the new MMT-Bench (31,325 questions across 32 meta-tasks including visual recognition and OCR).

---

## 7. Recommended Stack for a Manufacturing VLM Inspection Tool

| Use Case | Recommended Model | Runtime |
|---|---|---|
| General inspection on RTX 4070/4080 (12–16GB) | Qwen3-VL-8B Q5_K_M | Ollama |
| OCR on nameplates / engineering drawings | InternVL3-8B | vLLM or Ollama |
| Edge deployment (factory floor, Jetson Orin Nano) | Qwen3-VL-4B Q4_K_M | Ollama or llama.cpp |
| Highest accuracy (RTX 3090/4090 24GB) | InternVL3-14B Q5_K_M | vLLM |
| Fine-tuning on custom defect dataset | Qwen3-VL-8B + LlamaFactory QLoRA | Direct Transformers |
| Lightweight anomaly flagging (edge/embedded) | SmolVLM2-500M | llama.cpp |
