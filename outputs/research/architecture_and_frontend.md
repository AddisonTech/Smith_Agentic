# Architecture & Frontend for a Local VLM Inspection Tool
## Cutting-Edge Stack — Mid-2026

---

## 1. Backend Inference: FastAPI + Ollama vs vLLM vs llama.cpp Server

The choice of inference backend has a significant impact on latency, concurrency, and complexity. Here are real benchmark numbers from 2025:

### Benchmark Comparison (Single A100-PCIE-40GB, tested with GuideLLM, 300s runs)

| Backend | Peak Throughput | P99 Latency (peak load) | TTFT | Best For |
|---|---|---|---|---|
| **vLLM 0.9.1** | 793 TPS | 80 ms | Stable at all loads | Production, concurrent users |
| **Ollama 0.9.2** | 41 TPS | 673 ms | Spikes under load | Dev, single-user, simplicity |
| **llama.cpp server** | ~20–50 TPS | More stable ITL at high load | Moderate | Stability-critical deployments |

**Key findings from the Red Hat benchmarks:**
- vLLM delivers **>35x the request throughput** of llama.cpp at peak load
- Ollama's inter-token latency becomes "extremely erratic with massive spikes" beyond ~10 concurrent users
- For a single-user inspection tool: Ollama and llama.cpp are perfectly adequate and dramatically simpler to operate
- For multi-station factory floor deployment (multiple cameras, multiple users): vLLM is the only reasonable choice

### Recommendation by Deployment Scenario

**Single workstation / developer / MVP:**
```
FastAPI → Ollama (OpenAI-compatible API on port 11434)
```
- Complexity: low
- Setup: `ollama pull qwen3-vl:8b && ollama serve`
- FastAPI calls `http://localhost:11434/v1/chat/completions` with image payload
- Token streaming works natively

**Production / multi-station / concurrent cameras:**
```
FastAPI → vLLM (OpenAI-compatible API on port 8000)
```
- Complexity: medium
- Setup: `vllm serve Qwen/Qwen3-VL-8B-Instruct --port 8000`
- Continuous batching handles multiple simultaneous inspection requests
- Structured output (JSON) via guided decoding built-in

**Maximum portability / embedded / Jetson:**
```
llama.cpp server (no FastAPI needed — serves OpenAI-compatible API directly)
```
- `llama-server -hf ggml-org/qwen3-vl-8b-GGUF --port 8080`
- React frontend hits llama.cpp server directly

### FastAPI Image Inference Pattern

```python
import base64
import httpx
from fastapi import FastAPI, UploadFile

app = FastAPI()
OLLAMA_URL = "http://localhost:11434/v1/chat/completions"

@app.post("/inspect")
async def inspect_image(file: UploadFile, prompt: str = "Describe any defects"):
    image_data = base64.b64encode(await file.read()).decode()
    
    payload = {
        "model": "qwen3-vl:8b",
        "stream": True,  # token-by-token streaming
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                {"type": "text", "text": prompt}
            ]
        }]
    }
    
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", OLLAMA_URL, json=payload) as response:
            async for chunk in response.aiter_text():
                yield chunk  # SSE stream to React frontend
```

**Sources:**
- [Ollama vs. vLLM Benchmark — Red Hat Developer](https://developers.redhat.com/articles/2025/08/08/ollama-vs-vllm-deep-dive-performance-benchmarking)
- [vLLM vs Ollama: Choosing the Right Engine — Red Hat](https://developers.redhat.com/articles/2025/09/30/vllm-or-llamacpp-choosing-right-llm-inference-engine-your-use-case)
- [Open-Source LLM Inference Engines 2026 — Fish Audio](https://fish.audio/blog/open-source-llm-inference-engines-2026/)

---

## 2. Real-Time Camera Feed in React

### Technology Decision Matrix

| Approach | Latency | Browser Support | IP Camera Support | Complexity |
|---|---|---|---|---|
| **WebRTC (native)** | <1 second | Native in all modern browsers | Via RTSP bridge | Medium |
| **RTSP → WebRTC bridge** | ~1–2 seconds | Full | ✅ Direct IP cam | Medium-High |
| **HTTP MJPEG stream** | 2–5 seconds | Full | ✅ Most IP cams | Low |
| **USB webcam (MediaDevices API)** | <100ms | Full | ❌ USB only | Low |
| **WebSocket video frames** | ~500ms | Full | Via FFmpeg | Medium |

### Recommended Architecture for Industrial Inspection

**For USB webcam (simplest, immediate):**
```javascript
// React component — MediaDevices API
const startWebcam = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 1920, height: 1080, frameRate: 30 }
  });
  videoRef.current.srcObject = stream;
};

// Capture frame for inspection
const captureFrame = () => {
  const canvas = canvasRef.current;
  canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
  return canvas.toDataURL('image/jpeg', 0.9);
};
```

**For IP cameras via RTSP (factory floor):**
Use [go2rtc](https://github.com/AlexxIT/go2rtc) or [mediamtx](https://github.com/bluenviron/mediamtx) as a zero-config RTSP → WebRTC bridge:

```bash
# mediamtx config: rtsp_to_webrtc.yml
paths:
  cam1:
    source: rtsp://192.168.1.100:554/stream
```

React then connects via WebRTC to `http://localhost:8889/cam1` — sub-second latency, full browser compatibility.

**For React WebRTC integration:**
[react-webcam](https://github.com/mozmorris/react-webcam) is the standard library. For multi-camera industrial setups, build directly on `navigator.mediaDevices` to enumerate all connected cameras.

### Inspection Capture Pattern

Don't send every frame to the VLM — that's expensive and slow. The production pattern:

1. Display live video in React at 30fps (browser handles this natively)
2. On trigger (button press, motion detection, PLC signal via WebSocket), capture one frame
3. POST the JPEG to FastAPI `/inspect` endpoint
4. Stream the VLM response tokens back via SSE
5. Display result alongside the captured frame

**Sources:**
- [WebRTC Complete Guide 2026 — Dacast](https://www.dacast.com/blog/webrtc-web-real-time-communication/)
- [Building a ReactJS Component for WebRTC — Ant Media](https://antmedia.io/building-a-reactjs-component-for-webrtc-live-streaming/)
- [WebRTC IoT Integration — VideoSDK](https://www.videosdk.live/developer-hub/webrtc/webrtc-control)

---

## 3. Image Annotation & Bounding Box Libraries for React

### Comparison of Active Libraries

| Library | Type | Stars | Last Active | Best For |
|---|---|---|---|---|
| **Annotorious** | JS/React/TS | Active | 2025 | Flexible, production-quality |
| **react-image-annotate** | React | ~1.5k | Stale (v1.8.0, 5 yrs ago) | Quick prototypes only |
| **react-bbox-annotator** | React | Small | Moderate | Lightweight bounding boxes |
| **annotate-lab** | Full-stack (React + server) | Growing | Active 2025 | Full annotation pipeline |
| **react-bounding-box** | React | Small | Moderate | Display-only overlays |

### Recommended: Annotorious

[Annotorious](https://annotorious.dev/) is the strongest active choice. It provides:
- Polygon, bounding box, and point annotations
- TypeScript support
- React integration via hooks
- OpenSeadragon support for high-resolution images (important for manufacturing — you need to zoom into 4K+ images)
- Clean export to W3C Web Annotation format

```javascript
import { Annotorious } from '@annotorious/react';

<Annotorious>
  <OpenSeadragonAnnotator>
    <OpenSeadragonViewer options={{ tileSources: imageUrl }} />
  </OpenSeadragonAnnotator>
</Annotorious>
```

### For Full Annotation Pipelines: annotate-lab

[annotate-lab](https://github.com/sumn2u/annotate-lab) is a full-stack open-source annotation tool built on React with flexible export options (COCO, YOLO, Pascal VOC). Useful for building your own labeled defect dataset to feed into LlamaFactory fine-tuning.

**VLM → Annotation integration pattern:**
1. VLM returns JSON with bounding boxes (x, y, w, h) + defect label
2. React renders boxes on canvas using `react-bounding-box` or a custom canvas component
3. Human reviewer can adjust boxes via Annotorious before saving
4. Approved annotations feed back into training dataset

---

## 4. Streaming Inference: Token-by-Token While the User Watches

### How Image + Text Streaming Works

VLMs process images differently from text. The flow:
1. Image is **fully encoded upfront** by the vision encoder (ViT) — this is not streamable, takes 200–500ms
2. Once image tokens are in context, **text generation begins and streams token-by-token** — fully streamable via SSE

So from the user's perspective: a brief pause (image encoding), then text appears incrementally. This is perceptually fast — users see results beginning in under a second.

### vLLM Streaming

vLLM supports both SSE and a new **WebSocket Realtime API** (`/v1/realtime` endpoint, added early 2026). For inspection tools, SSE is simpler:

```python
# FastAPI SSE endpoint
from fastapi.responses import StreamingResponse

@app.post("/inspect/stream")
async def inspect_stream(request: InspectRequest):
    async def generate():
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", VLLM_URL, json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield f"{line}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

```javascript
// React SSE consumer
const source = new EventSource('/inspect/stream');
source.onmessage = (e) => {
  const delta = JSON.parse(e.data).choices[0].delta.content;
  setResult(prev => prev + delta);
};
```

Ollama also supports streaming via the same OpenAI-compatible interface.

**Sources:**
- [vLLM Streaming and Realtime API](https://vllm.ai/blog/streaming-realtime)
- [vLLM Multimodal Inputs](https://docs.vllm.ai/en/latest/features/multimodal_inputs/)
- [SSE vs WebSockets for LLM Streaming](https://compute.hivenet.com/post/llm-streaming-sse-websockets)

---

## 5. Open-Source VLM Inspection UIs to Learn From

### fastVLM — Most Directly Relevant

**GitHub:** [github.com/o-messai/fastVLM](https://github.com/o-messai/fastVLM)

FastAPI backend + React.js frontend with live webcam streaming. Runs any Hugging Face VLM. Has an Action/Caption mode and frame control. Stack: FastAPI + Uvicorn + Transformers + ONNX Runtime + React + Material UI + TailwindCSS. Good reference architecture for the inspection tool pattern.

### Open WebUI

[Open WebUI](https://github.com/open-webui/open-webui) supports image attachments and streams responses. Compatible with Ollama and vLLM. Not inspection-specific but the WebSocket + streaming + multimodal pattern is production-tested.

### No Purpose-Built Industrial Inspection VLM UI Exists Yet

As of mid-2026, there is no polished open-source UI specifically for manufacturing VLM inspection. This is a gap — building one would be a strong portfolio differentiator. The closest is fastVLM, but it's a research prototype, not production software.

---

## 6. UI Patterns for Industrial Inspection Workflows

### Recommended Layout

```
┌─────────────────────────────────────────────────────────┐
│  Live Camera Feed          │  Captured Frame + Overlays │
│  [WebRTC 30fps stream]     │  [Bounding boxes + labels] │
│                            │                            │
│  [TRIGGER INSPECTION]      │  VLM Analysis (streaming)  │
│                            │  ● Defect: Surface scratch  │
│                            │  ● Location: Top-left quad  │
│                            │  ● Severity: MEDIUM        │
│                            │  ● Action: REJECT          │
├─────────────────────────────────────────────────────────┤
│  Inspection History        │  Defect Heatmap            │
│  [Scrollable card list]    │  [Canvas overlay showing   │
│  Pass/Fail/Review badges   │   defect frequency zones]  │
└─────────────────────────────────────────────────────────┘
```

**Key UI components:**
- **Trigger button** with loading state (disabled during VLM inference)
- **Side-by-side** live feed + analyzed frame
- **Bounding box overlay** rendered on canvas — not on the `<img>` element
- **Streaming text** for VLM analysis (use a typewriter component)
- **Pass/Fail badge** derived from structured JSON output
- **Heatmap** built from historical inspection results — use a canvas library (konva.js, fabric.js) to accumulate defect coordinates

### Defect Heatmap Pattern

```javascript
// Accumulate defect coordinates from past inspections
const updateHeatmap = (defects) => {
  defects.forEach(({ x, y, w, h }) => {
    ctx.fillStyle = 'rgba(255, 0, 0, 0.1)';
    ctx.fillRect(x, y, w, h);
  });
};
```

---

## 7. Edge Deployment: NVIDIA Jetson

### Jetson Board Selection Guide

| Board | VRAM | VLM Capability | Recommended Models | Target Use |
|---|---|---|---|---|
| **Jetson Orin Nano Super** | 8 GB | ≤4B params | Qwen3-VL-4B, VILA-3B | Basic visual monitoring |
| **Jetson AGX Orin** | 64 GB | 4B–20B params | Qwen3-VL-8B, LLaVA-13B | Full inspection station |
| **Jetson AGX Thor** | 128 GB | Up to ~120B | Llama 3.2 Vision 70B | High-accuracy multi-camera |

Confirmed benchmark: **40 tokens/sec** for a 20B model on Jetson AGX Orin via vLLM.

### Jetson Deployment Stack

```
Docker (NVIDIA runtime)
  └── vLLM (or Ollama) — serves VLM on port 8000
  └── FastAPI — inspection API on port 8080
  └── React (served via Nginx) — on port 80
  └── mediamtx — RTSP → WebRTC bridge for IP cameras
```

NVIDIA provides official Jetson Platform Services with VLM inference built in. NVIDIA Cosmos Nemotron (VILA family) is specifically optimized for Jetson with 4-bit AWQ quantization and negligible accuracy loss — it's the recommended starting point for Jetson deployment.

**Edge optimization:** Use TensorRT-LLM (NVIDIA's open-source C++ framework) for sub-30ms latency requirements. Available for Jetson Orin and the newer Jetson Thor platform.

**Sources:**
- [NVIDIA Jetson Edge AI VLM Blog](https://developer.nvidia.com/blog/getting-started-with-edge-ai-on-nvidia-jetson-llms-vlms-and-foundation-models-for-robotics/)
- [Jetson Platform Services VLM Docs](https://docs.nvidia.com/jetson/jps/inference-services/vlm.html)
- [Cosmos Nemotron Edge AI 2.0](https://developer.nvidia.com/blog/visual-language-intelligence-and-edge-ai-2-0/)
