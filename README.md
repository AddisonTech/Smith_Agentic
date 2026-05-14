# SmithAgentic - Local Multi-Agent AI System

A fully local, open-source multi-agent AI system built on **CrewAI** + **Ollama**.
No paid APIs. No cloud dependencies. Everything runs on your machine.

---

## What it does

You give it a goal. A crew of specialized agents works through it - planning, researching, building, reviewing, validating, and documenting - entirely locally via Ollama.

All outputs are saved to `outputs/` as markdown or code files.

---

## Agent Team

| Agent | Role | Crew | Model Tier |
|---|---|---|---|
| Orchestrator | Plans and decomposes goals | Default | 7B |
| Researcher | Gathers information | Default | 7B |
| Builder | Produces deliverables | Default | 7B-Coder |
| Critic | Reviews output quality | Default | 7B |
| QA Sentinel | Executes code, blocks on failures | Safety | 8B |
| Security Reviewer | OWASP/vulnerability scanning | Safety | 7B |
| Deployment Validator | Compile and deploy checks | Safety | 7B |
| Documentation Writer | Generates structured docs | Ops | 8B |
| Memory Manager | Consolidates run knowledge | Ops | 8B |
| Observability Monitor | Run telemetry and audit | Ops | 8B |
| PLC Planner | PLC program structure | PLC | 8B |
| PLC Developer | Ladder logic / AOI code | PLC | 8B |
| PLC Safety Reviewer | NFPA/IEC safety compliance | PLC | 8B |
| UI Planner | React component design | React | 8B |
| UI Builder | React/MUI component code | React | 8B |
| UI Reviewer | React code quality review | React | 8B |
| Vision Analyst | Queries Vision_Inspect API, parses defect results | Vision | 7B |
| Vision Reporter | Synthesizes findings into structured reports | Vision | 8B |
| Vision QA Validator | Health-checks pipeline, audits reports, detects anomalies | Vision | 8B |

---

## Agents

### Default crew agents

| File | Role | Specialization |
|---|---|---|
| `agents/orchestrator.py` | Orchestrator | Decomposes any goal into a structured execution plan |
| `agents/researcher.py` | Researcher | General-purpose technical research and synthesis (shared across all crews) |
| `agents/builder.py` | Builder | Produces deliverables for any domain |
| `agents/critic.py` | Critic | Reviews deliverables against goal and plan |

### Safety crew agents

| File | Role | Specialization |
|---|---|---|
| `agents/qa_agent.py` | QA Sentinel | Executes code artifacts, blocks on crashes or import failures |
| `agents/security_agent.py` | Security Reviewer | OWASP Top-10 audit, hardcoded credential detection, injection risk scanning |
| `agents/deploy_agent.py` | Deployment Validator | py_compile checks, import chain validation, deploy readiness verdict |

### Ops crew agents

| File | Role | Specialization |
|---|---|---|
| `agents/docs_agent.py` | Documentation Writer | Generates structured README, API reference, and quickstart docs |
| `agents/memory_agent.py` | Memory Manager | Distills run outputs into tagged ChromaDB memory entries |
| `agents/observability_agent.py` | Observability Monitor | Reads all run outputs, reconstructs agent trace, produces telemetry report |

### PLC crew agents

| File | Role | Specialization |
|---|---|---|
| `agents/plc_planner.py` | PLC Program Planner | ControlLogix architecture, program hierarchy, I/O tag lists, AOI/UDT planning; aware of `plc_generator/` codebase |
| `agents/researcher.py` | PLC Standards Researcher | Reuses general researcher with PLC-specific tool access (codebase reader + memory) |
| `agents/plc_developer.py` | PLC Developer | Ladder logic, structured text, function blocks, AOI/UDT authoring; reads and extends `plc_generator/` modules |
| `agents/plc_safety_reviewer.py` | PLC Safety Reviewer | NFPA 79, ISO 13849, IEC 62061, ISA-88 compliance; fault handling and interlock completeness |

### React crew agents

| File | Role | Specialization |
|---|---|---|
| `agents/ui_planner.py` | React UI Planner | Component tree design, data flow, MUI v5 theming, industrial HMI patterns |
| `agents/researcher.py` | React Technical Researcher | Reuses general researcher with codebase reader access to study existing components |
| `agents/ui_builder.py` | React UI Developer | React 18 + MUI v5, dark industrial theme, complete drop-in components |
| `agents/ui_reviewer.py` | React UI Reviewer | Correctness, industrial UX, accessibility, performance, stack consistency |

### Vision crew agents

| File | Role | Specialization |
|---|---|---|
| `agents/vision_analyst.py` | Vision Inspection Analyst | Queries Vision_Inspect `/inspections` API; parses defect type, severity, confidence, zone; produces `vision_findings.md` |
| `agents/vision_reporter.py` | Vision Inspection Reporter | Reads analyst findings + ChromaDB trends; writes `inspection_report.md` with executive summary, statistics, defect breakdown, trend comparison, and recommended actions |
| `agents/vision_qa.py` | Vision QA Validator | Health-checks `/health` endpoint; audits report completeness and numeric consistency; flags zero-defect anomalies vs. historical baseline; writes `vision_qa_report.md` |

---

## Features

| Feature | Details |
|---|---|
| **ChromaDB Memory** | Agents store and query insights across sessions via `memory/chroma/` |
| **Reflexion Loop** | Default crew runs plan, research, build, and critique in sequence |
| **Per-Agent Routing** | Each agent uses its optimal model tier (configured in `agent_models:`) |
| **Human-in-the-loop** | Plan approval step before full crew runs (can skip with `--no-hitl`) |
| **Code Executor** | Agents can run Python snippets and capture output |
| **QA Sentinel** | Blocks pipeline if generated code crashes, fails imports, or has syntax errors |
| **Security Reviewer** | OWASP Top-10 audit of all generated code before delivery |
| **Deployment Validator** | py_compile checks on all Python artifacts before final output |
| **Observability Monitor** | Produces telemetry_report.md after every run for developer review |
| **Git Tool** | Agents can stage, commit, and push changes via GitPython |
| **Codebase Reader** | Agents can read any file in the repo before generating new code |
| **PLC Crew** | Domain-tuned agents for Rockwell Logix / ladder logic / AOI development |
| **React Crew** | Domain-tuned agents for industrial React/MUI HMI development |
| **Vision Crew** | Connects to Vision_Inspect backend; runs defect analysis, report generation, and pipeline QA |
| **Safety Crew** | Standalone QA, security, and deploy validation pipeline for any deliverable |
| **Ops Crew** | Standalone documentation, memory consolidation, and telemetry pipeline |
| **Chain Flag** | `--chain` runs safety then ops automatically after any primary crew finishes |
| **Web UI** | FastAPI + React CDN frontend with live WebSocket output streaming |

---

## Prerequisites

- **Python 3.10+**
- **Ollama** installed and running: https://ollama.com
- At least one model pulled into Ollama:
  ```
  ollama pull llama3.1:8b
  ```

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/AddisonTech/Smith_Agentic.git
cd Smith_Agentic

# 2. (Recommended) Create a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Make sure Ollama is running
ollama serve
```

---

## Running - CLI

```bash
# Default crew
python main.py --goal "Write a technical spec for a REST API rate limiter"

# PLC-specialized crew
python main.py --goal "Build a Rockwell Logix program for a conveyor E-stop system" --crew plc

# React-specialized crew
python main.py --goal "Build a React dashboard for machine OEE metrics" --crew react

# Vision inspection crew (requires Vision_Inspect running on port 8000)
python main.py --goal "Run a defect analysis on today's inspection batch" --crew vision

# Safety crew - validates deliverable in outputs/ for code quality, security, and deploy readiness
python main.py --goal "Validate the deliverable in outputs/" --crew safety

# Ops crew - generates docs, consolidates memory, and produces telemetry for the last run
python main.py --goal "Generate docs and telemetry for the last run" --crew ops

# Override model
python main.py --goal "..." --model qwen2.5:14b

# Skip human-in-the-loop plan approval
python main.py --goal "..." --no-hitl

# Suppress verbose agent output
python main.py --goal "..." --no-verbose
```

---

## Running - Web UI

```bash
python ui/server.py
```

Open **http://localhost:8765** in your browser.

Features:
- Goal input + crew/model selector
- Live streaming agent output (WebSocket)
- Download output files directly from the browser
- Ollama online/offline indicator

---

## Human-in-the-Loop Plan Approval

Before the full crew runs, the Orchestrator generates an execution plan and shows it to you:

```
============================================================
  HUMAN-IN-THE-LOOP: Plan Approval
============================================================
  Goal: Build a conveyor E-stop system
  Generating execution plan...

------------------------------------------------------------
  PROPOSED PLAN (iteration 1):
  1. Research NFPA 79 E-stop requirements...
  2. Define I/O tags and UDTs...
  ...

  [A]pprove and continue  /  type revision notes:
```

- Press **Enter** or type `a` to approve and launch the full crew.
- Type revision notes to have the Orchestrator regenerate the plan.
- Use `--no-hitl` (CLI) or the Web UI (always runs without blocking) to skip.

---

## ChromaDB Memory

Agents automatically store key findings and recall relevant past work:

- **MemoryStoreTool** - saves insights with a topic tag + session ID
- **MemoryQueryTool** - retrieves semantically similar past memories
- Persists to `memory/chroma/` across runs
- Session ID tags let you distinguish different run histories

Memory is enabled by default. To disable:
```yaml
# config/config.yaml
memory:
  enabled: false
```

---

## Output Files

**Default crew**

| File | Contents |
|---|---|
| `research.md` | Researcher's findings |
| `deliverable.md` | Builder's initial deliverable |
| `critique.md` | Reviewer's notes (APPROVED / NEEDS REVISION) |
| `deliverable_revised.md` | Builder's revised deliverable |
| `revision_summary.md` | What changed and why |

**Safety crew**

| File | Contents |
|---|---|
| `qa_report.md` | QA Sentinel verdict (SENTINEL_PASS / SENTINEL_BLOCK), exit code, errors |
| `security_report.md` | Security Reviewer findings by category and severity |
| `deploy_report.md` | Deployment Validator verdict (DEPLOY_READY / DEPLOY_BLOCKED) with numbered issues |

**Ops crew**

| File | Contents |
|---|---|
| `docs/deliverable_docs.md` | Documentation Writer output: overview, setup, usage, API reference, examples |
| `memory_summary.md` | Memory Manager report listing what was stored to ChromaDB |
| `telemetry_report.md` | Observability Monitor trace: agents run, files produced, verdicts, recommendations |

---

## Models

Each crew runs on its optimal model by default. Models are configured in `config/config.yaml` under `crew_models` - no code changes needed to swap them.

Per-crew defaults (set in `crew_models:`) and per-agent routing (set in `agent_models:`):

| Crew | Default model | Why |
|---|---|---|
| **default** | `qwen2.5:7b` (plan/research) + `qwen2.5-coder:7b` (build) | Balanced reasoning + specialized coder for generation |
| **safety** | `llama3.1:8b` | Fast and reliable for code execution, audit, and validation tasks |
| **ops** | `llama3.1:8b` | Strong instruction following for documentation and memory consolidation |
| **plc** | `qwen2.5:7b` | Strong instruction following for safety-critical PLC work |
| **react** | `qwen2.5-coder:7b` | Purpose-built for code generation - React/JS/TS |
| **vision** | `qwen2.5:7b` | Solid reasoning for defect analysis and report generation |

**Pull the recommended models:**

```bash
ollama pull qwen2.5:7b           # planning, research, review
ollama pull qwen2.5-coder:7b     # code generation
ollama pull llama3.1:8b          # fast specialist agents (QA, Docs, Memory, Observability)
```

**Override for a single run:**

```bash
python main.py --goal "..." --model qwen2.5:14b
```

**Swap a crew's default permanently** - edit `config/config.yaml`:

```yaml
crew_models:
  default: qwen2.5:32b
  plc:     qwen2.5:14b
  react:   qwen2.5-coder:14b   # ← change this
```

**Web UI** - the model selector auto-switches to the configured default when you change crews. You can still select any installed model manually.

**Fallback models** (if 14B models aren't available):

```bash
ollama pull llama3.1:8b          # solid all-around fallback
ollama pull mistral:7b           # fast, instruction-tuned
```

---

## MCP Server

The MCP server exposes SmithAgentic as a set of tools for **Claude Code** and **Claude Desktop** via the Model Context Protocol. Once connected, Claude can start crew runs, poll for progress, and read output files directly - no terminal required.

### Install the MCP dependency

```bash
pip install "mcp>=1.0.0,<2.0.0"
```

### Claude Code setup

```bash
claude mcp add smith_agentic python C:/Users/yourname/Documents/GitHub/Smith_Agentic/mcp_server.py
```

Verify it loaded:
```
/mcp
```

### Claude Desktop setup

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "smith_agentic": {
      "command": "python",
      "args": ["C:/Users/yourname/Documents/GitHub/Smith_Agentic/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop after saving.

### Available tools

| Tool | What it does |
|---|---|
| `check_ollama` | Verify Ollama is running and reachable |
| `list_crews` | Show available crews and descriptions |
| `list_models` | Show installed Ollama models |
| `run_crew(goal, crew, model, chain)` | Start a crew run in the background, returns run_id |
| `get_run_status(run_id)` | Poll a run for status and recent output |
| `list_output_files` | List files in outputs/ |
| `read_output_file(filename)` | Read a specific file from outputs/ |

### Example usage

Once connected, you can ask Claude:

> "Check if Ollama is running, then start a default crew run with the goal: write a Python rate limiter class with tests."

Claude will call `check_ollama`, then `run_crew`, then poll `get_run_status` until complete, then `read_output_file` to show you the result.

Crew runs take several minutes. `get_run_status` returns the last 20 lines of agent output so you can see what's happening.

---

## Vision Crew

The Vision Crew integrates with the **Vision_Inspect** backend to run automated inspection analysis entirely within the agent pipeline.

### Prerequisites

The Vision_Inspect FastAPI service must be running before starting the crew:

```bash
cd ../Vision_Inspect
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### What it does

| Step | Agent | Output |
|---|---|---|
| 1 | Vision Analyst | Calls `/inspections` API, parses defect results, writes `vision_findings.md` |
| 2 | Vision Reporter | Reads findings + ChromaDB trends, writes `inspection_report.md` |
| 3 | Vision QA Validator | Health-checks `/health`, audits report, flags anomalies, writes `vision_qa_report.md` |

### Run

```bash
python main.py --goal "Analyze today's inspection batch and report defect trends" --crew vision
```

### Output files

| File | Contents |
|---|---|
| `vision_findings.md` | Raw inspection statistics: pass/fail counts, defect breakdown by type and zone |
| `inspection_report.md` | Full QA report: executive summary, statistics, defect analysis, trend comparison, recommended actions |
| `vision_qa_report.md` | Pipeline health verdict (VISION_QA_PASS / VISION_QA_BLOCK), report completeness check, anomaly flags |

### Config

Connection settings are in `config/config.yaml`:

```yaml
vision_inspect:
  base_url: http://localhost:8000   # Vision_Inspect FastAPI service
  timeout:  30                      # seconds per API call
```

---

## Configuration reference

`config/config.yaml`:

```yaml
llm:
  base_url: http://localhost:11434
  temperature: 0.7
  timeout: 600                # 14B models need more time

crew_models:
  default: qwen2.5:7b        # per-crew model assignments
  plc:     qwen2.5:7b
  react:   qwen2.5-coder:7b
  vision:  qwen2.5:7b
  safety:  llama3.1:8b
  ops:     llama3.1:8b

agent_models:                # per-agent routing
  orchestrator:        qwen2.5:7b
  builder:             qwen2.5-coder:7b
  qa_agent:            llama3.1:8b
  security_agent:      qwen2.5:7b

llm_fallback:
  model: llama3.1:8b         # used if crew not in crew_models

crew:
  process: sequential        # sequential | hierarchical
  verbose: true
  max_rpm: 10
  output_dir: outputs
  hitl: true                 # human-in-the-loop plan approval

memory:
  persist_dir: memory/chroma
  collection: smith_agentic_memory
  enabled: true
```

---

## Project structure

```
smith_agentic/
├── main.py                     # CLI entrypoint
├── mcp_server.py               # MCP server (Claude Code / Claude Desktop integration)
├── requirements.txt
├── README.md
├── config/
│   ├── config.yaml             # model + crew settings
│   └── loader.py
├── agents/
│   ├── orchestrator.py         # default: goal decomposition
│   ├── researcher.py           # shared: general-purpose research (all crews)
│   ├── builder.py              # default: generic deliverable builder
│   ├── critic.py               # default: generic reviewer
│   ├── qa_agent.py             # safety: code execution and QA validation
│   ├── security_agent.py       # safety: OWASP Top-10 vulnerability audit
│   ├── deploy_agent.py         # safety: compile checks and deploy readiness
│   ├── docs_agent.py           # ops: structured markdown documentation
│   ├── memory_agent.py         # ops: ChromaDB knowledge consolidation
│   ├── observability_agent.py  # ops: run telemetry and audit trail
│   ├── plc_planner.py          # plc: ControlLogix architecture + plc_generator/ awareness
│   ├── plc_developer.py        # plc: ladder logic, ST, AOI/UDT, L5X authoring
│   ├── plc_safety_reviewer.py  # plc: NFPA 79, ISO 13849, fault/interlock review
│   ├── ui_planner.py           # react: component tree, data flow, MUI v5
│   ├── ui_builder.py           # react: React 18 + MUI v5, dark industrial theme
│   ├── ui_reviewer.py          # react: correctness, industrial UX, accessibility
│   ├── vision_analyst.py       # vision: queries Vision_Inspect API, parses defects
│   ├── vision_reporter.py      # vision: synthesizes findings + trends into reports
│   └── vision_qa.py            # vision: health-checks pipeline, audits reports
├── tasks/
│   ├── plan.py
│   ├── research.py
│   ├── build.py
│   ├── critique.py
│   ├── revise.py
│   ├── qa_task.py
│   ├── security_task.py
│   ├── deploy_task.py
│   ├── docs_task.py
│   ├── memory_task.py
│   ├── observability_task.py
│   └── vision_tasks.py
├── crews/
│   ├── default_crew.py         # 4-agent crew: plan, research, build, critique
│   ├── safety_crew.py          # QA, security, and deployment validation crew
│   ├── ops_crew.py             # documentation, memory, and observability crew
│   ├── plc_crew.py             # Rockwell Logix / ladder logic crew
│   ├── react_crew.py           # industrial React / MUI crew
│   ├── vision_crew.py          # Vision_Inspect integration crew
│   └── hitl.py                 # human-in-the-loop plan approval helper
├── tools/
│   ├── file_tools.py           # FileReadTool, FileWriteTool, FileListTool
│   ├── search_tool.py          # WebSearchTool (DuckDuckGo)
│   ├── web_fetch_tool.py       # WebFetchTool (raw URL fetch + HTML extraction)
│   ├── code_executor.py        # CodeExecutorTool (subprocess Python runner)
│   ├── git_tool.py             # GitStatusTool, GitStageTool, GitCommitTool, GitPushTool
│   ├── codebase_reader.py      # CodebaseReadTool, CodebaseListTool, CodebaseGlobTool
│   ├── vision_inspect_tool.py  # VisionInspectAPITool + Vision_Inspect file I/O tools
│   └── project_file_tool.py    # ProjectFileReadTool (reads files listed in agent context)
├── memory/
│   ├── memory_store.py         # MemoryStoreTool, MemoryQueryTool (ChromaDB)
│   └── chroma/                 # ChromaDB persistent storage (auto-created)
├── ui/
│   ├── server.py               # FastAPI + WebSocket backend (port 8765)
│   └── index.html              # React CDN frontend
└── outputs/                    # all agent outputs land here
    └── .gitkeep
```

---

## Adding a new crew

1. Create `crews/my_crew.py` with a `build_crew(goal, config)` function returning a `crewai.Crew`.
2. Add the crew name to `_CREW_BUILDERS` in `main.py`.
3. Add the crew name to the `builders` dict in `ui/server.py` and to the `api_crew_defaults` return value.
4. Add a default model entry under `crew_models:` in `config/config.yaml`.
5. Run with: `python main.py --goal "..." --crew my_crew`

---

## Adding a new agent

```python
# agents/my_agent.py
from crewai import Agent, LLM

def create_my_agent(llm: LLM, tools: list, verbose: bool = True) -> Agent:
    return Agent(
        role="My Agent Role",
        goal="What this agent is trying to accomplish.",
        backstory="Domain expertise and constraints for this agent.",
        llm=llm,
        tools=tools,
        verbose=verbose,
    )
```

1. Create `agents/my_agent.py` with a `create_my_agent(llm, tools, verbose)` function.
2. Create the corresponding task in `tasks/my_task.py`.
3. Import and wire the agent into the relevant crew file (`crews/default_crew.py` or a new crew).
4. Optionally add a per-agent model entry under `agent_models:` in `config/config.yaml`.

---

## Adding a new tool

```python
# tools/my_tool.py
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

class _MyInput(BaseModel):
    param: str = Field(description="What this parameter does.")

class MyTool(BaseTool):
    name: str = "My Tool Name"
    description: str = "What this tool does and when to use it."
    args_schema: Type[BaseModel] = _MyInput

    def _run(self, param: str) -> str:
        return f"Result for: {param}"
```

Then pass an instance to any agent's `tools=[]` list in the crew file.

---

## Troubleshooting

**"Cannot connect to Ollama"**
Run `ollama serve` in a separate terminal. The default URL is `http://localhost:11434`.

**ChromaDB install fails**
On some systems: `pip install chromadb --no-build-isolation`. If it still fails, set `memory.enabled: false` in config.yaml to disable memory entirely.

**Web UI shows blank / won't load**
Make sure `python ui/server.py` is running and port 8765 is not blocked. The UI uses CDN React - you need an internet connection on first load.

**Runs are slow**
- Use a smaller model (`llama3.1:8b`, `mistral:7b`)
- Increase `timeout` in `config.yaml` if hitting timeouts
- Set `verbose: false` to reduce console I/O

**Agent loops or repeats itself**
Lower `max_iter` in the agent file. Use `--no-hitl` to skip plan approval if it loops there.

**DuckDuckGo search fails**
DDG rate-limits aggressively. The tool fails gracefully and the agent continues without search results.
