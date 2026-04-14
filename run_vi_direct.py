"""
run_vi_direct.py — Direct Ollama generation for Vision_Inspect files.

CrewAI tool-use is broken with local Ollama (model outputs JSON tool calls
as Final Answer text instead of invoking tools). This script calls Ollama
directly per file. qwen2.5-coder authors all application code; this script
handles orchestration and file I/O.

Usage:
    python run_vi_direct.py --phase vi_a      # configs + infrastructure
    python run_vi_direct.py --phase vi_b      # backend core
    python run_vi_direct.py --phase vi_c      # backend utilities + main.py
    python run_vi_direct.py --phase vi_d      # React frontend
    python run_vi_direct.py --phase vi_e      # training + README
    python run_vi_direct.py --phase vi_commit # git commit + push
    python run_vi_direct.py --phase all       # run all build phases in order
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import requests

_HERE    = Path(__file__).resolve().parent
_VI_ROOT = _HERE.parent / "Vision_Inspect"
_OLLAMA  = "http://localhost:11434"
_CODE    = "qwen2.5-coder:7b"
_GEN     = "qwen2.5:7b"

_SYS = (
    "You are an expert software engineer writing production-quality code. "
    "Output ONLY the requested file content with no preamble, no trailing explanation, "
    "no markdown code fences, and no author attribution comments."
)


# ── Core helpers ──────────────────────────────────────────────────────────────

def _ollama(model: str, prompt: str, timeout: int = 300) -> str:
    payload = {
        "model": model,
        "system": _SYS,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 8192},
    }
    r = requests.post(f"{_OLLAMA}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "").strip()


def _clean(raw: str) -> str:
    """Strip any markdown code fences the model may have added."""
    s = raw.strip()
    s = re.sub(r"^```[\w]*\r?\n?", "", s, flags=re.MULTILINE)
    s = re.sub(r"\r?\n?```\s*$", "", s, flags=re.MULTILINE)
    return s.strip()


def _write(filepath: str, content: str) -> None:
    target = _VI_ROOT / filepath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"  \u2713 {filepath}  ({len(content.encode()):,} bytes)")


def _gen(filepath: str, model: str, prompt: str, timeout: int = 300) -> None:
    """Generate a file with Ollama and write it to Vision_Inspect."""
    if filepath.endswith(".gitkeep"):
        _write(filepath, "")
        return
    target = _VI_ROOT / filepath
    if target.exists() and target.stat().st_size > 20:
        print(f"  - skip {filepath} (exists)")
        return
    print(f"  \u2192 {filepath} ...")
    raw  = _ollama(model, prompt, timeout)
    text = _clean(raw)
    if not text:
        print(f"  ! WARNING: empty output for {filepath}")
        return
    _write(filepath, text + "\n")
    time.sleep(0.3)


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE VI-A  —  Config Files and Repo Infrastructure
# ══════════════════════════════════════════════════════════════════════════════

def phase_vi_a() -> None:
    print("\n=== Phase VI-A: Config Files ===\n")

    _gen(".gitignore", _GEN, """\
Write a .gitignore file for a Python + Node.js project. Include:
__pycache__/, *.pyc, .env, .venv, venv/, node_modules/, build/, dist/, .next/,
*.log, *.tmp, .DS_Store, Thumbs.db,
models/versions/*.onnx, models/versions/*.gguf,
outputs/inspection_reports/*.md, outputs/inspection_reports/*.png""")

    _gen("requirements.txt", _GEN, """\
Write a requirements.txt with exactly these packages, one per line:
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
websockets>=12.0
python-multipart>=0.0.9
pyyaml>=6.0.1
pillow>=10.3.0
opencv-python-headless>=4.9.0
numpy>=1.26.4
httpx>=0.27.0
requests>=2.31.0
aiofiles>=23.2.1
pydantic>=2.7.0
pydantic-settings>=2.2.1
onnxruntime>=1.18.0
scipy>=1.13.0""")

    _gen("configs/input_config.yaml", _GEN, """\
Write a YAML config file for Vision_Inspect input modes with this exact structure:

input:
  mode: live_camera
  manual_upload:
    enabled: true
    accepted_formats: [jpg, jpeg, png, bmp, tiff, mp4, avi, mkv]
    max_file_size_mb: 50
  live_camera:
    enabled: true
    device_index: 0
    stream_url: ""
    capture_width: 1280
    capture_height: 720
    fps: 30
    buffer_frames: 3
  scheduled_capture:
    enabled: false
    interval_seconds: 60
    duration_seconds: 5
  manual_trigger:
    enabled: true
    endpoint: /inspect""")

    _gen("configs/vlm_config.yaml", _GEN, """\
Write a YAML config for VLM model routing with this exact structure.
Include comments about quantization recommendations.

ollama:
  base_url: http://localhost:11434
  timeout_seconds: 120
  max_retries: 3

# Quant guide: Q5_K_M recommended, Q4_K_M acceptable, Q8_0 near-lossless, IQ3_M CPU fallback
primary_model:
  name: qwen3vl:8b
  quant: Q5_K_M
  context_length: 8192
  temperature: 0.1
  use_cases:
    - defect_detection
    - surface_anomaly_classification
    - engineering_drawing_interpretation
    - process_deviation_flagging

fallback_model:
  name: internvl3:8b
  quant: Q5_K_M
  temperature: 0.05
  use_cases:
    - nameplate_ocr
    - serial_number_extraction
    - label_reading
    - high_resolution_text

routing:
  ocr_task_types:
    - nameplate_ocr
    - serial_number_extraction
    - label_reading
  retry_below_confidence: 0.65""")

    _gen("configs/inspection_config.yaml", _GEN, """\
Write a YAML config for inspection parameters with this exact structure:

preprocessing:
  brightness_target: 128
  brightness_tolerance: 30
  contrast_min: 0.4
  resize_max_dimension: 1024
  normalize: true

defect_detection:
  sensitivity: 0.72
  min_defect_area_px: 25
  ignore_regions: []

surface_anomaly:
  sensitivity: 0.68
  classes_to_ignore: []

ocr:
  min_confidence: 0.80
  expected_formats:
    serial_number: "^[A-Z0-9\\-]{6,20}$"
    nameplate_fields:
      - manufacturer
      - model_number
      - serial_number
      - voltage
      - current
      - power

process_deviation:
  sensitivity: 0.60
  reference_image_path: ""
  max_deviation_percent: 15

video:
  frame_sample_interval: 5
  drift_window_frames: 30
  anomaly_trend_threshold: 3""")

    _gen("configs/notification_config.yaml", _GEN, """\
Write a YAML config for notifications with this exact structure:

notifications:
  enabled: true
  severity_thresholds:
    teams: high
    email: critical
  teams:
    enabled: false
    webhook_url: ""
    mention_channel: false
  email:
    enabled: false
    smtp_host: smtp.example.com
    smtp_port: 587
    smtp_use_tls: true
    smtp_username: ""
    smtp_password: ""
    from_address: ""
    recipients:
      - ""
  message_template:
    subject: "Vision_Inspect Alert [{severity}] - {input_source}"
    body_prefix: "Vision_Inspect has detected an anomaly requiring human review."
""")

    _gen("models/versions/.gitkeep",          _GEN, "")
    _gen("outputs/inspection_reports/.gitkeep", _GEN, "")
    _gen("training/.gitkeep",                  _GEN, "")

    print("\nPhase VI-A complete.")


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE VI-B  —  Backend Core Python Files
# ══════════════════════════════════════════════════════════════════════════════

def phase_vi_b() -> None:
    print("\n=== Phase VI-B: Backend Core ===\n")

    _gen("backend/__init__.py", _CODE,
         'Write a Python module __init__.py with only a module docstring: "Vision_Inspect backend package."')

    _gen("backend/pipeline/__init__.py", _CODE,
         'Write a Python module __init__.py with only a module docstring: "Vision_Inspect modular inspection pipeline."')

    _gen("backend/config_loader.py", _CODE, """\
Write a complete Python module backend/config_loader.py for the Vision_Inspect project.

The configs/ directory is located at:
    Path(__file__).resolve().parent.parent / "configs"

Write four functions, each loading one YAML file using yaml.safe_load():
  load_input_config() -> dict        # reads input_config.yaml
  load_vlm_config() -> dict          # reads vlm_config.yaml
  load_inspection_config() -> dict   # reads inspection_config.yaml
  load_notification_config() -> dict # reads notification_config.yaml

Include imports: pathlib.Path, yaml. No other dependencies.""")

    _gen("backend/hardware_abstraction.py", _CODE, """\
Write a complete Python module backend/hardware_abstraction.py for Vision_Inspect.

Implement two functions:

get_onnx_providers() -> list[str]:
  Try to import onnxruntime.providers and check for CUDAExecutionProvider.
  Try OpenVINOExecutionProvider.
  Always include CPUExecutionProvider.
  Return list of available providers (most capable first).

get_device_info() -> dict:
  Return a dict with keys:
    provider: str   (first available from get_onnx_providers())
    cuda_available: bool
    cpu_count: int  (os.cpu_count())

Import: os, logging. Use try/except for optional providers.""")

    _gen("backend/pipeline/ingestion.py", _CODE, """\
Write a complete Python module backend/pipeline/ingestion.py for Vision_Inspect.

Imports: cv2, numpy as np, PIL.Image, io, base64, datetime, dataclasses, pathlib, tempfile, os

@dataclass class IngestResult:
    frames: list          # list of numpy arrays (BGR)
    source_type: str      # manual_upload | live_camera | scheduled | manual_trigger
    source_path: str
    timestamp: str        # ISO 8601
    frame_count: int
    width: int
    height: int

class Ingester:
    def __init__(self, config: dict):
        Store config. Extract device_index (default 0), stream_url (default ""),
        buffer_frames (default 3), duration_seconds (default 5).

    def ingest_upload(self, file_bytes: bytes, filename: str) -> IngestResult:
        Detect video vs image from filename extension (.mp4 .avi .mkv = video).
        For images: open with PIL.Image, convert to numpy BGR array.
        For videos: write bytes to a temp file, use cv2.VideoCapture to read all frames.
        Return IngestResult with source_type="manual_upload".

    def ingest_camera_frame(self) -> IngestResult:
        Open cv2.VideoCapture(stream_url if stream_url else device_index).
        Read buffer_frames frames (discard all but last to flush buffer).
        Release capture. Return IngestResult with source_type="live_camera".
        On failure: return IngestResult with empty frames list.

    def ingest_scheduled(self) -> IngestResult:
        Same as ingest_camera_frame but source_type="scheduled".

    def ingest_manual_trigger(self) -> IngestResult:
        Same as ingest_camera_frame but source_type="manual_trigger".

Helper: _now() -> str returning datetime.datetime.now().isoformat()""")

    _gen("backend/pipeline/preprocessing.py", _CODE, """\
Write a complete Python module backend/pipeline/preprocessing.py for Vision_Inspect.

Imports: cv2, numpy as np, base64

def preprocess_frame(frame: np.ndarray, config: dict) -> np.ndarray:
    Read preprocessing config (brightness_target=128, brightness_tolerance=30,
    resize_max_dimension=1024, normalize=True from config dict).
    1. Brightness adjustment: compute mean pixel value. If abs(mean - target) > tolerance,
       scale frame by (target / mean), clip to [0, 255].
    2. Resize: if max(h, w) > resize_max_dimension, scale proportionally with cv2.resize.
    3. Normalize: if normalize True, convert to float32 and divide by 255.0.
    Return processed frame.

def frame_to_base64(frame: np.ndarray) -> str:
    Encode frame as JPEG using cv2.imencode. Return base64.b64encode as UTF-8 string.
    If frame is float32, convert to uint8 first (multiply by 255 if max <= 1.0).

def preprocess_batch(frames: list, config: dict) -> list:
    Return [preprocess_frame(f, config) for f in frames]""")

    _gen("backend/pipeline/inference.py", _CODE, """\
Write a complete Python module backend/pipeline/inference.py for Vision_Inspect.

Imports: requests, json, time, datetime, dataclasses, numpy as np
from backend.config_loader import load_vlm_config
from backend.pipeline.preprocessing import frame_to_base64

TASK_PROMPTS: dict mapping task type strings to inspection prompts.
Keys: defect_detection, surface_anomaly_classification, nameplate_ocr,
serial_number_extraction, engineering_drawing_interpretation, process_deviation_flagging.
Each prompt instructs the model to return JSON with: findings list, pass_fail ("PASS"/"FAIL"),
confidence float (0.0-1.0), and notes string.

@dataclass class InferenceResult:
    task_type: str
    model_used: str
    raw_response: str
    findings: list
    confidence_scores: list
    latency_ms: float
    timestamp: str

class VLMInferenceEngine:
    def __init__(self, vlm_config: dict):
        Store config.

    def _get_model_for_task(self, task_type: str) -> str:
        Return fallback_model name for OCR task types (nameplate_ocr,
        serial_number_extraction, label_reading), primary_model name for others.

    def _call_ollama(self, model: str, prompt: str, image_b64: str) -> dict:
        POST to config ollama.base_url + /api/generate with:
          model=model, prompt=prompt, images=[image_b64], stream=False
        Timeout from config. Handle RequestException gracefully (return empty dict).
        Return response.json() or empty dict on error.

    def run_inspection(self, frames: list, task_type: str,
                       inspection_config: dict) -> InferenceResult:
        Get model and prompt. Preprocess first frame to base64.
        Record start time. Call _call_ollama. Compute latency_ms.
        Try to parse JSON from response.get("response", "").
        Extract findings list and confidence.
        If confidence < routing.retry_below_confidence: retry with fallback model.
        Return InferenceResult with all fields populated.""")

    _gen("backend/pipeline/monitoring.py", _CODE, """\
Write a complete Python module backend/pipeline/monitoring.py for Vision_Inspect.

Imports: collections, statistics

class FrameMonitor:
    def __init__(self, config: dict):
        self._config = config
        self._history = collections.deque(
            maxlen=config.get("video", {}).get("drift_window_frames", 30))

    def update(self, result) -> dict:
        Append result to _history.
        Compute anomaly_trend: count of results in history where pass_fail == "FAIL".
          Support both dataclass (getattr) and dict (result.get) result types.
        Compute mean_confidence: mean of all confidence_scores across history.
          Support both dataclass (.confidence_scores list) and dict (".confidence" key).
        drift_detected = anomaly_trend >= config.get("video", {}).get("anomaly_trend_threshold", 3)
        Return dict: anomaly_trend, mean_confidence, drift_detected.

    def get_trend_summary(self) -> dict:
        h = list(self._history)
        n = len(h)
        if n == 0:
            return dict(frame_count_analyzed=0, anomaly_rate=0.0,
                       mean_confidence=0.0, drift_detected=False,
                       consecutive_anomaly_windows=0)
        anomaly_count = sum(1 for r in h if
            (getattr(r, "pass_fail", None) or r.get("pass_fail", "PASS") if isinstance(r, dict) else "PASS") == "FAIL")
        confs = []
        for r in h:
            cs = getattr(r, "confidence_scores", None)
            if cs: confs.extend(cs)
            else:
                c = r.get("confidence", 0.5) if isinstance(r, dict) else 0.5
                confs.append(c)
        mean_conf = statistics.mean(confs) if confs else 0.0
        drift = anomaly_count >= self._config.get("video", {}).get("anomaly_trend_threshold", 3)
        return dict(
            frame_count_analyzed=n,
            anomaly_rate=round(anomaly_count / n, 3),
            mean_confidence=round(mean_conf, 4),
            drift_detected=drift,
            consecutive_anomaly_windows=anomaly_count,
        )""")

    print("\nPhase VI-B complete.")


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE VI-C  —  Backend Utilities + main.py
# ══════════════════════════════════════════════════════════════════════════════

def phase_vi_c() -> None:
    print("\n=== Phase VI-C: Backend Utilities ===\n")

    _gen("backend/vlm_router.py", _CODE, """\
Write a complete Python module backend/vlm_router.py for Vision_Inspect.

Imports: requests, json, time, logging
from backend.config_loader import load_vlm_config

class VLMRouter:
    def __init__(self, config: dict = None):
        self._cfg = config or load_vlm_config()

    def get_model(self, task_type: str) -> str:
        Return fallback_model name if task_type in routing.ocr_task_types,
        else primary_model name.

    def build_prompt(self, task_type: str) -> str:
        Return an inspection prompt for each task_type. Prompts instruct the model
        to return JSON with: findings (list of dicts with label, confidence, severity,
        description), confidence (float 0-1), pass_fail ("PASS" or "FAIL"), notes (str).
        Handle all 6 task types: defect_detection, surface_anomaly_classification,
        nameplate_ocr, serial_number_extraction, engineering_drawing_interpretation,
        process_deviation_flagging.

    def call(self, task_type: str, image_b64: str, timeout: int = 120) -> dict:
        base_url = self._cfg["ollama"]["base_url"]
        model = self.get_model(task_type)
        prompt = self.build_prompt(task_type)
        start = time.time()
        resp = requests.post(base_url + "/api/generate",
            json=dict(model=model, prompt=prompt, images=[image_b64], stream=False),
            timeout=timeout)
        latency_ms = round((time.time() - start) * 1000, 2)
        raw = resp.json().get("response", "")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = dict(findings=[], confidence=0.0, pass_fail="UNKNOWN", raw=raw)
        data["model"] = model
        data["task_type"] = task_type
        data["latency_ms"] = latency_ms
        return data""")

    _gen("backend/proxy_metrics.py", _CODE, """\
Write a complete Python module backend/proxy_metrics.py for Vision_Inspect.

Imports: collections, statistics, logging

class ProxyMetricsCollector:
    def __init__(self, window_size: int = 50):
        self._latency: collections.deque = collections.deque(maxlen=window_size)
        self._confidence: collections.deque = collections.deque(maxlen=window_size)

    def record(self, latency_ms: float, confidence: float) -> None:
        Append to both deques.

    def get_metrics(self) -> dict:
        If empty: return zeros dict with keys: mean_latency_ms, p95_latency_ms,
        mean_confidence, confidence_std, confidence_drift_alert (False),
        distribution_shift_score (0.0), distribution_shift_alert (False), sample_count (0).
        Otherwise compute:
          mean_latency_ms, p95_latency_ms (index int(len*0.95) of sorted list),
          mean_confidence, confidence_std (stdev if >1 sample else 0),
          shift = abs(mean_confidence - 0.5) * confidence_std,
          confidence_drift_alert = confidence_std > 0.15,
          distribution_shift_alert = shift > 0.3.
        Return all as dict with rounded values.

    def detect_silent_failures(self) -> list[str]:
        Return warning strings for:
          - latency spike: last latency > mean * 3
          - confidence collapse: mean_confidence < 0.4
          - distribution shift: distribution_shift_alert is True
        Only check when sample_count > 5.

    def to_report_section(self) -> str:
        Return markdown table string of metrics and Active Warnings list.

_collector = ProxyMetricsCollector()

def get_metrics_collector() -> ProxyMetricsCollector:
    return _collector

def record_inference(latency_ms: float, confidence: float) -> None:
    _collector.record(latency_ms, confidence)""")

    _gen("backend/notifier.py", _CODE, """\
Write a complete Python module backend/notifier.py for Vision_Inspect.

Imports: smtplib, json, logging, requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.config_loader import load_notification_config

SEVERITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
TEAMS_COLORS = {"critical": "FF0000", "high": "FF6600", "medium": "FFCC00", "low": "00CC00"}

class Notifier:
    def __init__(self, config: dict = None):
        self._cfg = config or load_notification_config()

    def should_notify(self, severity: str, channel: str) -> bool:
        Compare SEVERITY_LEVELS of severity vs threshold for channel.

    def send_teams(self, subject: str, body: str, severity: str) -> bool:
        If not enabled: return False.
        POST MessageCard JSON to webhook_url. themeColor from TEAMS_COLORS.
        Return True on 200, False on exception.

    def send_email(self, subject: str, body: str, recipients: list) -> bool:
        If not enabled: return False.
        Build MIMEMultipart, connect to SMTP with TLS, send.
        Return True on success, False on exception.

    def notify(self, finding: dict, report_path: str) -> None:
        Build subject and body from message_template (format severity and source).
        Call send_teams if should_notify severity/teams.
        Call send_email if should_notify severity/email.""")

    _gen("backend/model_versioning.py", _CODE, """\
Write a complete Python module backend/model_versioning.py for Vision_Inspect.

Imports: json, pathlib, datetime, logging
from pathlib import Path

class ModelVersionManager:
    def __init__(self, versions_dir: Path):
        self.versions_dir = versions_dir
        versions_dir.mkdir(parents=True, exist_ok=True)

    def list_versions(self) -> list:
        Iterate sorted subdirs of versions_dir. For each dir with model_info.json,
        load the JSON, add "active" bool (True if .active marker file exists).
        Return list of dicts.

    def get_active_version(self):
        Return first version where active is True, or None.

    def set_active_version(self, version: str) -> bool:
        Remove all .active marker files. Create .active in versions_dir/version.
        Return False if version dir doesn't exist.

    def create_version(self, model_name: str, notes: str = "") -> dict:
        tag = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        Create vdir = versions_dir / tag. Write model_info.json with
        version, model_name, created_at (ISO), notes.
        Return the info dict.

    def rollback(self, version: str) -> bool:
        Call set_active_version. Log the rollback. Return result.

def get_version_manager() -> ModelVersionManager:
    vi_root = Path(__file__).resolve().parent.parent
    return ModelVersionManager(vi_root / "models" / "versions")""")

    _gen("backend/report_generator.py", _CODE, """\
Write a complete Python module backend/report_generator.py for Vision_Inspect.

Imports: pathlib, datetime, logging
from pathlib import Path

def get_reports_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "outputs" / "inspection_reports"

def generate_report(job_id: str, input_source: str, inference_result: dict,
                    proxy_metrics: dict, model_version: str,
                    annotated_image_path: str = None) -> str:
    Build a markdown report string with these sections:
    # Vision_Inspect Report — {timestamp}
    **Job ID**, **Input Source**, **Model Version**, **Model Used**
    ## Findings  (markdown table with Label|Confidence|Severity|Description, or "*No findings.*")
    ## Pass/Fail Verdict  (PASS or FAIL)
    ## Proxy Metrics  (dict formatted as key: value lines or proxy_metrics string)
    ## Annotated Frame  (![]({path}) or "*No annotated frame available.*")
    ## Recommended Human Actions  (list of actions based on findings, or "No action required")
    ---
    *This report is for human review only. Vision_Inspect makes no automated decisions.*

    Save report to get_reports_dir() / f"{job_id}.md" (create dir if needed).
    Return the report string.""")

    _gen("backend/main.py", _CODE, """\
Write a complete Python module backend/main.py implementing a FastAPI application for Vision_Inspect.

Imports:
    fastapi: FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
    fastapi.middleware.cors: CORSMiddleware
    fastapi.responses: JSONResponse
    uvicorn
    uuid, json, asyncio, pathlib, logging
    from backend.config_loader import load_vlm_config, load_input_config
    from backend.vlm_router import VLMRouter
    from backend.pipeline.ingestion import Ingester
    from backend.pipeline.preprocessing import preprocess_frame, frame_to_base64
    from backend.proxy_metrics import record_inference, get_metrics_collector
    from backend.report_generator import generate_report, get_reports_dir
    from backend.model_versioning import get_version_manager
    from backend.notifier import Notifier

app = FastAPI(title="Vision_Inspect", version="1.0.0")
Add CORSMiddleware with allow_origins=["*"], allow_methods=["*"], allow_headers=["*"].

class ConnectionManager:
    __init__: self.active = []
    connect(ws): await ws.accept(), append
    disconnect(ws): remove from active
    broadcast(msg: dict): json.dumps, send_text to all, remove dead connections

manager = ConnectionManager()
_job_store: dict = {}
Lazy singletons: _get_vlm() -> VLMRouter, _get_ingester() -> Ingester

Endpoints:
POST /upload  (file: UploadFile, task_type: str = "defect_detection")
    job_id = uuid4()[:8], read bytes, ingest_upload, vlm.call, record_inference,
    get_metrics, get_version, generate_report, store in _job_store, broadcast result.
    Return {job_id, status, task_type, finding_count}.

POST /inspect  (body: dict with task_type and source)
    Similar to upload but uses ingest_camera_frame or ingest_manual_trigger.
    Return {job_id, status}.

GET /results/{job_id}  -> 404 if not found, else job data

POST /report/{job_id}  -> generate and return {report_path, report_content}

GET /reports  -> list of {filename, size_bytes} for all .md in reports dir

GET /models/versions  -> list_versions()

POST /models/rollback  (body: {"version": str})  -> rollback or 404

GET /health  -> {status: "ok", ollama_reachable: bool}

WebSocket /ws/stream
    On connect: add to manager. Loop: receive_text, parse JSON, ingest_camera_frame,
    vlm.call, broadcast result. On disconnect: remove from manager.

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)""", timeout=600)

    print("\nPhase VI-C complete.")


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE VI-D  —  React Frontend
# ══════════════════════════════════════════════════════════════════════════════

def phase_vi_d() -> None:
    print("\n=== Phase VI-D: React Frontend ===\n")

    _gen("frontend/package.json", _GEN, """\
Write this exact JSON for a React + MUI v5 + TypeScript project:
{
  "name": "vision-inspect-ui",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@emotion/react": "^11.11.4",
    "@emotion/styled": "^11.11.5",
    "@mui/material": "^5.15.20",
    "@mui/icons-material": "^5.15.20",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.12.7",
    "axios": "^1.7.2",
    "react-scripts": "5.0.1",
    "typescript": "^4.9.5"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  },
  "browserslist": {
    "production": [">0.2%", "not dead"],
    "development": ["last 1 chrome version"]
  },
  "proxy": "http://localhost:8000"
}""")

    _gen("frontend/tsconfig.json", _GEN, """\
Write a standard Create React App TypeScript tsconfig.json with:
compilerOptions: target ES6, lib [dom,dom.iterable,esnext], allowJs true,
skipLibCheck true, esModuleInterop true, allowSyntheticDefaultImports true,
strict false, jsx react-jsx, moduleResolution node, baseUrl src.
include: ["src"]""")

    _gen("frontend/src/theme/theme.ts", _CODE, """\
Write a MUI v5 dark industrial theme file for Vision_Inspect.

Import createTheme from @mui/material/styles.

Create and export default a theme with:
- palette.mode: "dark"
- background.default: "#0d0d0d", background.paper: "#1a1a1a"
- primary.main: "#f59e0b"  (amber — industrial warning color)
- secondary.main: "#22d3ee"  (cyan — data color)
- error.main: "#ef4444"
- success.main: "#22c55e"
- text.primary: "#e5e7eb", text.secondary: "#9ca3af"
- typography.fontFamily: "JetBrains Mono, Consolas, monospace" """)

    _gen("frontend/src/types.ts", _CODE, """\
Write TypeScript type definitions for Vision_Inspect frontend.

Export these interfaces:
  InspectionFinding { label: string; confidence: number; severity: string; bbox?: number[]; description: string; }
  InspectionResult { job_id: string; timestamp: string; model_used: string; pass_fail: string; findings: InspectionFinding[]; notes: string; }
  ProxyMetrics { mean_latency_ms: number; mean_confidence: number; confidence_drift_alert: boolean; distribution_shift_alert: boolean; sample_count: number; }
  Report { filename: string; size_bytes: number; }""")

    _gen("frontend/src/api.ts", _CODE, """\
Write an axios-based API client for Vision_Inspect frontend (TypeScript).

Import axios, InspectionResult, Report from ./types.
Create axios instance with baseURL "/api".

Export:
  uploadImage(file: File, taskType: string): Promise<InspectionResult>
    Use FormData, POST /upload?task_type=taskType, return r.data.
  triggerInspection(taskType: string, source: string): Promise<any>
    POST /inspect with {task_type, source}.
  getResults(jobId: string): Promise<any>
    GET /results/{jobId}.
  generateReport(jobId: string): Promise<any>
    POST /report/{jobId}.
  listReports(): Promise<Report[]>
    GET /reports.
  getHealth(): Promise<any>
    GET /health.""")

    _gen("frontend/src/hooks/useWebSocket.ts", _CODE, """\
Write a React custom hook useWebSocket(url: string) in TypeScript.

State: connected (bool), lastMessage (any), error (string|null).
useRef for WebSocket instance.
useEffect: create WebSocket, set onopen/onmessage/onerror/onclose handlers.
  onmessage: JSON.parse the data, setLastMessage.
  onclose: setConnected(false), reconnect after 3000ms.
  onopen: setConnected(true).
  onerror: setError("WebSocket error").
Cleanup: close WebSocket on unmount.
Return { connected, lastMessage, error }.""")

    _gen("frontend/src/components/CameraFeed.tsx", _CODE, """\
Write a React TypeScript component CameraFeed.tsx using MUI v5.

Props: { imageUrl?: string; streaming: boolean; onTrigger: () => void; }

Render a Card with:
- Header with VideocamIcon and "Live Feed" title in primary.main color
- Dark Box (bgcolor #000, min-height 200) showing either the image or "No feed available" text
  with a CircularProgress overlay when streaming
- "Trigger Inspection" Button (contained, primary, fullWidth) that calls onTrigger,
  disabled when streaming, text changes to "Inspecting..." when streaming

Import from @mui/material: Card, CardContent, Typography, Button, Box, CircularProgress
Import VideocamIcon from @mui/icons-material/Videocam""")

    _gen("frontend/src/components/DefectOverlay.tsx", _CODE, """\
Write a React TypeScript component DefectOverlay.tsx using MUI v5.

Props: { imageUrl: string; findings: InspectionFinding[]; }

Severity color map: critical #ef4444, high #f97316, medium #eab308, low #22d3ee.

Render a relative-positioned Box with the image as background.
For each finding that has a bbox (x1,y1,x2,y2 as percentages):
  Render an absolutely positioned Box with border in severity color.
  Show a label caption with severity background color, label text and confidence %.

Import InspectionFinding from ../types.
Import from @mui/material: Box, Typography.""")

    _gen("frontend/src/components/InspectionResults.tsx", _CODE, """\
Write a React TypeScript component InspectionResults.tsx using MUI v5.

Props: { result?: InspectionResult; loading: boolean; }

If loading: return Card with Skeleton height=200.
Otherwise render a Card with:
- "Inspection Results" heading
- If result: Chip with pass_fail label (color success/error), timestamp and model_used caption
  If result.findings.length > 0: Table (size small) with columns Label/Confidence/Severity/Description
- If no result: "No results yet." text

Import InspectionResult from ../types.
Import from @mui/material: Card, CardContent, Typography, Chip, Table, TableHead, TableRow, TableCell, TableBody, Skeleton.""")

    _gen("frontend/src/components/ProxyMetrics.tsx", _CODE, """\
Write a React TypeScript component ProxyMetrics.tsx using MUI v5.

Props: { metrics?: ProxyMetrics; }  (import ProxyMetrics as PM from ../types)

If no metrics: return null.

Render a Card with "Proxy Metrics" heading and a Stack of Chips:
- Latency chip: label "Latency: {ms}ms", color success if <500ms, warning if <2000ms, error otherwise
- Confidence chip: label "Confidence: {pct}%", color success if >70%, warning if >40%, error otherwise
- Drift chip: "Drift: ALERT" (warning) or "Drift: OK" (success)
- Shift chip: "Shift: ALERT" (warning) or "Shift: OK" (success)

Import from @mui/material: Card, CardContent, Typography, Chip, Stack.""")

    _gen("frontend/src/components/ProcessTrends.tsx", _CODE, """\
Write a React TypeScript component ProcessTrends.tsx using MUI v5 and Recharts.

Interface DataPoint { timestamp: string; confidence: number; anomaly_rate: number; }
Props: { data: DataPoint[]; }

Render a Card with "Process Trends" heading and a Recharts LineChart (ResponsiveContainer width=100% height=200):
- CartesianGrid strokeDasharray="3 3" stroke="#333"
- XAxis dataKey="timestamp" with dark tick style
- Two YAxis (left: confidence domain [0,1], right: anomaly_rate domain [0,1])
- Tooltip with dark background
- Legend
- Line for confidence (cyan #22d3ee, yAxisId="left", dot=false)
- Line for anomaly_rate (amber #f59e0b, yAxisId="right", dot=false)

Import from @mui/material: Card, CardContent, Typography.
Import from recharts: LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer.""")

    _gen("frontend/src/components/ReportHistory.tsx", _CODE, """\
Write a React TypeScript component ReportHistory.tsx using MUI v5.

Props: { reports: Report[]; onDownload: (filename: string) => void; }

Render a Card with "Report History" heading.
If no reports: show "No reports yet." text.
Otherwise show a dense List of reports with:
  - ListItemText: primary=filename, secondary="{size_kb} KB"
  - Secondary action: IconButton with DownloadIcon (secondary.main color) calling onDownload

Import Report from ../types.
Import from @mui/material: Card, CardContent, Typography, List, ListItem, ListItemText, IconButton.
Import DownloadIcon from @mui/icons-material/Download.""")

    _gen("frontend/src/App.tsx", _CODE, """\
Write a complete React TypeScript App.tsx for Vision_Inspect with MUI v5 dark industrial theme.

Imports: React, useState, useEffect, useCallback, useRef
ThemeProvider, CssBaseline, Grid, AppBar, Toolbar, Typography,
Select, MenuItem, Button, Chip, Box from @mui/material
theme from ./theme/theme
All 6 components: CameraFeed, DefectOverlay, InspectionResults, ProxyMetrics, ProcessTrends, ReportHistory
useWebSocket from ./hooks/useWebSocket
{ uploadImage, triggerInspection, getResults, listReports, getHealth } from ./api
{ InspectionResult, Report } from ./types

State:
  result: InspectionResult | undefined
  loading: boolean (false)
  reports: Report[] ([])
  trendData: DataPoint[] ([])  where DataPoint = {timestamp, confidence, anomaly_rate}
  taskType: string ("defect_detection")
  health: any (null)

const { connected, lastMessage } = useWebSocket("ws://localhost:8000/ws/stream")
useEffect: when lastMessage has type=="result", setResult(lastMessage.data)
useEffect on mount: listReports().then(setReports), getHealth().then(setHealth)

handleUpload: FileReader or direct — on file input change, call uploadImage(file, taskType),
  setLoading(true), on result setResult + add to trendData + reload reports.

handleTrigger: call triggerInspection(taskType, "camera"), setLoading(true),
  then getResults(job.job_id), setResult, setLoading(false).

fileInputRef = useRef<HTMLInputElement>(null)

Layout wrapped in ThemeProvider + CssBaseline:
  AppBar: title "Vision_Inspect | Local Process Monitor",
    Chip showing WS connected/disconnected,
    Chip showing ollama status from health.

  Box with padding 2:
    Grid container spacing=2:
      xs=12 md=4: CameraFeed + (result with bbox findings -> DefectOverlay)
      xs=12 md=4: Select for taskType (options: defect_detection/surface_anomaly_classification/nameplate_ocr/serial_number_extraction/engineering_drawing_interpretation/process_deviation_flagging),
                  Upload Button + hidden file input,
                  InspectionResults,
                  ProxyMetrics (extract from result.proxy_metrics if present)
      xs=12 md=4: ProcessTrends, ReportHistory

export default App""", timeout=600)

    _gen("frontend/src/index.tsx", _CODE, """\
Write frontend/src/index.tsx — the React application entry point.

Import React from "react", ReactDOM from "react-dom/client", App from "./App".
Create root with ReactDOM.createRoot(document.getElementById("root") as HTMLElement).
Render <React.StrictMode><App /></React.StrictMode>.""")

    print("\nPhase VI-D complete.")


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE VI-E  —  Training Scaffold + README
# ══════════════════════════════════════════════════════════════════════════════

def phase_vi_e() -> None:
    print("\n=== Phase VI-E: Training + README ===\n")

    _gen("training/dataset_template.json", _GEN, """\
Write a JSON array with 3 training conversation examples for fine-tuning a VLM on manufacturing inspection.

Format: array of objects, each with "conversations" array.
Each conversation has "from" ("human" or "gpt") and "value" fields.

Example 1: Defect detection — human turn has image path + prompt asking for JSON defect analysis,
gpt turn returns JSON with findings (list with label/confidence/severity/bbox/description), pass_fail, confidence.

Example 2: Nameplate OCR — human asks to extract text from nameplate image,
gpt returns JSON with manufacturer, model_number, serial_number, voltage, current found.

Example 3: Process deviation — human asks to compare current state to expected process state,
gpt returns JSON with deviation detected, confidence, description, pass_fail.

Make the examples realistic for a manufacturing shop floor context.""")

    _gen("training/llama_factory_qlora.yaml", _GEN, """\
Write a LlamaFactory QLoRA training config YAML for fine-tuning Qwen3-VL-8B on visual inspection data.

model:
  model_name_or_path: Qwen/Qwen3-VL-8B-Instruct
  visual_inputs: true

method:
  stage: sft
  finetuning_type: lora
  lora_rank: 16
  lora_alpha: 32
  lora_dropout: 0.05
  lora_target: q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj

dataset:
  dataset: vision_inspect_defects
  dataset_dir: training/
  template: qwen3_vl
  cutoff_len: 2048
  max_samples: 5000

output:
  output_dir: models/versions/qlora_finetuned
  overwrite_output_dir: true

train:
  per_device_train_batch_size: 1
  gradient_accumulation_steps: 8
  learning_rate: 1.0e-4
  num_train_epochs: 3
  bf16: true

eval:
  val_size: 0.1
  eval_steps: 100""")

    _gen("training/COLLECTING_DATA.md", _GEN, """\
Write a markdown guide for collecting labeled training data for Vision_Inspect fine-tuning.

Sections:
## Overview
Brief description of why fine-tuning helps and what data is needed.

## Step 1 — Enable Frame Saving
How to configure Vision_Inspect to save frames during inspection.

## Step 2 — Collect Raw Frames
How to run inspections and accumulate diverse examples.

## Step 3 — Label with Bounding Boxes
Recommend LabelImg or Roboflow. Explain the labeling format.

## Step 4 — Convert to dataset_template.json Format
Python snippet to convert annotated images to the conversation format.

## Step 5 — Run Fine-Tuning
llamafactory-cli train command pointing at llama_factory_qlora.yaml.

## Step 6 — Register with Ollama and Activate
ollama create command, then POST to /models/rollback to activate.""")

    _gen("README.md", _GEN, """\
Write a complete README.md for Vision_Inspect, a local shop-floor visual process monitoring system.

Structure:
# Vision_Inspect
One paragraph: what it does (local shop-floor visual inspection using VLMs via Ollama),
key principle: "sees everything, touches nothing, reports everything — no automated process control".

## Architecture
ASCII flow diagram:
Camera/Upload → Ingestion → Preprocessing → VLM Inference (Ollama) → Report Generator → outputs/
Tech stack table: FastAPI backend, React + MUI v5 frontend, Ollama (qwen3vl:8b + internvl3:8b), WebSocket streaming.

## Requirements
Python 3.11+, Node.js 18+, Ollama with 8GB+ VRAM recommended.
ollama pull commands for qwen3vl:8b and internvl3:8b.

## Quick Start
Step-by-step: git clone, cd Vision_Inspect, pip install -r requirements.txt,
uvicorn backend.main:app --host 0.0.0.0 --port 8000,
cd frontend && npm install && npm start.

## Configuration Reference
Table: File | Purpose | Key Settings
(4 rows for the 4 config files)

## Input Modes
Table: Mode | YAML value | Description
(4 rows: live camera, manual upload, scheduled capture, manual trigger)

## Inspection Endpoints
Table: Endpoint | Method | Description
POST /upload, POST /inspect, GET /results/{job_id}, POST /report/{job_id},
GET /reports, GET /models/versions, POST /models/rollback, GET /health, WS /ws/stream.

## Proxy Metrics
Brief explanation of each metric: latency, confidence, drift alert, distribution shift.
When alerts trigger. Silent failure detection.

## Model Versioning
How to create versions with POST /models/rollback, list with GET /models/versions,
activate with set_active_version.

## Notifications
How to configure Teams webhook and SMTP email in notification_config.yaml.
Severity thresholds: high triggers Teams, critical triggers email.

## Fine-Tuning
One paragraph pointing to training/COLLECTING_DATA.md for QLoRA fine-tuning workflow.

## Important: Observation Only
Bold section: this system never modifies, interrupts, or sends commands to any monitored process.
All reports are for human review only. No automated decisions are made.""")

    print("\nPhase VI-E complete.")


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE VI-COMMIT  —  Git Commit + Push
# ══════════════════════════════════════════════════════════════════════════════

def phase_vi_commit() -> None:
    import subprocess
    print("\n=== Phase VI-COMMIT: Git Commit + Push ===\n")
    vi = str(_VI_ROOT)

    def run(cmd: list[str]) -> tuple[int, str]:
        r = subprocess.run(cmd, cwd=vi, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        return r.returncode, out

    # Verify key files
    required = [
        ".gitignore", "requirements.txt", "README.md",
        "backend/__init__.py", "backend/main.py", "backend/vlm_router.py",
        "configs/vlm_config.yaml", "configs/input_config.yaml",
        "frontend/package.json", "frontend/src/App.tsx",
        "training/llama_factory_qlora.yaml",
    ]
    missing = [f for f in required if not (_VI_ROOT / f).exists()]
    if missing:
        print(f"  ! Missing files: {missing}")
        print("  Aborting commit — run missing phases first.")
        return

    code, out = run(["git", "status", "--short"])
    print(f"  Status:\n{out}\n")

    code, out = run(["git", "add", "."])
    print(f"  Stage: {out or 'OK'}")

    msg = "Initial commit: Vision_Inspect visual process monitoring system"
    code, out = run(["git", "commit", "-m", msg])
    print(f"  Commit: {out}")
    if code != 0:
        print("  Commit failed — check git output above.")
        return

    code, out = run(["git", "push", "origin", "main"])
    print(f"  Push: {out}")
    if code == 0:
        # get commit hash
        _, h = run(["git", "rev-parse", "--short", "HEAD"])
        print(f"\n  Pushed commit {h} to AddisonTech/Vision_Inspect.git")
    else:
        print("  Push failed — check remote/auth.")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

PHASES = {
    "vi_a":      phase_vi_a,
    "vi_b":      phase_vi_b,
    "vi_c":      phase_vi_c,
    "vi_d":      phase_vi_d,
    "vi_e":      phase_vi_e,
    "vi_commit": phase_vi_commit,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Vision_Inspect files via Ollama.")
    parser.add_argument("--phase", default="vi_a",
                        choices=list(PHASES.keys()) + ["all"])
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Vision_Inspect Direct Build — {args.phase.upper()}")
    print(f"  Target: {_VI_ROOT}")
    print(f"{'='*60}")

    if args.phase == "all":
        for phase in ["vi_a", "vi_b", "vi_c", "vi_d", "vi_e", "vi_commit"]:
            PHASES[phase]()
    else:
        PHASES[args.phase]()


if __name__ == "__main__":
    main()
