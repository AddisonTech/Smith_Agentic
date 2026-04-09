# SmithAgentic — Local Multi-Agent AI System

A fully local, open-source multi-agent AI system built on **CrewAI** + **Ollama**.
No paid APIs. No cloud dependencies. Everything runs on your machine.

---

## What it does

You give it a goal. A crew of specialized agents works through it:

| Role | Default crew | PLC crew | React crew |
|---|---|---|---|
| **Planner** | `orchestrator.py` | `plc_planner.py` | `ui_planner.py` |
| **Researcher** | `researcher.py` | `researcher.py` | `researcher.py` |
| **Builder** | `builder.py` | `plc_developer.py` | `ui_builder.py` |
| **Reviewer** | `critic.py` | `plc_safety_reviewer.py` | `ui_reviewer.py` |

All outputs are saved to `outputs/` as markdown or code files.

---

## Agents

### Default crew agents

| File | Role | Specialization |
|---|---|---|
| `agents/orchestrator.py` | Orchestrator | Decomposes any goal into a structured execution plan |
| `agents/researcher.py` | Researcher | General-purpose technical research and synthesis (shared across all crews) |
| `agents/builder.py` | Builder | Produces deliverables for any domain |
| `agents/critic.py` | Critic | Reviews deliverables against goal and plan |

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

---

## Features

| Feature | Details |
|---|---|
| **ChromaDB Memory** | Agents store and query insights across sessions via `memory/chroma/` |
| **Human-in-the-loop** | Plan approval step before full crew runs (can skip with `--no-hitl`) |
| **Code Executor** | Agents can run Python snippets and capture output |
| **Git Tool** | Agents can stage, commit, and push changes via GitPython |
| **Codebase Reader** | Agents can read any file in the repo before generating new code |
| **PLC Crew** | Domain-tuned agents for Rockwell Logix / ladder logic / AOI development |
| **React Crew** | Domain-tuned agents for industrial React/MUI HMI development |
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
git clone https://github.com/AddisonTech/smith_agentic.git
cd smith_agentic

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

## Running — CLI

```bash
# Default crew
python main.py --goal "Write a technical spec for a REST API rate limiter"

# PLC-specialized crew
python main.py --goal "Build a Rockwell Logix program for a conveyor E-stop system" --crew plc

# React-specialized crew
python main.py --goal "Build a React dashboard for machine OEE metrics" --crew react

# Override model
python main.py --goal "..." --model qwen2.5:14b

# Skip human-in-the-loop plan approval
python main.py --goal "..." --no-hitl

# Suppress verbose agent output
python main.py --goal "..." --no-verbose
```

---

## Running — Web UI

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

- **MemoryStoreTool** — saves insights with a topic tag + session ID
- **MemoryQueryTool** — retrieves semantically similar past memories
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

| File | Contents |
|---|---|
| `research.md` | Researcher's findings |
| `deliverable.md` | Builder's initial deliverable |
| `critique.md` | Reviewer's notes (APPROVED / NEEDS REVISION) |
| `deliverable_revised.md` | Builder's revised deliverable |
| `revision_summary.md` | What changed and why |

---

## Models

Each crew runs on its optimal model by default. Models are configured in `config/config.yaml` under `crew_models` — no code changes needed to swap them.

| Crew | Default model | Why |
|---|---|---|
| **default** | `deepseek-r1:14b` | Best open-source reasoning model — handles unknown goal domains, strong chain-of-thought |
| **plc** | `deepseek-r1:14b` | Reasoning is critical for safe PLC planning, interlock logic, and safety review |
| **react** | `qwen2.5-coder:14b` | Purpose-built for code generation — strongest open-source model for React/JS/TS |

**Pull the recommended models:**

```bash
ollama pull deepseek-r1:14b      # reasoning — default + plc crews
ollama pull qwen2.5-coder:14b    # code generation — react crew
```

**Override for a single run:**

```bash
python main.py --goal "..." --model qwen2.5:14b
```

**Swap a crew's default permanently** — edit `config/config.yaml`:

```yaml
crew_models:
  default: deepseek-r1:14b
  plc:     deepseek-r1:14b
  react:   qwen2.5-coder:14b   # ← change this
```

**Web UI** — the model selector auto-switches to the configured default when you change crews. A `★` in the dropdown marks the optimal model for the current crew. You can still select any installed model manually.

**Fallback models** (if 14B models aren't available):

```bash
ollama pull llama3.1:8b          # solid all-around fallback
ollama pull qwen2.5-coder:7b     # smaller code model
ollama pull deepseek-r1:8b       # smaller reasoning model
ollama pull mistral:7b           # fast, instruction-tuned
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
  default: deepseek-r1:14b   # per-crew model assignments
  plc:     deepseek-r1:14b
  react:   qwen2.5-coder:14b

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
│   ├── plc_planner.py          # plc: ControlLogix architecture + plc_generator/ awareness
│   ├── plc_developer.py        # plc: ladder logic, ST, AOI/UDT, L5X authoring
│   ├── plc_safety_reviewer.py  # plc: NFPA 79, ISO 13849, fault/interlock review
│   ├── ui_planner.py           # react: component tree, data flow, MUI v5
│   ├── ui_builder.py           # react: React 18 + MUI v5, dark industrial theme
│   └── ui_reviewer.py          # react: correctness, industrial UX, accessibility
├── tasks/
│   ├── plan.py
│   ├── research.py
│   ├── build.py
│   ├── critique.py
│   └── revise.py
├── crews/
│   ├── default_crew.py         # general-purpose 5-agent crew
│   ├── plc_crew.py             # Rockwell Logix / ladder logic crew
│   ├── react_crew.py           # industrial React / MUI crew
│   └── hitl.py                 # human-in-the-loop plan approval helper
├── tools/
│   ├── file_tools.py           # FileReadTool, FileWriteTool, FileListTool
│   ├── search_tool.py          # WebSearchTool (DuckDuckGo)
│   ├── code_executor.py        # CodeExecutorTool (subprocess Python runner)
│   ├── git_tool.py             # GitStatusTool, GitStageTool, GitCommitTool, GitPushTool
│   └── codebase_reader.py      # CodebaseReadTool, CodebaseListTool, CodebaseGlobTool
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
3. Run with: `python main.py --goal "..." --crew my_crew`

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
Make sure `python ui/server.py` is running and port 8765 is not blocked. The UI uses CDN React — you need an internet connection on first load.

**Runs are slow**
- Use a smaller model (`llama3.1:8b`, `mistral:7b`)
- Increase `timeout` in `config.yaml` if hitting timeouts
- Set `verbose: false` to reduce console I/O

**Agent loops or repeats itself**
Lower `max_iter` in the agent file. Use `--no-hitl` to skip plan approval if it loops there.

**DuckDuckGo search fails**
DDG rate-limits aggressively. The tool fails gracefully and the agent continues without search results.
