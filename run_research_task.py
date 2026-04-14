"""
Launcher for the VLM visual inspection research task.
Run from Smith_Agentic/: python run_research_task.py
"""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config.loader import load_config
from crews.default_crew import build_crew

GOAL = """\
Deep research on building the most cutting-edge, locally-hosted VLM-powered visual
inspection tool for manufacturing environments. Fully open source, no paid APIs.

=== TOPIC 1: VLM Model Selection ===

Research the newest open-source VLMs for industrial visual inspection: Qwen3-VL,
GLM-4.6V, InternVL3, DeepSeek-VL2, Molmo2, SmolVLM2. Specifically:
- Which run on a single RTX GPU (8-16GB VRAM) via Ollama, vLLM, or llama.cpp?
- Which support native tool calling for agentic workflows?
- Quantization tradeoffs: GGUF Q4_K_M vs Q5_K_M vs Q8 for inspection accuracy
- Fine-tuning with LoRA/QLoRA on small manufacturing image datasets — best approach
- Any models designed specifically for industrial imagery, OCR, or defect classification?
- Are any Vision-Language-Action (VLA) models mature enough for real-world inspection?

=== TOPIC 2: Architecture & Frontend ===

Research the best stack for a local VLM inspection tool with a React frontend:
- Backend: FastAPI + Ollama vs vLLM vs llama.cpp server — latency for image inference
- Real-time camera in React: WebRTC, RTSP-to-browser, IP cameras, USB webcam capture
- React libraries for image annotation and bounding box overlay
- Streaming inference: token-by-token while the user watches
- Open source VLM inspection UIs that already exist and could be forked
- Edge deployment on NVIDIA Jetson or factory floor devices

=== TOPIC 3: Agentic VLM Integration ===

Research integrating a VLM as a Vision agent in a multi-agent system:
- Architecture patterns: Vision agent that Orchestrator/Builder/Critic can call with
  an image + prompt and receive structured output
- Multi-modal memory: storing image+text pairs in ChromaDB for past inspection recall
- Chaining YOLO/SAM2 detection with VLM reasoning on crops
- Structured JSON output from VLMs: defect reports, severity scores, pass/fail
- Best open source agentic VLM systems today (AutoGen multimodal, LangGraph vision,
  CrewAI vision tools)

=== OUTPUT INSTRUCTIONS ===

The Builder MUST write FOUR files using the Write Output File tool:
1. filepath='deliverable.md'                          — combined master report
2. filepath='research/vlm_model_selection.md'         — TOPIC 1 standalone
3. filepath='research/architecture_and_frontend.md'   — TOPIC 2 standalone
4. filepath='research/agentic_vlm_integration.md'     — TOPIC 3 standalone

Write complete reports with real findings. Not outlines. Not templates. Not
placeholders. Fill every section with what you actually found via web search and
page fetches. Cite real URLs. If you have not yet searched for something, search
for it now — do not write 'to be researched'.
"""


def main():
    cfg = load_config()
    cfg["crew"]["hitl"] = False
    cfg["crew"]["verbose"] = True

    print("\n" + "=" * 60)
    print("  SmithAgentic — VLM Inspection Research Run")
    print("  Model : qwen2.5:32b  |  HITL : OFF")
    print("=" * 60 + "\n")

    crew = build_crew(goal=GOAL, config=cfg)
    result = crew.kickoff()

    print("\n" + "=" * 60)
    print("  CREW COMPLETE")
    print("=" * 60)
    print(result)
    print("\nOutputs written to Smith_Agentic/outputs/")


if __name__ == "__main__":
    main()
