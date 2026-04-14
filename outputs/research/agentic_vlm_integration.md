# Agentic VLM Integration for Smith_Agentic
## Multi-Modal Multi-Agent Architecture — Mid-2026

---

## 1. Vision Agent Architecture Pattern

### Core Design: VLM as a Tool, Not an Agent

The most robust pattern for integrating a VLM into an existing multi-agent system is to expose it as a **callable tool** rather than a full agent. This keeps the agent topology clean — Orchestrator, Researcher, Builder, Critic all retain their existing roles, but any of them can call the vision tool when they need image analysis.

```python
# tools/vision_tool.py
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import base64
import httpx

class _VisionInput(BaseModel):
    image_path: str = Field(description="Path to image file in outputs/ directory.")
    prompt: str = Field(description="What to analyze in the image.")
    structured: bool = Field(default=True, description="Return JSON defect report if True.")

class VisionInspectionTool(BaseTool):
    name: str = "Vision Inspection"
    description: str = (
        "Analyze an image using a local VLM. Pass an image path and a prompt. "
        "Returns structured JSON with defect classification, severity, and location "
        "when structured=True, or freeform analysis when structured=False. "
        "Use this to inspect uploaded images, frame captures, or saved inspection photos."
    )
    args_schema: type[BaseModel] = _VisionInput

    def _run(self, image_path: str, prompt: str, structured: bool = True) -> str:
        # Load image from outputs/ directory
        from pathlib import Path
        img_bytes = (Path(__file__).parent.parent / "outputs" / image_path).read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode()

        system_prompt = ""
        if structured:
            system_prompt = (
                "You are a manufacturing quality inspector. "
                "Respond ONLY with valid JSON matching this schema: "
                '{"pass": bool, "defects": [{"label": str, "severity": "low"|"medium"|"high"|"critical", '
                '"location": str, "confidence": float, "bbox": [x,y,w,h]}], '
                '"summary": str, "action": "PASS"|"REVIEW"|"REJECT"}'
            )

        payload = {
            "model": "qwen3-vl:8b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt}
                ]}
            ],
            "temperature": 0.1,  # Low temp for consistent structured output
        }

        response = httpx.post(
            "http://localhost:11434/v1/chat/completions",
            json=payload,
            timeout=120
        )
        return response.json()["choices"][0]["message"]["content"]
```

### Wiring into Smith_Agentic's Default Crew

Add `VisionInspectionTool` to the Builder and Critic — the agents most likely to need image analysis:

```python
# crews/default_crew.py addition
from tools.vision_tool import VisionInspectionTool

vision_inspect = VisionInspectionTool()

builder = create_builder(llm=llm, tools=[
    file_read, file_write, file_list,
    vision_inspect,   # ← Builder can inspect images when building reports
    mem_store, mem_query
], verbose=verbose)

critic = create_critic(llm=llm, tools=[
    file_read, file_write, file_list,
    vision_inspect,   # ← Critic can verify VLM outputs by re-inspecting images
    mem_query
], verbose=verbose)
```

### New: VisionCrew

For dedicated inspection workflows, create a `vision_crew.py` alongside the existing PLC and React crews:

```
Vision Crew flow:
  InspectionPlanner → VisionResearcher (YOLO + VLM) → DefectReporter → QualityReviewer
```

Where `VisionResearcher` has: `YOLODetectionTool`, `SAM2SegmentTool`, `VisionInspectionTool`, `FileWriteTool`

---

## 2. Multi-Modal Memory with ChromaDB

### How ChromaDB Handles Images

ChromaDB's multimodal support (Python only, built-in OpenCLIP embedding function) stores image URIs and their embeddings in the same vector space as text. This enables:
- **Text → Image search:** "show me previous surface scratch defects" → returns similar past inspection images
- **Image → Image search:** pass a new defect image → retrieve similar past defects
- **Cross-modal:** text description → find visually similar image in history

**Setup:**

```python
# memory/vision_memory.py
import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader

client = chromadb.PersistentClient(path="memory/chroma")

def get_inspection_collection():
    return client.get_or_create_collection(
        name="inspection_history",
        embedding_function=OpenCLIPEmbeddingFunction(),
        data_loader=ImageLoader()
    )

def store_inspection(inspection_id: str, image_path: str, result: dict):
    collection = get_inspection_collection()
    collection.add(
        ids=[inspection_id],
        uris=[image_path],           # ChromaDB loads + embeds the image
        documents=[result["summary"]],  # Text description for hybrid search
        metadatas=[{
            "action": result["action"],
            "severity": max((d["severity"] for d in result["defects"]), default="none"),
            "timestamp": result.get("timestamp", ""),
            "part_id": result.get("part_id", ""),
        }]
    )

def find_similar_defects(query_text: str = None, query_image_path: str = None, n=5):
    collection = get_inspection_collection()
    if query_image_path:
        # Image-to-image similarity search
        from PIL import Image
        import numpy as np
        img = np.array(Image.open(query_image_path))
        return collection.query(query_images=[img], n_results=n, include=["documents", "metadatas", "uris"])
    if query_text:
        return collection.query(query_texts=[query_text], n_results=n, include=["documents", "metadatas", "uris"])
```

**Important caveats:**
- ChromaDB's OpenCLIP embeddings capture visual semantics (scenes, objects, textures) but not fine-grained defect detail at pixel level. For defect similarity, combine OpenCLIP embeddings with defect JSON metadata filtering.
- ChromaDB's 2025 Rust-core rewrite delivers **4x faster writes and queries** — production-ready for inspection logging at volume.
- Multimodal support is currently **Python only** (no JS client for multimodal collections).

**Sources:**
- [ChromaDB Multimodal Embeddings Docs](https://docs.trychroma.com/docs/embeddings/multimodal)
- [ChromaDB GitHub](https://github.com/chroma-core/chroma)
- [OpenCLIP + ChromaDB guide](https://dev.to/sreeni5018/enhancing-ai-chatbots-with-multimodal-capabilities-using-chromadb-and-openai-clip-1534)

---

## 3. Chaining YOLO/SAM2 Detection with VLM Reasoning

### The InfraGPT Pattern (Production-Proven)

A 2025 paper (InfraGPT) documented a full working pipeline for infrastructure defect detection using CCTV streams:

```
Video stream → YOLO detection → SAM2 segmentation → VLM reasoning → JSON action plan
```

The VLM generates structured output including: incident description, recommended tools, estimated dimensions, repair plan, and urgency alerts. This is directly applicable to manufacturing inspection.

### Full Pipeline Implementation

```python
# tools/yolo_sam2_vlm_pipeline.py
from ultralytics import YOLO, SAM
import httpx
import base64
import json
from PIL import Image
import numpy as np

YOLO_MODEL = YOLO("yolov8n.pt")      # or a custom fine-tuned defect model
SAM2_MODEL = SAM("sam2_b.pt")

def inspect_image_full_pipeline(image_path: str, vlm_prompt: str) -> dict:
    """
    Stage 1: YOLO detects regions of interest
    Stage 2: SAM2 refines masks for each detection
    Stage 3: VLM reasons about each crop with context
    Stage 4: Aggregate into structured report
    """
    img = Image.open(image_path)

    # Stage 1: YOLO detection
    yolo_results = YOLO_MODEL(image_path, conf=0.3)
    boxes = yolo_results[0].boxes.xyxy.tolist()
    labels = [YOLO_MODEL.names[int(c)] for c in yolo_results[0].boxes.cls.tolist()]

    if not boxes:
        return {"pass": True, "defects": [], "summary": "No anomalies detected by YOLO", "action": "PASS"}

    # Stage 2: SAM2 segmentation on detected regions
    sam_results = SAM2_MODEL(image_path, bboxes=boxes)

    defects = []
    for i, (box, label, mask_result) in enumerate(zip(boxes, labels, sam_results)):
        x1, y1, x2, y2 = [int(v) for v in box]

        # Crop to bounding box + small padding
        pad = 20
        crop = img.crop((max(0, x1-pad), max(0, y1-pad), x2+pad, y2+pad))
        crop_b64 = _pil_to_b64(crop)

        # Stage 3: VLM analysis of each crop
        vlm_response = _call_vlm(
            image_b64=crop_b64,
            prompt=f"This is a crop from a manufacturing inspection. "
                   f"YOLO detected: '{label}'. {vlm_prompt} "
                   f"Respond with JSON: {{\"defect_type\": str, \"severity\": str, "
                   f"\"description\": str, \"confidence\": float}}"
        )
        try:
            defect_detail = json.loads(vlm_response)
        except json.JSONDecodeError:
            defect_detail = {"defect_type": label, "severity": "unknown",
                             "description": vlm_response, "confidence": 0.5}

        defects.append({
            **defect_detail,
            "bbox": [x1, y1, x2-x1, y2-y1],
            "yolo_label": label
        })

    # Stage 4: Final structured report
    max_severity = _max_severity(defects)
    action = "PASS" if not defects else ("REJECT" if max_severity == "high" else "REVIEW")

    return {
        "pass": action == "PASS",
        "defects": defects,
        "summary": f"Found {len(defects)} anomaly(ies). Max severity: {max_severity}.",
        "action": action
    }

def _pil_to_b64(img: Image.Image) -> str:
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()

def _call_vlm(image_b64: str, prompt: str) -> str:
    payload = {
        "model": "qwen3-vl:8b",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": prompt}
        ]}],
        "temperature": 0.1
    }
    r = httpx.post("http://localhost:11434/v1/chat/completions", json=payload, timeout=60)
    return r.json()["choices"][0]["message"]["content"]

def _max_severity(defects):
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    return max((d.get("severity", "unknown") for d in defects), key=lambda s: order.get(s, 0), default="none")
```

### YOLO + SAM2 for Video Frames

For continuous monitoring (conveyor belt inspection), the pipeline extends naturally to video:

```python
# Frame-by-frame inspection at configurable interval
import cv2

def inspect_video_stream(rtsp_url: str, frame_interval: int = 30):
    cap = cv2.VideoCapture(rtsp_url)
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            # Save frame, run pipeline
            frame_path = f"/tmp/frame_{frame_count}.jpg"
            cv2.imwrite(frame_path, frame)
            result = inspect_image_full_pipeline(frame_path, "Identify any surface defects.")
            if result["action"] != "PASS":
                yield result   # Alert the agent / log to ChromaDB
        frame_count += 1
```

**Sources:**
- [InfraGPT VLM Pipeline Paper (arxiv)](https://arxiv.org/html/2510.16017)
- [YOLO + SAM2 for Video Segmentation — Medium](https://medium.com/@genet.gessessew/supercharging-object-detection-combining-yolo-and-sam2-for-enhanced-video-segmentation-3a8c5e603430)
- [YOLO Defect Detection Guide](https://detectdefects.com/blog/2025/10/15/yolo-defect-detection/)
- [Depth-Enhanced YOLO-SAM2 (arxiv)](https://arxiv.org/html/2602.18961)

---

## 4. Structured JSON Output from VLMs

### Best Approach: vLLM + Outlines/xgrammar Guided Decoding

vLLM supports three backends for constrained output:
- **xgrammar** (default, fastest)
- **outlines** (most flexible)
- **lm-format-enforcer** (strict JSON schema)

```python
# Define Pydantic schema — VLM MUST return this structure
from pydantic import BaseModel
from typing import Literal

class DefectDetail(BaseModel):
    defect_type: str
    severity: Literal["low", "medium", "high", "critical"]
    location: str
    confidence: float
    bbox: list[int]  # [x, y, w, h]

class InspectionReport(BaseModel):
    part_id: str
    timestamp: str
    pass_fail: Literal["PASS", "REVIEW", "REJECT"]
    defects: list[DefectDetail]
    summary: str
    inspector_notes: str

# vLLM request with guided JSON
import json
payload = {
    "model": "qwen3-vl:8b",
    "messages": [...],
    "guided_json": InspectionReport.model_json_schema(),  # vLLM enforces this
    "temperature": 0.1
}
```

**With Ollama** (no guided decoding): use `format: "json"` parameter and rely on prompt engineering + model capability. Qwen3-VL and InternVL3 are reliable enough for consistent JSON output with clear prompts at temperature 0.1. For mission-critical structured output, prefer vLLM.

**Sources:**
- [vLLM Structured Outputs Docs](https://docs.vllm.ai/en/latest/features/structured_outputs/)
- [Structured Outputs with vLLM + Outlines — Vast.ai](https://vast.ai/article/structured-outputs-with-vllm-and-outlines-on-vast.ai)
- [Red Hat: Structured Outputs in vLLM](https://developers.redhat.com/articles/2025/06/03/structured-outputs-vllm-guiding-ai-responses)

---

## 5. Advanced Open-Source Agentic VLM Systems

### LangGraph Vision (LangChain ecosystem)

LangGraph is the most mature framework for stateful multi-agent workflows with vision support. Key pattern for inspection:

```python
from langgraph.graph import StateGraph
from typing import TypedDict, Optional
from PIL import Image

class InspectionState(TypedDict):
    image_path: str
    yolo_detections: Optional[list]
    vlm_analysis: Optional[dict]
    final_report: Optional[dict]

def yolo_node(state: InspectionState) -> InspectionState:
    # Run YOLO detection, add to state
    ...

def vlm_node(state: InspectionState) -> InspectionState:
    # Run VLM on crops from YOLO detections
    ...

def report_node(state: InspectionState) -> InspectionState:
    # Aggregate into final structured report
    ...

builder = StateGraph(InspectionState)
builder.add_node("detect", yolo_node)
builder.add_node("analyze", vlm_node)
builder.add_node("report", report_node)
builder.add_edge("detect", "analyze")
builder.add_edge("analyze", "report")
graph = builder.compile()
```

### AutoGen Multimodal

AutoGen (Microsoft) supports image inputs in messages natively. The `MultimodalConversableAgent` accepts PIL images or base64. For inspection, wire a `VisionAgent` that wraps the Ollama/vLLM endpoint and participates in a conversation with a `CriticAgent` that challenges low-confidence detections.

### WikiSeeker VLM Pattern (2025)

A 2025 paper introduced WikiSeeker, which uses VLMs as specialized **Refiner** and **Inspector** agents within a RAG pipeline. The Inspector-agent role is directly applicable to Smith_Agentic: the VLM-Inspector receives an image + preliminary analysis and returns a structured assessment with confidence scores. This pattern is implemented on top of standard LangGraph state graphs.

### Google ADK Multimodal

Google's Agent Development Kit (ADK, released April 2025) has the strongest **native** multimodal support among the major frameworks — agents process images, audio, and video natively through Gemini's API. Not relevant for a fully local/open-source stack, but worth monitoring for patterns.

**Source:**
- [Multi-Agent Frameworks 2026 Landscape — Adopt.AI](https://www.adopt.ai/blog/multi-agent-frameworks)
- [VLM Agent Frameworks — getmaxim.ai](https://www.getmaxim.ai/articles/top-5-ai-agent-frameworks-in-2025-a-practical-guide-for-ai-builders/)

---

## 6. Recommended Smith_Agentic Expansion: VisionCrew

Based on all research above, here is the concrete expansion to add to Smith_Agentic:

### New Files to Create

```
agents/vision_inspector.py       — VLM-powered inspection agent
agents/defect_reporter.py        — Structured reporting agent
tools/vision_tool.py             — VisionInspectionTool (calls Ollama VLM)
tools/yolo_tool.py               — YOLODetectionTool (runs YOLOv8)
tools/sam2_tool.py               — SAM2SegmentationTool
memory/vision_memory.py          — ChromaDB multimodal inspection history
crews/vision_crew.py             — Full inspection pipeline crew
```

### Crew Flow

```
VisionCrew:
  1. InspectionPlanner (Orchestrator)
     → breaks goal into inspection plan, selects which tools to use

  2. VisionInspector (new agent)
     Tools: YOLODetectionTool, SAM2SegmentationTool, VisionInspectionTool
     → detects, segments, analyzes defects
     → queries ChromaDB for similar past defects
     → saves structured JSON report to outputs/inspection_{id}.json

  3. DefectReporter (Builder variant)
     Tools: FileRead, FileWrite, VisionInspectionTool
     → reads JSON report, generates human-readable markdown report
     → saves outputs/report_{id}.md

  4. QualityReviewer (Critic variant)
     Tools: FileRead, FileWrite, VisionInspectionTool
     → reviews report for completeness and confidence
     → flags low-confidence detections for human review (HITL)
```

### Implementation Priority

| Component | Complexity | Value | Priority |
|---|---|---|---|
| `VisionInspectionTool` | Low | High | **1 — build first** |
| `vision_memory.py` (ChromaDB) | Low | High | **2** |
| `vision_crew.py` | Medium | High | **3** |
| YOLO+SAM2 pipeline | Medium | Medium | **4** |
| Video frame monitoring | Medium | Medium | **5** |
| Structured output (vLLM) | Low | Medium | **6** |
