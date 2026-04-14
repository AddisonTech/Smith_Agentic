"""
run_vision_inspect.py — Vision_Inspect build runner.

Uses the Smith_Agentic expanded agent team to build Vision_Inspect.
All output files are written to ../Vision_Inspect/ via VisionInspectWriteTool.

Key design decisions:
  - Builder receives ONLY VI tools — cannot accidentally write to wrong location.
  - Uses qwen2.5-coder:14b for builder (best instruction-following for code gen).
  - Tight 4-task pipeline per phase: plan -> build -> critique -> revise.
  - Full 10-agent pipeline for QA/Security/Deploy on backend phases.

Usage:
    python run_vision_inspect.py --phase vi_a   # configs + infrastructure
    python run_vision_inspect.py --phase vi_b   # backend core + pipeline
    python run_vision_inspect.py --phase vi_c   # backend utilities
    python run_vision_inspect.py --phase vi_d   # frontend
    python run_vision_inspect.py --phase vi_e   # training + README
    python run_vision_inspect.py --phase vi_commit  # git commit + push
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from crewai import Crew, LLM, Process, Task

from config.loader import load_config
from agents.orchestrator        import create_orchestrator
from agents.builder             import create_builder
from agents.critic              import create_critic
from agents.qa_agent            import create_qa_agent
from agents.security_agent      import create_security_agent
from agents.deploy_agent        import create_deploy_agent

from tools.file_tools          import FileReadTool, FileListTool, FileWriteTool
from tools.search_tool         import WebSearchTool
from tools.web_fetch_tool      import WebFetchTool
from tools.code_executor       import CodeExecutorTool
from tools.vision_inspect_tool import (
    VisionInspectWriteTool,
    VisionInspectReadTool,
    VisionInspectListTool,
)
from tools.git_tool    import GitStatusTool, GitStageTool, GitCommitTool, GitPushTool
from memory.memory_store import create_memory_tools

_VI_ROOT     = _HERE.parent / "Vision_Inspect"
_VI_ROOT_STR = str(_VI_ROOT)

# Safe placeholder — no curly braces, no format() conflicts.
_R = _VI_ROOT_STR


# ══════════════════════════════════════════════════════════════════════════════
#  PHASE SPECS
# ══════════════════════════════════════════════════════════════════════════════

PHASE_VI_A = f"""
PHASE VI-A: Vision_Inspect — Config Files and Repo Infrastructure

Vision_Inspect root: {_R}

You are writing infrastructure and configuration files for Vision_Inspect,
a local shop-floor visual inspection system. It never modifies monitored
processes — it only observes and reports.

Use ONLY "Write Vision_Inspect File" for ALL file writes.
Paths are relative to Vision_Inspect root (e.g. "configs/input_config.yaml").
After writing each file, verify it with "Read Vision_Inspect File".

FILES TO CREATE:

1. .gitignore
   Standard Python + Node gitignore. Include: __pycache__/, *.pyc, .env,
   .venv, venv/, node_modules/, build/, dist/, .next/, *.log, *.tmp,
   .DS_Store, Thumbs.db, models/versions/*.onnx, models/versions/*.gguf,
   outputs/inspection_reports/*.md, outputs/inspection_reports/*.png

2. requirements.txt
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
   scipy>=1.13.0

3. configs/input_config.yaml
   YAML config controlling all 4 input modes. Include all fields:
   input.mode (default: live_camera),
   input.manual_upload (enabled, accepted_formats, max_file_size_mb),
   input.live_camera (enabled, device_index, stream_url, capture_width,
     capture_height, fps, buffer_frames),
   input.scheduled_capture (enabled, interval_seconds, duration_seconds),
   input.manual_trigger (enabled, endpoint: /inspect)

4. configs/vlm_config.yaml
   YAML config for VLM routing. Include:
   ollama.base_url: http://localhost:11434
   ollama.timeout_seconds: 120
   ollama.max_retries: 3
   primary_model (name: qwen3vl:8b, quant: Q5_K_M, context_length: 8192,
     temperature: 0.1, use_cases list)
   fallback_model (name: internvl3:8b, quant: Q5_K_M, temperature: 0.05,
     use_cases: [nameplate_ocr, serial_number_extraction, label_reading, high_resolution_text])
   routing.ocr_task_types: [nameplate_ocr, serial_number_extraction, label_reading]
   routing.retry_below_confidence: 0.65
   Comments documenting quant recommendations: Q5_K_M recommended, Q4_K_M
   acceptable, Q8_0 near-lossless, IQ3_M CPU fallback.

5. configs/inspection_config.yaml
   YAML config for field-adjustable inspection parameters. Include:
   preprocessing (brightness_target: 128, brightness_tolerance: 30,
     contrast_min: 0.4, resize_max_dimension: 1024, normalize: true)
   defect_detection (sensitivity: 0.72, min_defect_area_px: 25, ignore_regions: [])
   surface_anomaly (sensitivity: 0.68, classes_to_ignore: [])
   ocr (min_confidence: 0.80, expected_formats with serial_number regex and
     nameplate_fields list)
   process_deviation (sensitivity: 0.60, reference_image_path: "",
     max_deviation_percent: 15)
   video (frame_sample_interval: 5, drift_window_frames: 30,
     anomaly_trend_threshold: 3)

6. configs/notification_config.yaml
   YAML config for notifications. Include:
   notifications.enabled: true
   notifications.severity_thresholds (teams: high, email: critical)
   notifications.teams (enabled: false, webhook_url: "", mention_channel: false)
   notifications.email (enabled: false, smtp_host, smtp_port: 587,
     smtp_use_tls: true, smtp_username: "", smtp_password: "",
     from_address: "", recipients: [""])
   notifications.message_template (subject, body_prefix)

7. models/versions/.gitkeep  (empty file)
8. outputs/inspection_reports/.gitkeep  (empty file)
9. training/.gitkeep  (empty file)

After writing all files, use "List Vision_Inspect Directory" to confirm they exist.
"""

PHASE_VI_B = f"""
PHASE VI-B: Vision_Inspect — Backend Core Python Files

Vision_Inspect root: {_R}

Use ONLY "Write Vision_Inspect File" for ALL file writes.
Read existing configs first with "Read Vision_Inspect File".
Use Web Search / Fetch Web Page if you need to look up FastAPI or Ollama API details.

Read these first:
  configs/vlm_config.yaml
  configs/inspection_config.yaml
  configs/input_config.yaml

FILES TO CREATE (write each one completely — no TODOs, no stubs):

1. backend/__init__.py
   Content: just a module docstring: "Vision_Inspect backend package."

2. backend/pipeline/__init__.py
   Content: just a module docstring: "Vision_Inspect modular inspection pipeline."

3. backend/config_loader.py
   Load all 4 YAML config files. The configs/ directory is at:
     Path(__file__).resolve().parent.parent / "configs"
   Functions:
     load_input_config() -> dict
     load_vlm_config() -> dict
     load_inspection_config() -> dict
     load_notification_config() -> dict
   Each opens the appropriate .yaml file and returns yaml.safe_load result.

4. backend/hardware_abstraction.py
   Hardware abstraction layer for ONNX runtime provider selection.
   Functions:
     get_onnx_providers() -> list[str]:
       Try in order: CUDAExecutionProvider (check ort_gpu import),
       OpenVINOExecutionProvider, CPUExecutionProvider.
       Return list of available providers. Always includes CPU.
     get_device_info() -> dict:
       Return dict: provider (first available), cuda_available (bool),
       cpu_count (os.cpu_count()).

5. backend/pipeline/ingestion.py
   Handles all 4 input modes using OpenCV and Pillow.
   Import: cv2, numpy, PIL.Image, io, base64, datetime, dataclasses, pathlib
   @dataclass class IngestResult:
     frames: list          # list of numpy arrays
     source_type: str      # manual_upload|live_camera|scheduled|manual_trigger
     source_path: str
     timestamp: str        # ISO 8601
     frame_count: int
     width: int
     height: int
   class Ingester:
     def __init__(self, config: dict): store config, set device_index and stream_url
     def ingest_upload(self, file_bytes: bytes, filename: str) -> IngestResult:
       Detect video vs image from extension. For images: use PIL then convert to cv2.
       For video: use cv2.VideoCapture on a temp file, read all frames.
       Return IngestResult.
     def ingest_camera_frame(self) -> IngestResult:
       cv2.VideoCapture(device_index or stream_url). Read buffer_frames frames.
       Release after. Return IngestResult with source_type="live_camera".
     def ingest_scheduled(self) -> IngestResult:
       Same as camera but read for duration_seconds. source_type="scheduled".
     def ingest_manual_trigger(self) -> IngestResult:
       Same as camera but source_type="manual_trigger".

6. backend/pipeline/preprocessing.py
   Image preprocessing before inference.
   Import: cv2, numpy, base64
   def preprocess_frame(frame: "np.ndarray", config: dict) -> "np.ndarray":
     1. Brightness: compute mean. If deviation from brightness_target >
        brightness_tolerance: scale frame * (brightness_target / mean).
        Clip to [0, 255].
     2. Resize: if max(h,w) > resize_max_dimension, scale proportionally.
     3. Normalize: if config normalize True, scale to float32 / 255.0.
     Return processed frame.
   def frame_to_base64(frame: "np.ndarray") -> str:
     Encode as JPEG with cv2.imencode. Return base64.b64encode string.
   def preprocess_batch(frames: list, config: dict) -> list:
     Return [preprocess_frame(f, config) for f in frames]

7. backend/pipeline/inference.py
   VLM inference via Ollama REST API.
   Import: requests, json, time, datetime, dataclasses, numpy
   from backend.config_loader import load_vlm_config
   from backend.pipeline.preprocessing import frame_to_base64

   TASK_PROMPTS = dict with keys:
     defect_detection, surface_anomaly_classification, nameplate_ocr,
     serial_number_extraction, engineering_drawing_interpretation,
     process_deviation_flagging.
   Each value is a prompt string instructing the model to return JSON with
   a findings list, pass_fail field, and confidence float.

   @dataclass class InferenceResult:
     task_type: str
     model_used: str
     raw_response: str
     findings: list
     confidence_scores: list
     latency_ms: float
     timestamp: str

   class VLMInferenceEngine:
     def __init__(self, vlm_config: dict): store config
     def _get_model_for_task(self, task_type: str) -> str:
       Return fallback model name for OCR tasks, primary for others.
     def _call_ollama(self, model: str, prompt: str, image_b64: str) -> dict:
       POST to base_url + /api/generate with json:
         model=model, prompt=prompt, images=[image_b64], stream=False
       Handle requests.exceptions.RequestException gracefully.
       Return response.json().
     def run_inspection(self, frames: list, task_type: str,
                        inspection_config: dict) -> InferenceResult:
       Get model and prompt. For first frame: preprocess and get base64.
       Record start time. Call _call_ollama. Compute latency_ms.
       Parse JSON from response["response"]. Extract findings list.
       If confidence below retry threshold: retry with fallback model.
       Return InferenceResult.

8. backend/pipeline/monitoring.py
   Frame sequence monitoring for drift and anomaly trends.
   Import: collections, dataclasses
   class FrameMonitor:
     def __init__(self, config: dict):
       self._config = config
       self._history = collections.deque(
         maxlen=config.get("video", {{}}).get("drift_window_frames", 30))
     def update(self, result) -> dict:
       Append result to history. Compute:
         anomaly_trend = sum(1 for r in self._history if
           getattr(r, "pass_fail", r.get("pass_fail", "PASS") if isinstance(r, dict) else "PASS") == "FAIL")
         mean_confidence = mean of all confidence_scores across history
         drift_detected = anomaly_trend >= config video.anomaly_trend_threshold
       Return dict: anomaly_trend, mean_confidence, drift_detected.
     def get_trend_summary(self) -> dict:
       Return: frame_count_analyzed (len history), anomaly_rate, mean_confidence,
               drift_detected, consecutive_anomaly_windows (anomaly_trend).

After writing all 8 files, use "List Vision_Inspect Directory" with dirpath="backend"
and dirpath="backend/pipeline" to verify all files exist.
"""

PHASE_VI_C = f"""
PHASE VI-C: Vision_Inspect — Backend Utilities

Vision_Inspect root: {_R}

Use ONLY "Write Vision_Inspect File" for ALL file writes.
Read existing files first with "Read Vision_Inspect File" as needed.

Read these first:
  configs/vlm_config.yaml
  configs/notification_config.yaml
  backend/pipeline/inference.py

FILES TO CREATE:

1. backend/vlm_router.py
   Routes inspection tasks to the correct Ollama model.
   Import: requests, json, time, logging
   from backend.config_loader import load_vlm_config

   class VLMRouter:
     def __init__(self, config: dict = None):
       self._cfg = config or load_vlm_config()
     def get_model(self, task_type: str) -> str:
       ocr_types = self._cfg["routing"]["ocr_task_types"]
       if task_type in ocr_types:
         return self._cfg["fallback_model"]["name"]
       return self._cfg["primary_model"]["name"]
     def build_prompt(self, task_type: str) -> str:
       Return a clear inspection prompt for each task_type. Each prompt
       instructs the model to return structured JSON with: findings list,
       confidence float, pass_fail ("PASS" or "FAIL"), and notes.
       Handle: defect_detection, surface_anomaly_classification, nameplate_ocr,
       serial_number_extraction, engineering_drawing_interpretation,
       process_deviation_flagging.
     def call(self, task_type: str, image_b64: str, timeout: int = 120) -> dict:
       base_url = self._cfg["ollama"]["base_url"]
       model = self.get_model(task_type)
       prompt = self.build_prompt(task_type)
       start = time.time()
       resp = requests.post(base_url + "/api/generate",
         json=dict(model=model, prompt=prompt,
                   images=[image_b64], stream=False),
         timeout=timeout)
       latency_ms = (time.time() - start) * 1000
       raw = resp.json().get("response", "")
       try:
         data = json.loads(raw)
       except json.JSONDecodeError:
         data = dict(findings=[], confidence=0.0, pass_fail="UNKNOWN", raw=raw)
       data["model"] = model
       data["task_type"] = task_type
       data["latency_ms"] = round(latency_ms, 2)
       return data

2. backend/proxy_metrics.py
   Tracks inference health metrics without labels.
   Import: collections, math, statistics, time, logging

   class ProxyMetricsCollector:
     def __init__(self, window_size: int = 50):
       self._latency: collections.deque = collections.deque(maxlen=window_size)
       self._confidence: collections.deque = collections.deque(maxlen=window_size)
     def record(self, latency_ms: float, confidence: float) -> None:
       self._latency.append(latency_ms)
       self._confidence.append(confidence)
     def get_metrics(self) -> dict:
       if not self._latency:
         return dict(mean_latency_ms=0, p95_latency_ms=0, mean_confidence=0,
                     confidence_std=0, confidence_drift_alert=False,
                     distribution_shift_score=0.0,
                     distribution_shift_alert=False, sample_count=0)
       lats = sorted(self._latency)
       confs = list(self._confidence)
       mean_lat = statistics.mean(lats)
       p95_lat = lats[int(len(lats) * 0.95)] if len(lats) > 1 else lats[0]
       mean_conf = statistics.mean(confs)
       std_conf = statistics.stdev(confs) if len(confs) > 1 else 0.0
       shift = abs(mean_conf - 0.5) * std_conf  # simple drift score
       return dict(
         mean_latency_ms=round(mean_lat, 2),
         p95_latency_ms=round(p95_lat, 2),
         mean_confidence=round(mean_conf, 4),
         confidence_std=round(std_conf, 4),
         confidence_drift_alert=std_conf > 0.15,
         distribution_shift_score=round(shift, 4),
         distribution_shift_alert=shift > 0.3,
         sample_count=len(lats),
       )
     def detect_silent_failures(self) -> list:
       warnings = []
       m = self.get_metrics()
       if m["sample_count"] > 5:
         if self._latency and list(self._latency)[-1] > m["mean_latency_ms"] * 3:
           warnings.append("latency spike — possible hardware issue or dirty lens")
         if m["mean_confidence"] < 0.4:
           warnings.append("confidence collapse — check lens, lighting, or material")
         if m["distribution_shift_alert"]:
           warnings.append("distribution shift — possible process or material change")
       return warnings
     def to_report_section(self) -> str:
       m = self.get_metrics()
       rows = [
         f"| Mean Latency | {{m['mean_latency_ms']}} ms |",
         f"| P95 Latency | {{m['p95_latency_ms']}} ms |",
         f"| Mean Confidence | {{m['mean_confidence']}} |",
         f"| Confidence Std | {{m['confidence_std']}} |",
         f"| Drift Alert | {{'YES' if m['confidence_drift_alert'] else 'no'}} |",
         f"| Shift Score | {{m['distribution_shift_score']}} |",
       ]
       warnings = self.detect_silent_failures()
       warn_str = "\n".join(f"- {{w}}" for w in warnings) if warnings else "None"
       return ("## Proxy Metric Readings\n| Metric | Value |\n|--------|-------|\n"
               + "\n".join(rows) + f"\n\n**Active Warnings:** {{warn_str}}\n")

   _collector = ProxyMetricsCollector()
   def get_metrics_collector() -> ProxyMetricsCollector: return _collector
   def record_inference(latency_ms: float, confidence: float) -> None:
     _collector.record(latency_ms, confidence)

3. backend/notifier.py
   Sends notifications for findings above severity thresholds.
   Import: smtplib, json, logging, requests
   from email.mime.text import MIMEText
   from email.mime.multipart import MIMEMultipart
   from backend.config_loader import load_notification_config

   SEVERITY_LEVELS = dict(critical=4, high=3, medium=2, low=1, none=0)
   TEAMS_COLORS = dict(critical="FF0000", high="FF6600", medium="FFCC00", low="00CC00")

   class Notifier:
     def __init__(self, config: dict = None):
       self._cfg = config or load_notification_config()
     def should_notify(self, severity: str, channel: str) -> bool:
       thresh = self._cfg["notifications"]["severity_thresholds"][channel]
       return SEVERITY_LEVELS.get(severity,0) >= SEVERITY_LEVELS.get(thresh,99)
     def send_teams(self, subject: str, body: str, severity: str) -> bool:
       tcfg = self._cfg["notifications"]["teams"]
       if not tcfg["enabled"]: return False
       payload = dict(**{{"@type":"MessageCard","@context":"https://schema.org/extensions"}},
                      summary=subject,
                      themeColor=TEAMS_COLORS.get(severity,"0000FF"),
                      title=subject, text=body)
       try:
         r = requests.post(tcfg["webhook_url"], json=payload, timeout=10)
         return r.status_code == 200
       except Exception as e:
         logging.error("Teams notify failed: %s", e)
         return False
     def send_email(self, subject: str, body: str, recipients: list) -> bool:
       ecfg = self._cfg["notifications"]["email"]
       if not ecfg["enabled"]: return False
       msg = MIMEMultipart()
       msg["From"] = ecfg["from_address"]
       msg["To"] = ", ".join(recipients)
       msg["Subject"] = subject
       msg.attach(MIMEText(body, "plain"))
       try:
         with smtplib.SMTP(ecfg["smtp_host"], ecfg["smtp_port"]) as s:
           if ecfg["smtp_use_tls"]: s.starttls()
           s.login(ecfg["smtp_username"], ecfg["smtp_password"])
           s.sendmail(ecfg["from_address"], recipients, msg.as_string())
         return True
       except Exception as e:
         logging.error("Email notify failed: %s", e)
         return False
     def notify(self, finding: dict, report_path: str) -> None:
       severity = finding.get("severity","low")
       tmpl = self._cfg["notifications"]["message_template"]
       subject = tmpl["subject"].format(
         severity=severity, input_source=finding.get("source","camera"))
       body = tmpl["body_prefix"] + "\\n\\n" + str(finding) + "\\nReport: " + report_path
       if self.should_notify(severity,"teams"): self.send_teams(subject,body,severity)
       if self.should_notify(severity,"email"):
         self.send_email(subject,body,self._cfg["notifications"]["email"]["recipients"])

4. backend/model_versioning.py
   Manages model versions in models/versions/.
   Import: json, pathlib, datetime, logging
   from pathlib import Path

   class ModelVersionManager:
     def __init__(self, versions_dir: Path):
       self.versions_dir = versions_dir
       versions_dir.mkdir(parents=True, exist_ok=True)
     def list_versions(self) -> list:
       result = []
       for d in sorted(self.versions_dir.iterdir()):
         if d.is_dir():
           info_file = d / "model_info.json"
           if info_file.exists():
             data = json.loads(info_file.read_text())
             data["active"] = (d / ".active").exists()
             result.append(data)
       return result
     def get_active_version(self):
       for v in self.list_versions():
         if v.get("active"): return v
       return None
     def set_active_version(self, version: str) -> bool:
       for d in self.versions_dir.iterdir():
         marker = d / ".active"
         if marker.exists(): marker.unlink()
       target = self.versions_dir / version
       if not target.exists(): return False
       (target / ".active").touch()
       return True
     def create_version(self, model_name: str, notes: str = "") -> dict:
       tag = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
       vdir = self.versions_dir / tag
       vdir.mkdir(parents=True, exist_ok=True)
       info = dict(version=tag, model_name=model_name,
                   created_at=datetime.datetime.now().isoformat(), notes=notes)
       (vdir / "model_info.json").write_text(json.dumps(info, indent=2))
       return info
     def rollback(self, version: str) -> bool:
       ok = self.set_active_version(version)
       if ok: logging.info("Rolled back to model version %s", version)
       return ok

   def get_version_manager() -> ModelVersionManager:
     vi_root = Path(__file__).resolve().parent.parent
     return ModelVersionManager(vi_root / "models" / "versions")

5. backend/report_generator.py
   Generates structured markdown inspection reports.
   Import: pathlib, datetime, logging

   def get_reports_dir() -> "Path":
     from pathlib import Path
     return Path(__file__).resolve().parent.parent / "outputs" / "inspection_reports"

   def generate_report(job_id: str, input_source: str, inference_result: dict,
                       proxy_metrics: dict, model_version: str,
                       annotated_image_path: str = None) -> str:
     timestamp = datetime.datetime.now().isoformat()
     findings = inference_result.get("findings", [])
     pass_fail = inference_result.get("pass_fail", "UNKNOWN")
     model_used = inference_result.get("model", "unknown")
     # Build findings table
     if findings:
       table_rows = "\\n".join(
         f"| {{f.get('label','?')}} | {{f.get('confidence','?')}} | "
         f"{{f.get('severity','?')}} | {{f.get('description','')}} |"
         for f in findings)
       table = ("| Label | Confidence | Severity | Description |\\n"
                "|-------|-----------|----------|-------------|\\n" + table_rows)
     else:
       table = "*No findings.*"
     # Proxy metrics section
     proxy_section = proxy_metrics.get("_formatted","")
     if not proxy_section:
       proxy_section = str(proxy_metrics)
     # Annotated frame
     frame_section = (f"![]({{annotated_image_path}})" if annotated_image_path
                      else "*No annotated frame available.*")
     # Recommended actions
     if pass_fail == "PASS":
       actions = "- No action required — continue monitoring."
     else:
       actions = "\\n".join(
         f"- Review {{f.get('label','finding')}} at confidence "
         f"{{f.get('confidence','?')}}: {{f.get('description','')}}"
         for f in findings) or "- Inspect flagged area manually."
     report = (
       f"# Vision_Inspect Report — {{timestamp}}\\n\\n"
       f"**Job ID**: {{job_id}}\\n"
       f"**Input Source**: {{input_source}}\\n"
       f"**Model Version**: {{model_version}}\\n"
       f"**Model Used**: {{model_used}}\\n\\n"
       f"## Findings\\n{{table}}\\n\\n"
       f"## Pass/Fail Verdict\\n{{pass_fail}}\\n\\n"
       f"{{proxy_section}}\\n\\n"
       f"## Annotated Frame\\n{{frame_section}}\\n\\n"
       f"## Recommended Human Actions\\n{{actions}}\\n\\n"
       f"---\\n*This report is for human review only. "
       f"Vision_Inspect makes no automated decisions.*\\n"
     ).format(timestamp=timestamp, job_id=job_id, input_source=input_source,
              model_version=model_version, model_used=model_used,
              table=table, pass_fail=pass_fail,
              proxy_section=proxy_section, frame_section=frame_section,
              actions=actions)
     reports_dir = get_reports_dir()
     reports_dir.mkdir(parents=True, exist_ok=True)
     (reports_dir / f"{{job_id}}.md").write_text(report, encoding="utf-8")
     return report

6. backend/main.py
   FastAPI application — complete async implementation.
   Import: fastapi, uvicorn, uuid, json, asyncio, pathlib, logging
   from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
   from fastapi.middleware.cors import CORSMiddleware
   from fastapi.responses import JSONResponse
   from backend.config_loader import load_vlm_config, load_input_config
   from backend.vlm_router import VLMRouter
   from backend.pipeline.ingestion import Ingester
   from backend.pipeline.preprocessing import preprocess_frame, frame_to_base64
   from backend.proxy_metrics import record_inference, get_metrics_collector
   from backend.report_generator import generate_report, get_reports_dir
   from backend.model_versioning import get_version_manager
   from backend.notifier import Notifier

   app = FastAPI(title="Vision_Inspect", version="1.0.0")
   app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                      allow_headers=["*"])

   class ConnectionManager:
     def __init__(self): self.active: list = []
     async def connect(self, ws: WebSocket):
       await ws.accept(); self.active.append(ws)
     def disconnect(self, ws: WebSocket):
       if ws in self.active: self.active.remove(ws)
     async def broadcast(self, msg: dict):
       text = json.dumps(msg)
       dead = []
       for ws in self.active:
         try: await ws.send_text(text)
         except Exception: dead.append(ws)
       for ws in dead: self.disconnect(ws)

   manager = ConnectionManager()
   _job_store: dict = {{}}
   _vlm = None
   _ingester = None

   def _get_vlm() -> VLMRouter:
     global _vlm
     if _vlm is None: _vlm = VLMRouter()
     return _vlm

   def _get_ingester() -> Ingester:
     global _ingester
     if _ingester is None: _ingester = Ingester(load_input_config())
     return _ingester

   @app.post("/upload")
   async def upload_image(file: UploadFile = File(...), task_type: str = "defect_detection"):
     job_id = str(uuid.uuid4())[:8]
     data = await file.read()
     ingester = _get_ingester()
     ingest = ingester.ingest_upload(data, file.filename)
     vlm = _get_vlm()
     cfg = load_vlm_config()
     frame_b64 = frame_to_base64(ingest.frames[0]) if ingest.frames else ""
     result = vlm.call(task_type, frame_b64)
     conf = result.get("confidence", 0.0)
     record_inference(result.get("latency_ms", 0), conf if isinstance(conf, float) else 0.5)
     metrics = get_metrics_collector().get_metrics()
     version = get_version_manager().get_active_version()
     ver_str = version["version"] if version else "unversioned"
     report = generate_report(job_id, file.filename, result, metrics, ver_str)
     _job_store[job_id] = dict(result=result, metrics=metrics, report=report)
     await manager.broadcast(dict(type="result", job_id=job_id, data=result))
     return dict(job_id=job_id, status="complete",
                 task_type=task_type, finding_count=len(result.get("findings",[])))

   @app.post("/inspect")
   async def trigger_inspection(body: dict):
     job_id = str(uuid.uuid4())[:8]
     task_type = body.get("task_type","defect_detection")
     source = body.get("source","camera")
     ingester = _get_ingester()
     ingest = (ingester.ingest_manual_trigger() if source == "manual"
               else ingester.ingest_camera_frame())
     vlm = _get_vlm()
     frame_b64 = frame_to_base64(ingest.frames[0]) if ingest.frames else ""
     result = vlm.call(task_type, frame_b64)
     conf = result.get("confidence", 0.0)
     record_inference(result.get("latency_ms",0), conf if isinstance(conf,float) else 0.5)
     metrics = get_metrics_collector().get_metrics()
     version = get_version_manager().get_active_version()
     ver_str = version["version"] if version else "unversioned"
     generate_report(job_id, source, result, metrics, ver_str)
     _job_store[job_id] = dict(result=result, metrics=metrics)
     await manager.broadcast(dict(type="result", job_id=job_id, data=result))
     return dict(job_id=job_id, status="complete")

   @app.get("/results/{{job_id}}")
   async def get_results(job_id: str):
     if job_id not in _job_store:
       raise HTTPException(status_code=404, detail="Job not found")
     return _job_store[job_id]

   @app.post("/report/{{job_id}}")
   async def get_report(job_id: str):
     if job_id not in _job_store:
       raise HTTPException(status_code=404, detail="Job not found")
     job = _job_store[job_id]
     version = get_version_manager().get_active_version()
     ver_str = version["version"] if version else "unversioned"
     report = generate_report(job_id, "api_request", job.get("result",{{}}),
                               job.get("metrics",{{}}), ver_str)
     report_path = str(get_reports_dir() / f"{{job_id}}.md")
     return dict(report_path=report_path, report_content=report)

   @app.get("/reports")
   async def list_reports():
     d = get_reports_dir()
     if not d.exists(): return []
     return [dict(filename=f.name, size_bytes=f.stat().st_size)
             for f in sorted(d.glob("*.md"))]

   @app.get("/models/versions")
   async def list_model_versions():
     return get_version_manager().list_versions()

   @app.post("/models/rollback")
   async def rollback_model(body: dict):
     version = body.get("version","")
     ok = get_version_manager().rollback(version)
     if not ok: raise HTTPException(status_code=404, detail="Version not found")
     return dict(status="ok", version=version)

   @app.get("/health")
   async def health():
     import requests as req
     try:
       cfg = load_vlm_config()
       req.get(cfg["ollama"]["base_url"] + "/api/tags", timeout=3)
       ollama_ok = True
     except Exception: ollama_ok = False
     return dict(status="ok", ollama_reachable=ollama_ok)

   @app.websocket("/ws/stream")
   async def ws_stream(websocket: WebSocket):
     await manager.connect(websocket)
     try:
       while True:
         data = await websocket.receive_text()
         try:
           msg = json.loads(data)
           task_type = msg.get("task_type","defect_detection")
           ingester = _get_ingester()
           ingest = ingester.ingest_camera_frame()
           vlm = _get_vlm()
           frame_b64 = frame_to_base64(ingest.frames[0]) if ingest.frames else ""
           result = vlm.call(task_type, frame_b64)
           await manager.broadcast(dict(type="result", data=result))
         except Exception as e:
           await websocket.send_text(json.dumps(dict(type="error", message=str(e))))
     except WebSocketDisconnect:
       manager.disconnect(websocket)

   if __name__ == "__main__":
     uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)

After writing all files, use "List Vision_Inspect Directory" with dirpath="backend"
to verify all files exist.
"""

PHASE_VI_D = f"""
PHASE VI-D: Vision_Inspect — React Frontend (Dark Industrial MUI v5)

Vision_Inspect root: {_R}

Use ONLY "Write Vision_Inspect File" for ALL file writes.
Use Web Search / Fetch Web Page if you need MUI v5 or Recharts API details.

FILES TO CREATE:

1. frontend/package.json
   Write this JSON exactly:
   {{
     "name": "vision-inspect-ui",
     "version": "1.0.0",
     "private": true,
     "dependencies": {{
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
     }},
     "scripts": {{
       "start": "react-scripts start",
       "build": "react-scripts build"
     }},
     "browserslist": {{
       "production": [">0.2%", "not dead"],
       "development": ["last 1 chrome version"]
     }},
     "proxy": "http://localhost:8000"
   }}

2. frontend/tsconfig.json
   Standard CRA TypeScript config. compilerOptions: target ES6, lib [dom,dom.iterable,esnext],
   allowJs true, skipLibCheck true, esModuleInterop true, allowSyntheticDefaultImports true,
   strict false, jsx react-jsx, moduleResolution node,
   baseUrl src. Include [src].

3. frontend/src/theme/theme.ts
   import {{ createTheme }} from "@mui/material/styles";
   const theme = createTheme({{
     palette: {{
       mode: "dark",
       background: {{ default: "#0d0d0d", paper: "#1a1a1a" }},
       primary: {{ main: "#f59e0b" }},
       secondary: {{ main: "#22d3ee" }},
       error: {{ main: "#ef4444" }},
       success: {{ main: "#22c55e" }},
       text: {{ primary: "#e5e7eb", secondary: "#9ca3af" }},
     }},
     typography: {{ fontFamily: "JetBrains Mono, Consolas, monospace" }},
   }});
   export default theme;

4. frontend/src/types.ts
   export interface InspectionFinding {{
     label: string; confidence: number; severity: string;
     bbox?: number[]; description: string;
   }}
   export interface InspectionResult {{
     job_id: string; timestamp: string; model_used: string;
     pass_fail: string; findings: InspectionFinding[]; notes: string;
   }}
   export interface ProxyMetrics {{
     mean_latency_ms: number; mean_confidence: number;
     confidence_drift_alert: boolean; distribution_shift_alert: boolean;
     sample_count: number;
   }}
   export interface Report {{ filename: string; size_bytes: number; }}

5. frontend/src/api.ts
   import axios from "axios";
   import {{ InspectionResult, Report }} from "./types";
   const api = axios.create({{ baseURL: "/api" }});
   export const uploadImage = (file: File, taskType: string): Promise<InspectionResult> => {{
     const fd = new FormData(); fd.append("file", file);
     return api.post(`/upload?task_type=${{taskType}}`, fd).then(r => r.data);
   }};
   export const triggerInspection = (taskType: string, source: string) =>
     api.post("/inspect", {{ task_type: taskType, source }}).then(r => r.data);
   export const getResults = (jobId: string) =>
     api.get(`/results/${{jobId}}`).then(r => r.data);
   export const generateReport = (jobId: string) =>
     api.post(`/report/${{jobId}}`).then(r => r.data);
   export const listReports = (): Promise<Report[]> =>
     api.get("/reports").then(r => r.data);
   export const getHealth = () =>
     api.get("/health").then(r => r.data);

6. frontend/src/hooks/useWebSocket.ts
   import {{ useEffect, useRef, useState }} from "react";
   export function useWebSocket(url: string) {{
     const [connected, setConnected] = useState(false);
     const [lastMessage, setLastMessage] = useState<any>(null);
     const [error, setError] = useState<string | null>(null);
     const wsRef = useRef<WebSocket | null>(null);
     useEffect(() => {{
       const connect = () => {{
         const ws = new WebSocket(url);
         wsRef.current = ws;
         ws.onopen = () => setConnected(true);
         ws.onmessage = (e) => {{
           try {{ setLastMessage(JSON.parse(e.data)); }}
           catch {{ setLastMessage(e.data); }}
         }};
         ws.onerror = () => setError("WebSocket error");
         ws.onclose = () => {{
           setConnected(false);
           setTimeout(connect, 3000);
         }};
       }};
       connect();
       return () => wsRef.current?.close();
     }}, [url]);
     return {{ connected, lastMessage, error }};
   }}

7. frontend/src/components/CameraFeed.tsx
   import React from "react";
   import {{ Card, CardContent, Typography, Button, Box, CircularProgress }} from "@mui/material";
   import VideocamIcon from "@mui/icons-material/Videocam";
   interface Props {{ imageUrl?: string; streaming: boolean; onTrigger: () => void; }}
   export default function CameraFeed({{ imageUrl, streaming, onTrigger }}: Props) {{
     return (
       <Card sx={{{{ bgcolor: "background.paper", mb: 2 }}}}>
         <CardContent>
           <Typography variant="h6" sx={{{{ color: "primary.main", mb: 1 }}}}>
             <VideocamIcon sx={{{{ mr: 1, verticalAlign: "middle" }}}} />Live Feed
           </Typography>
           <Box sx={{{{ position: "relative", minHeight: 200, bgcolor: "#000",
                      display: "flex", alignItems: "center", justifyContent: "center" }}}}>
             {{imageUrl
               ? <img src={{imageUrl}} alt="feed" style={{{{ width: "100%", maxHeight: 300, objectFit: "contain" }}}} />
               : <Typography color="text.secondary">No feed available</Typography>}}
             {{streaming && <CircularProgress sx={{{{ position: "absolute" }}}} size={{24}} />}}
           </Box>
           <Button variant="contained" color="primary" fullWidth
             sx={{{{ mt: 1 }}}} onClick={{onTrigger}} disabled={{streaming}}>
             {{streaming ? "Inspecting..." : "Trigger Inspection"}}
           </Button>
         </CardContent>
       </Card>
     );
   }}

8. frontend/src/components/DefectOverlay.tsx
   import React from "react";
   import {{ Box, Typography }} from "@mui/material";
   import {{ InspectionFinding }} from "../types";
   const SEV_COLORS: Record<string, string> = {{
     critical: "#ef4444", high: "#f97316", medium: "#eab308", low: "#22d3ee"
   }};
   interface Props {{ imageUrl: string; findings: InspectionFinding[]; }}
   export default function DefectOverlay({{ imageUrl, findings }}: Props) {{
     return (
       <Box sx={{{{ position: "relative", display: "inline-block", width: "100%" }}}}>
         <img src={{imageUrl}} alt="inspection" style={{{{ width: "100%" }}}} />
         {{findings.filter(f => f.bbox).map((f, i) => {{
           const [x1,y1,x2,y2] = f.bbox!;
           return (
             <Box key={{i}} sx={{{{
               position: "absolute", left: `${{x1}}%`, top: `${{y1}}%`,
               width: `${{x2-x1}}%`, height: `${{y2-y1}}%`,
               border: `2px solid ${{SEV_COLORS[f.severity] || "#fff"}}`,
               boxSizing: "border-box",
             }}}}>
               <Typography variant="caption"
                 sx={{{{ bgcolor: SEV_COLORS[f.severity] || "#fff",
                        color: "#000", px: 0.5 }}}}>
                 {{f.label}} {{Math.round(f.confidence*100)}}%
               </Typography>
             </Box>
           );
         }})}}
       </Box>
     );
   }}

9. frontend/src/components/InspectionResults.tsx
   import React from "react";
   import {{ Card, CardContent, Typography, Chip, Table, TableHead,
           TableRow, TableCell, TableBody, Skeleton }} from "@mui/material";
   import {{ InspectionResult }} from "../types";
   interface Props {{ result?: InspectionResult; loading: boolean; }}
   export default function InspectionResults({{ result, loading }}: Props) {{
     if (loading) return <Card><CardContent><Skeleton height={{200}} /></CardContent></Card>;
     return (
       <Card sx={{{{ bgcolor: "background.paper", mb: 2 }}}}>
         <CardContent>
           <Typography variant="h6" sx={{{{ mb: 1 }}}}>Inspection Results</Typography>
           {{result ? (
             <>
               <Chip label={{result.pass_fail}}
                 color={{result.pass_fail === "PASS" ? "success" : "error"}} sx={{{{ mb: 1 }}}} />
               <Typography variant="caption" display="block" color="text.secondary">
                 {{result.timestamp}} — {{result.model_used}}
               </Typography>
               {{result.findings.length > 0 && (
                 <Table size="small" sx={{{{ mt: 1 }}}}>
                   <TableHead>
                     <TableRow>
                       {{["Label","Confidence","Severity","Description"].map(h =>
                         <TableCell key={{h}} sx={{{{ color: "text.secondary" }}}}>{{h}}</TableCell>)}}
                     </TableRow>
                   </TableHead>
                   <TableBody>
                     {{result.findings.map((f,i) => (
                       <TableRow key={{i}}>
                         <TableCell>{{f.label}}</TableCell>
                         <TableCell>{{Math.round(f.confidence*100)}}%</TableCell>
                         <TableCell>{{f.severity}}</TableCell>
                         <TableCell>{{f.description}}</TableCell>
                       </TableRow>
                     ))}}
                   </TableBody>
                 </Table>
               )}}
             </>
           ) : <Typography color="text.secondary">No results yet.</Typography>}}
         </CardContent>
       </Card>
     );
   }}

10. frontend/src/components/ProxyMetrics.tsx
    import React from "react";
    import {{ Card, CardContent, Typography, Chip, Stack }} from "@mui/material";
    import {{ ProxyMetrics as PM }} from "../types";
    interface Props {{ metrics?: PM; }}
    export default function ProxyMetrics({{ metrics }}: Props) {{
      if (!metrics) return null;
      const latColor = metrics.mean_latency_ms < 500 ? "success"
        : metrics.mean_latency_ms < 2000 ? "warning" : "error";
      const confColor = metrics.mean_confidence > 0.7 ? "success"
        : metrics.mean_confidence > 0.4 ? "warning" : "error";
      return (
        <Card sx={{{{ bgcolor: "background.paper", mb: 2 }}}}>
          <CardContent>
            <Typography variant="h6" sx={{{{ mb: 1 }}}}>Proxy Metrics</Typography>
            <Stack direction="row" spacing={{1}} flexWrap="wrap">
              <Chip label={{`Latency: ${{metrics.mean_latency_ms}}ms`}} color={{latColor}} size="small" />
              <Chip label={{`Confidence: ${{(metrics.mean_confidence*100).toFixed(0)}}%`}} color={{confColor}} size="small" />
              <Chip label={{metrics.confidence_drift_alert ? "Drift: ALERT" : "Drift: OK"}}
                color={{metrics.confidence_drift_alert ? "warning" : "success"}} size="small" />
              <Chip label={{metrics.distribution_shift_alert ? "Shift: ALERT" : "Shift: OK"}}
                color={{metrics.distribution_shift_alert ? "warning" : "success"}} size="small" />
            </Stack>
          </CardContent>
        </Card>
      );
    }}

11. frontend/src/components/ProcessTrends.tsx
    import React from "react";
    import {{ Card, CardContent, Typography }} from "@mui/material";
    import {{ LineChart, Line, XAxis, YAxis, CartesianGrid,
            Tooltip, Legend, ResponsiveContainer }} from "recharts";
    interface DataPoint {{ timestamp: string; confidence: number; anomaly_rate: number; }}
    interface Props {{ data: DataPoint[]; }}
    export default function ProcessTrends({{ data }}: Props) {{
      return (
        <Card sx={{{{ bgcolor: "background.paper", mb: 2 }}}}>
          <CardContent>
            <Typography variant="h6" sx={{{{ mb: 1 }}}}>Process Trends</Typography>
            <ResponsiveContainer width="100%" height={{200}}>
              <LineChart data={{data}}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="timestamp" tick={{{{ fill: "#9ca3af", fontSize: 10 }}}} />
                <YAxis yAxisId="left" domain={{[0,1]}} tick={{{{ fill: "#9ca3af" }}}} />
                <YAxis yAxisId="right" orientation="right" domain={{[0,1]}} tick={{{{ fill: "#9ca3af" }}}} />
                <Tooltip contentStyle={{{{ background: "#1a1a1a", border: "none" }}}} />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="confidence"
                  stroke="#22d3ee" dot={{false}} name="Confidence" />
                <Line yAxisId="right" type="monotone" dataKey="anomaly_rate"
                  stroke="#f59e0b" dot={{false}} name="Anomaly Rate" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      );
    }}

12. frontend/src/components/ReportHistory.tsx
    import React from "react";
    import {{ Card, CardContent, Typography, List, ListItem,
            ListItemText, IconButton }} from "@mui/material";
    import DownloadIcon from "@mui/icons-material/Download";
    import {{ Report }} from "../types";
    interface Props {{ reports: Report[]; onDownload: (filename: string) => void; }}
    export default function ReportHistory({{ reports, onDownload }}: Props) {{
      return (
        <Card sx={{{{ bgcolor: "background.paper" }}}}>
          <CardContent>
            <Typography variant="h6" sx={{{{ mb: 1 }}}}>Report History</Typography>
            {{reports.length === 0
              ? <Typography color="text.secondary">No reports yet.</Typography>
              : <List dense>
                  {{reports.map(r => (
                    <ListItem key={{r.filename}} secondaryAction={{
                      <IconButton edge="end" onClick={{() => onDownload(r.filename)}}
                        sx={{{{ color: "secondary.main" }}}}>
                        <DownloadIcon />
                      </IconButton>
                    }}>
                      <ListItemText primary={{r.filename}}
                        secondary={{`${{(r.size_bytes/1024).toFixed(1)}} KB`}} />
                    </ListItem>
                  ))}}
                </List>
            }}
          </CardContent>
        </Card>
      );
    }}

13. frontend/src/App.tsx
    Full app with ThemeProvider, Grid layout, WebSocket, file upload.
    Import: React, useState, useEffect, useCallback, ThemeProvider, CssBaseline,
    Grid, AppBar, Toolbar, Typography, Select, MenuItem, Button, Chip, Box.
    Import all components and hooks.
    State: result, loading, reports, trendData, taskType, wsStatus.
    useWebSocket("ws://localhost:8000/ws/stream") — on lastMessage update result.
    useEffect: load reports on mount via listReports().
    handleUpload: file input change → uploadImage → setResult, add to trendData.
    handleTrigger: triggerInspection → setLoading → getResults → setResult.
    Layout:
      AppBar with title "Vision_Inspect", health chip, WS status chip.
      Grid container spacing=2:
        xs=12 md=4: CameraFeed, DefectOverlay (if result has findings with bbox)
        xs=12 md=4: InspectionResults, ProxyMetrics (extract from result if available)
        xs=12 md=4: ProcessTrends, ReportHistory
      Hidden file input (ref). Upload Button triggers it. Task type Select.

14. frontend/src/index.tsx
    import React from "react";
    import ReactDOM from "react-dom/client";
    import App from "./App";
    const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
    root.render(<React.StrictMode><App /></React.StrictMode>);

After writing all files, use "List Vision_Inspect Directory" with
dirpath="frontend/src" and dirpath="frontend/src/components" to verify.
"""

PHASE_VI_E = f"""
PHASE VI-E: Vision_Inspect — Training Scaffold and README

Vision_Inspect root: {_R}

Use ONLY "Write Vision_Inspect File" for ALL file writes.

FILES TO CREATE:

1. training/dataset_template.json
   JSON array. Include 3 complete conversation examples:
   a) Defect detection with bounding box annotation
   b) Nameplate OCR extraction
   c) Process deviation flagging
   Format each entry as a conversations array with "from" and "value" fields,
   where human turn has an image path and inspection prompt,
   and gpt turn has a JSON string response with findings/confidence/pass_fail.
   Make the examples realistic for manufacturing inspection.

2. training/llama_factory_qlora.yaml
   LlamaFactory QLoRA recipe for Qwen3-VL-8B fine-tuning.
   Include these sections with proper YAML formatting:
   model: model_name_or_path: Qwen/Qwen3-VL-8B-Instruct, visual_inputs: true
   method: stage: sft, finetuning_type: lora, lora_rank: 16, lora_alpha: 32,
     lora_dropout: 0.05, lora_target: q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj
   dataset: dataset: vision_inspect_defects, dataset_dir: training/,
     template: qwen3_vl, cutoff_len: 2048, max_samples: 5000
   output: output_dir: models/versions/qlora_finetuned, overwrite_output_dir: true
   train: per_device_train_batch_size: 1, gradient_accumulation_steps: 8,
     learning_rate: 1.0e-4, num_train_epochs: 3, bf16: true
   eval: val_size: 0.1, eval_steps: 100

3. training/COLLECTING_DATA.md
   Markdown instructions for collecting labeled training data.
   Sections:
   ## Overview
   ## Step 1 — Enable Frame Saving
   ## Step 2 — Collect Raw Frames
   ## Step 3 — Label with Bounding Boxes (LabelImg or Roboflow)
   ## Step 4 — Convert to dataset_template.json Format
   ## Step 5 — Run Fine-Tuning (llamafactory-cli train command)
   ## Step 6 — Register with Ollama and Activate

4. README.md
   Complete project documentation with these sections:
   # Vision_Inspect
   (One paragraph: local shop-floor monitoring system, never modifies processes,
    sees everything touches nothing reports everything)

   ## Architecture
   (ASCII flow: Camera/Upload → Ingestion → Preprocessing → VLM Inference
    → Report Generator → outputs/inspection_reports/)
   (Tech stack: FastAPI backend, React + MUI v5 frontend, Ollama VLMs)

   ## Requirements
   (Python 3.11+, Ollama, 8GB+ VRAM recommended, Node.js 18+)

   ## Quick Start
   (Step by step: clone, pip install, ollama pull commands, uvicorn command,
    npm install + npm start)

   ## Configuration Reference
   (Table of all 4 config files: File | Purpose | Key Settings)

   ## Input Modes
   (Table: Mode | YAML value | Description)

   ## Inspection Endpoints
   (Table: Endpoint | Method | Capability | Model Used)

   ## Proxy Metrics
   (What each metric means, when alerts trigger, silent failure detection)

   ## Model Versioning
   (How to create, list, and rollback versions via API)

   ## Notifications
   (How to configure Teams and email in notification_config.yaml)

   ## Fine-Tuning
   (Reference to training/COLLECTING_DATA.md)

   ## Important: Observation Only
   (This system never modifies, interrupts, or sends commands to any
    monitored process. All reports are for human review only.)

After writing all files, use "List Vision_Inspect Directory" to confirm
the full root structure, then confirm training/ and README.md exist.
"""

PHASE_VI_COMMIT = f"""
PHASE VI-COMMIT: Commit and Push All Vision_Inspect Files

Vision_Inspect repo: {_R}

STEP 1 — Use "List Vision_Inspect Directory" to verify these files exist:
  Root: .gitignore, requirements.txt, README.md
  backend/: __init__.py, main.py, vlm_router.py, config_loader.py,
    hardware_abstraction.py, proxy_metrics.py, notifier.py,
    model_versioning.py, report_generator.py
  backend/pipeline/: __init__.py, ingestion.py, preprocessing.py,
    inference.py, monitoring.py
  configs/: input_config.yaml, vlm_config.yaml, inspection_config.yaml,
    notification_config.yaml
  frontend/: package.json, tsconfig.json
  frontend/src/: App.tsx, index.tsx, api.ts, types.ts
  frontend/src/components/: 6 component files
  frontend/src/hooks/: useWebSocket.ts
  frontend/src/theme/: theme.ts
  training/: dataset_template.json, llama_factory_qlora.yaml, COLLECTING_DATA.md

STEP 2 — Use "Git Status" to see all untracked files.

STEP 3 — Use "Git Stage Files" with paths="." to stage everything.

STEP 4 — Use "Git Commit" with message:
  "Initial commit: Vision_Inspect visual process monitoring system"

STEP 5 — Use "Git Push" to push to origin/main.

Report the commit hash.
"""


# ══════════════════════════════════════════════════════════════════════════════
#  CREW BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _lm(base_url: str, model: str, temp: float, timeout: int) -> LLM:
    return LLM(model=f"ollama/{model}", base_url=base_url,
               temperature=temp, timeout=timeout)


def build_crew(phase_goal: str, config: dict) -> Crew:
    base_url = config["llm"].get("base_url", "http://localhost:11434")
    timeout  = config["llm"].get("timeout", 600)
    verbose  = config["crew"].get("verbose", True)
    max_rpm  = config["crew"].get("max_rpm", 10)

    # All agents use 14B coder for better tool-use reliability.
    # Builder gets ONLY VI tools — cannot accidentally use Smith_Agentic outputs/.
    llm_build  = _lm(base_url, "qwen2.5-coder:14b", 0.2, timeout)
    llm_plan   = _lm(base_url, "qwen2.5:14b",       0.3, timeout)
    llm_qa     = _lm(base_url, "llama3.1:8b",        0.1, timeout)
    llm_sec    = _lm(base_url, "qwen2.5:14b",        0.2, timeout)

    vi_write  = VisionInspectWriteTool()
    vi_read   = VisionInspectReadTool()
    vi_list   = VisionInspectListTool()
    web_search = WebSearchTool()
    web_fetch  = WebFetchTool()
    code_exec  = CodeExecutorTool()
    file_write = FileWriteTool()   # only for orchestrator/critic logs to outputs/
    file_read  = FileReadTool()
    file_list  = FileListTool()
    git_status = GitStatusTool(repo_path=_VI_ROOT_STR)
    git_stage  = GitStageTool(repo_path=_VI_ROOT_STR)
    git_commit = GitCommitTool(repo_path=_VI_ROOT_STR)
    git_push   = GitPushTool(repo_path=_VI_ROOT_STR)
    mem_store, mem_query = create_memory_tools(config)

    # ── Commit phase ─────────────────────────────────────────────────────────
    if "PHASE VI-COMMIT" in phase_goal:
        critic = create_critic(
            llm=llm_plan,
            tools=[vi_list, vi_read, git_status, git_stage,
                   git_commit, git_push, file_list, mem_query],
            verbose=verbose,
        )
        return Crew(
            agents=[critic],
            tasks=[Task(description=phase_goal,
                        expected_output="All files committed and pushed.",
                        agent=critic)],
            process=Process.sequential,
            verbose=verbose,
            max_rpm=max_rpm,
        )

    # ── Standard build phases ─────────────────────────────────────────────────
    orchestrator = create_orchestrator(
        llm=llm_plan,
        tools=[vi_list, vi_read, web_search, web_fetch, file_write, file_list, mem_query],
        verbose=verbose,
    )
    # Builder: ONLY VI tools — guaranteed to write to Vision_Inspect
    builder = create_builder(
        llm=llm_build,
        tools=[vi_write, vi_read, vi_list, web_search, web_fetch, mem_store, mem_query],
        verbose=verbose,
    )
    critic = create_critic(
        llm=llm_plan,
        tools=[vi_read, vi_list, file_write, file_list, mem_query],
        verbose=verbose,
    )
    qa_agent = create_qa_agent(
        llm=llm_qa,
        tools=[vi_read, vi_list, file_write, file_list, code_exec, mem_store, mem_query],
        verbose=verbose,
    )
    security_agent = create_security_agent(
        llm=llm_sec,
        tools=[vi_read, vi_list, file_write, file_list, mem_store, mem_query],
        verbose=verbose,
    )
    deploy_agent = create_deploy_agent(
        llm=llm_sec,
        tools=[vi_read, vi_list, file_write, file_list, code_exec, mem_store, mem_query],
        verbose=verbose,
    )

    plan_task = Task(
        description=(
            "Analyze this Vision_Inspect build phase and list exactly what to build.\n\n"
            f"PHASE:\n{phase_goal}\n\n"
            "Output a numbered list: each file to create, its path relative to "
            "Vision_Inspect root, and a one-line summary of its content.\n"
            "Use 'List Vision_Inspect Directory' to see current state first."
        ),
        expected_output="Numbered file list with paths and content summaries.",
        agent=orchestrator,
    )

    build_task = Task(
        description=(
            "Write all files listed in the plan to the Vision_Inspect repository.\n\n"
            f"FULL SPECIFICATION:\n{phase_goal}\n\n"
            "CRITICAL RULES:\n"
            "1. Use 'Write Vision_Inspect File' for EVERY file. No exceptions.\n"
            "2. filepath must be relative to Vision_Inspect root "
            "   (e.g. 'backend/main.py', NOT an absolute path).\n"
            "3. Write COMPLETE files. No TODOs. No stubs. No placeholder comments.\n"
            "4. After writing each file, call 'Read Vision_Inspect File' to confirm it saved.\n"
            "5. Do NOT skip any file from the specification.\n"
        ),
        expected_output="All specified files written and verified in Vision_Inspect.",
        agent=builder,
        context=[plan_task],
    )

    critique_task = Task(
        description=(
            "Verify every file specified in the phase was written correctly.\n\n"
            "For each file:\n"
            "1. Use 'Read Vision_Inspect File' to read it.\n"
            "2. Is it complete? No TODOs, no stubs, no truncation?\n"
            "3. Are all imports present?\n"
            "4. Does it match the spec?\n\n"
            "Verdict: APPROVED or NEEDS REVISION (list file + exact issue).\n"
            "Write your verdict to critique.md using 'Write Output File'."
        ),
        expected_output="critique.md written with APPROVED or NEEDS REVISION.",
        agent=critic,
        context=[plan_task, build_task],
    )

    revise_task = Task(
        description=(
            "Fix every issue listed in critique.md.\n\n"
            "Read critique.md using 'Read Output File'.\n"
            "For each NEEDS REVISION item:\n"
            "  - Read the file with 'Read Vision_Inspect File'\n"
            "  - Fix the issue\n"
            "  - Write the corrected file with 'Write Vision_Inspect File'\n"
            "If APPROVED: proceed without changes.\n"
            "Write revised_log.md to outputs/ via 'Write Output File'."
        ),
        expected_output="All critique issues fixed.",
        agent=builder,
        context=[plan_task, build_task, critique_task],
    )

    # Only run QA/Security/Deploy on backend Python phases (vi_b and vi_c)
    is_code_phase = any(kw in phase_goal for kw in
                        ["backend/__init__", "backend/main.py", "vlm_router",
                         "proxy_metrics", "notifier", "ingestion"])

    if is_code_phase:
        qa_task = Task(
            description=(
                "Syntax-check all Python files written in this phase.\n\n"
                "For each .py file: read it with 'Read Vision_Inspect File', "
                "then run via 'Execute Python Code':\n"
                "  import ast\n"
                "  ast.parse('''<file content>''')\n"
                "  print('SYNTAX_OK')\n"
                "Write qa_report.md to outputs/. "
                "Verdict: SENTINEL_PASS or SENTINEL_BLOCK."
            ),
            expected_output="qa_report.md written.",
            agent=qa_agent,
            context=[plan_task, revise_task],
        )
        sec_task = Task(
            description=(
                "Security audit all Python files in this phase.\n\n"
                "Read each .py file via 'Read Vision_Inspect File'.\n"
                "Check: hardcoded credentials, shell injection, path traversal, "
                "eval/exec on user input. NOTE: localhost Ollama calls are expected.\n"
                "Write security_report.md to outputs/. "
                "Verdict: SECURITY_PASS, SECURITY_PASS_WITH_WARNINGS, SECURITY_BLOCK."
            ),
            expected_output="security_report.md written.",
            agent=security_agent,
            context=[plan_task, revise_task],
        )
        return Crew(
            agents=[orchestrator, builder, critic, qa_agent, security_agent],
            tasks=[plan_task, build_task, critique_task, revise_task, qa_task, sec_task],
            process=Process.sequential,
            verbose=verbose,
            max_rpm=max_rpm,
        )

    # Config/frontend/docs phases: plan + build + critique + revise only
    return Crew(
        agents=[orchestrator, builder, critic],
        tasks=[plan_task, build_task, critique_task, revise_task],
        process=Process.sequential,
        verbose=verbose,
        max_rpm=max_rpm,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

PHASES = {
    "vi_a":      PHASE_VI_A,
    "vi_b":      PHASE_VI_B,
    "vi_c":      PHASE_VI_C,
    "vi_d":      PHASE_VI_D,
    "vi_e":      PHASE_VI_E,
    "vi_commit": PHASE_VI_COMMIT,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Vision_Inspect build crew.")
    parser.add_argument("--phase", default="vi_a", choices=list(PHASES.keys()))
    args = parser.parse_args()

    config = load_config()
    config["crew"]["hitl"]    = False
    config["crew"]["verbose"] = True

    print(f"\n{'='*60}")
    print(f"  Vision_Inspect Build — Phase {args.phase.upper()}")
    print(f"  Target: {_VI_ROOT_STR}")
    print(f"{'='*60}\n")

    crew   = build_crew(PHASES[args.phase], config)
    result = crew.kickoff()

    print(f"\n{'='*60}")
    print(f"  Phase {args.phase.upper()} Complete")
    print(f"{'='*60}")
    print(result)


if __name__ == "__main__":
    main()
