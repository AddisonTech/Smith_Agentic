"""
run_expansion.py — Phase 1 expansion runner.

Activates the Smith_Agentic crew with extended project-write tools and runs
the Phase 1 agent team expansion task. The crew reads the full existing
codebase, then creates all new agents, tasks, memory modules, and wires
them into all three existing crews.

Usage:
    python run_expansion.py
    python run_expansion.py --phase 1a   # Core agents (QA, Security, Reflexion)
    python run_expansion.py --phase 1b   # Specialist agents (Docs, Memory)
    python run_expansion.py --phase 1c   # Ops agents (Deploy, Observability)
    python run_expansion.py --phase 1d   # Infra (checkpoints, scratchpad, routing)
    python run_expansion.py --phase 1e   # Integration (wire into all crews + commit)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from crewai import Crew, LLM, Process, Agent, Task

from config.loader import load_config
from agents.orchestrator import create_orchestrator
from agents.researcher import create_researcher
from agents.builder import create_builder
from agents.critic import create_critic

from tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from tools.search_tool import WebSearchTool
from tools.web_fetch_tool import WebFetchTool
from tools.project_file_tool import ProjectFileWriteTool, ProjectFileReadTool, ProjectListTool
from tools.git_tool import GitStatusTool, GitStageTool, GitCommitTool, GitPushTool
from memory.memory_store import create_memory_tools

_PROJECT_ROOT = _HERE  # Smith_Agentic/


# ── Task Specs ────────────────────────────────────────────────────────────────

PHASE_1A_GOAL = """\
PHASE 1A: Create Core Agent Files for Smith_Agentic

PROJECT ROOT: {root}
RULE: Use 'Read Project File' to read existing files — pass paths like 'agents/builder.py'.
RULE: Use 'Write Project File' to create/modify files — pass paths like 'agents/qa_agent.py'.
RULE: Follow existing code patterns EXACTLY — same imports, same docstring style, same factory-function pattern.

STEP 1 — READ THESE FILES FIRST (use Read Project File):
  agents/builder.py
  agents/critic.py
  agents/orchestrator.py
  tasks/build.py
  tasks/critique.py
  tasks/revise.py
  crews/default_crew.py
  memory/memory_store.py
  tools/code_executor.py

STEP 2 — CREATE: agents/qa_agent.py
Factory function: create_qa_agent(llm, tools=None, verbose=True) -> Agent
  role="QA Sentinel"
  goal: Receive the deliverable from the Builder. Execute it if it is Python code using
    the Execute Python Code tool. Examine stdout, stderr, and exit code. If the code
    crashes (exit code != 0), contains a syntax error, or fails a basic import check,
    issue verdict SENTINEL_BLOCK with the exact error. If it passes, issue SENTINEL_PASS.
    Always write your report to 'qa_report.md' using Write Output File.
  backstory: Senior QA engineer. You run code, you do not just read it. Passing review
    means the code actually executes without errors. You block the pipeline on crashes,
    import errors, and syntax failures. You pass only working code.
  allow_delegation=False, max_iter=8
  Tools needed by this agent: file_read, file_write, file_list, code_executor, mem_store, mem_query

STEP 3 — CREATE: tasks/qa_task.py
Factory function: create_qa_task(qa_agent, goal, context=None) -> Task
  Description: Run a QA validation pass on the deliverable for goal: {{goal}}.
    Use Execute Python Code tool to run any Python content in the deliverable.
    Parse the exit code and stderr. Write qa_report.md with:
      - VERDICT: SENTINEL_PASS or SENTINEL_BLOCK
      - EXIT_CODE: (the exit code)
      - ERRORS: (any errors from stderr)
      - SUMMARY: one paragraph
  Expected output: qa_report.md written. Returns SENTINEL_PASS or SENTINEL_BLOCK in task output.

STEP 4 — CREATE: agents/security_agent.py
Factory function: create_security_agent(llm, tools=None, verbose=True) -> Agent
  role="Security Reviewer"
  goal: Review all generated code for OWASP top-10 vulnerabilities, hardcoded secrets,
    injection risks, and unsafe subprocess usage. Read the deliverable using
    Read Output File. Write a security report to 'security_report.md'. If critical
    issues are found (hardcoded credentials, shell injection, arbitrary code execution),
    issue verdict SECURITY_BLOCK. For warnings only, issue SECURITY_PASS_WITH_WARNINGS.
    For clean code, issue SECURITY_PASS.
  backstory: Application security engineer with expertise in OWASP Top 10, Python
    security patterns, and code audit. You read every line, not summaries. You catch
    hardcoded tokens, injection points, and dangerous eval/exec usage.
  allow_delegation=False, max_iter=6
  Tools needed: file_read, file_write, file_list, mem_store, mem_query

STEP 5 — CREATE: tasks/security_task.py
Factory function: create_security_task(security_agent, goal, context=None) -> Task
  Description: Review all generated code for security vulnerabilities. Goal: {{goal}}.
    Use Read Output File to read deliverable.md and deliverable_revised.md.
    Check for: hardcoded secrets/tokens, shell injection (subprocess with shell=True),
    path traversal, unsafe deserialization, eval()/exec() on user input.
    Write security_report.md with VERDICT (SECURITY_BLOCK / SECURITY_PASS_WITH_WARNINGS / SECURITY_PASS)
    and numbered list of findings.
  Expected output: security_report.md written.

STEP 6 — UPDATE: crews/default_crew.py
Read the current file first (Read Project File: 'crews/default_crew.py').
Add imports for qa_agent, security_agent, qa_task, security_task.
Add code_executor tool instantiation.
Add qa_agent and security_agent instantiation after critic (same llm, verbose).
Add qa_task after revise_task (context=[plan_task, revise_task]).
Add security_task after qa_task (context=[plan_task, revise_task]).
Add qa_agent and security_agent to the agents list.
Add qa_task and security_task to the tasks list.
Keep ALL existing code — only add, do not remove anything.

STEP 7 — UPDATE: crews/plc_crew.py
Read it first (Read Project File: 'crews/plc_crew.py').
Apply same pattern: add QA Sentinel and Security Reviewer after the existing
plc_safety_reviewer revise step. Wire them the same way as default_crew.

STEP 8 — UPDATE: crews/react_crew.py
Read it first (Read Project File: 'crews/react_crew.py').
Apply same pattern: add QA Sentinel and Security Reviewer after the existing
ui_reviewer revise step.

After completing all writes, confirm each file was written by listing them.
""".format(root=str(_PROJECT_ROOT))


PHASE_1B_GOAL = """\
PHASE 1B: Create Specialist Agents — Documentation and Memory

PROJECT ROOT: {root}
RULE: Use 'Read Project File' for existing files, 'Write Project File' for new/modified files.
RULE: Follow the factory-function pattern from agents/builder.py exactly.

STEP 1 — READ THESE FILES FIRST:
  agents/builder.py
  agents/researcher.py
  memory/memory_store.py
  tasks/build.py

STEP 2 — CREATE: agents/docs_agent.py
Factory function: create_docs_agent(llm, tools=None, verbose=True) -> Agent
  role="Documentation Writer"
  goal: Read the final revised deliverable and any source files produced during
    the run. Generate structured markdown documentation: README section with
    overview and usage, inline docstring suggestions for any functions/classes,
    API reference for any endpoints, and a quickstart example. Write all output
    to 'outputs/docs/deliverable_docs.md'. Never summarize — produce complete docs.
  backstory: Technical writer and developer with 10 years of experience producing
    clear, complete API documentation and README files for open-source projects.
    You read source files first and document what actually exists, not assumptions.
  allow_delegation=False, max_iter=8
  Tools needed: file_read, file_write, file_list, cb_read (CodebaseReadTool if available,
    otherwise file_read), mem_store, mem_query

STEP 3 — CREATE: tasks/docs_task.py
Factory function: create_docs_task(docs_agent, goal, context=None) -> Task
  Description: Generate complete documentation for the deliverable. Goal: {{goal}}.
    Read deliverable_revised.md using Read Output File.
    Produce: section headers, description, installation/usage, examples, and
    any API endpoint documentation. Save to filepath='docs/deliverable_docs.md'
    (the tool will scope this under outputs/).
  Expected output: outputs/docs/deliverable_docs.md written.

STEP 4 — CREATE: agents/memory_agent.py
Factory function: create_memory_agent(llm, tools=None, verbose=True) -> Agent
  role="Memory Manager"
  goal: After each crew run, consolidate key findings into structured persistent memory.
    Read research.md and deliverable_revised.md. Extract: (1) key technical decisions
    made (topic='decisions'), (2) research findings worth keeping (topic='research'),
    (3) patterns used in the deliverable (topic='patterns'). Store each using
    Store Memory tool. Also check Query Memory for duplicates before storing.
    Write a brief memory_summary.md report listing what was stored.
  backstory: Knowledge management specialist. You distill lengthy run outputs into
    reusable memory entries tagged by topic. Future crews retrieve your memories
    and avoid redoing work. You never store vague summaries — only specific,
    actionable facts.
  allow_delegation=False, max_iter=6
  Tools needed: file_read, file_list, mem_store, mem_query, file_write

STEP 5 — CREATE: tasks/memory_task.py
Factory function: create_memory_task(memory_agent, goal, context=None) -> Task
  Description: Consolidate this crew run into persistent memory. Goal: {{goal}}.
    Read research.md and deliverable_revised.md using Read Output File.
    Store three memory entries covering decisions, research findings, and patterns.
    Write memory_summary.md listing what was stored with topic labels.
  Expected output: Three memory entries stored. memory_summary.md written.

STEP 6 — CREATE: memory/compartments.py
This module extends ChromaDB memory into 6 MIRIX-style compartments.
Pattern: follow memory/memory_store.py exactly.

Implement:
  _COMPARTMENTS = ["core", "episodic", "semantic", "procedural", "resource", "knowledge_vault"]

  class CompartmentStoreTool(BaseTool):
    name="Store Compartment Memory"
    inputs: content, topic, compartment (one of _COMPARTMENTS, default "episodic")
    Stores to ChromaDB collection named f"smith_{{compartment}}"
    Returns: stored entry ID

  class CompartmentQueryTool(BaseTool):
    name="Query Compartment Memory"
    inputs: query, compartment (or "all" to search all compartments), n_results=5
    If compartment == "all": queries all 6 collections, returns top n_results overall
    Otherwise: queries specific compartment collection

  def create_compartment_tools(config) -> tuple[CompartmentStoreTool, CompartmentQueryTool]:
    Same pattern as create_memory_tools() in memory_store.py

After all writes confirm them.
""".format(root=str(_PROJECT_ROOT))


PHASE_1C_GOAL = """\
PHASE 1C: Create Operations Agents — Deployment and Observability

PROJECT ROOT: {root}
RULE: Read before writing. Use 'Read Project File' and 'Write Project File'.
RULE: Follow the factory-function agent pattern from agents/builder.py.

STEP 1 — READ FIRST:
  agents/critic.py
  agents/plc_safety_reviewer.py
  tasks/critique.py
  tools/code_executor.py

STEP 2 — CREATE: agents/deploy_agent.py
Factory function: create_deploy_agent(llm, tools=None, verbose=True) -> Agent
  role="Deployment Validator"
  goal: Validate that generated code artifacts are deployment-ready.
    For Python code: attempt to compile (py_compile) every .py snippet in the deliverable
    using Execute Python Code tool. For React code: check that JSX syntax is valid and
    imports are resolvable by running a syntax check. Check for missing requirements,
    undeclared variables, and broken import chains. Write deploy_report.md with
    DEPLOY_READY or DEPLOY_BLOCKED verdict and numbered list of issues.
  backstory: DevOps engineer and build systems specialist. You validate that code
    artifacts can actually be deployed. You run compile checks, static analysis,
    and import validation before anything ships. You block deployment on import errors,
    syntax errors, and missing dependencies.
  allow_delegation=False, max_iter=8
  Tools needed: file_read, file_write, file_list, code_executor, mem_store, mem_query

STEP 3 — CREATE: tasks/deploy_task.py
Factory function: create_deploy_task(deploy_agent, goal, context=None) -> Task
  Description: Validate deployment readiness for goal: {{goal}}.
    Read deliverable_revised.md using Read Output File.
    For each Python code block: extract it and run via Execute Python Code with
    a py_compile check. Write deploy_report.md with DEPLOY_READY or DEPLOY_BLOCKED
    and list of any blocking issues.
  Expected output: deploy_report.md written with verdict.

STEP 4 — CREATE: agents/observability_agent.py
Factory function: create_observability_agent(llm, tools=None, verbose=True) -> Agent
  role="Observability Monitor"
  goal: After a crew run completes, analyze the run's audit trail.
    Read all output files (research.md, deliverable.md, critique.md,
    deliverable_revised.md, qa_report.md if present, security_report.md if present).
    Produce a telemetry_report.md in outputs/ containing:
      - Agents that ran and approximate iterations used
      - Files produced
      - Any SENTINEL_BLOCK, SECURITY_BLOCK, or DEPLOY_BLOCKED verdicts
      - Recommendations for improving the next run
    This report is for developer review, not agent routing.
  backstory: Platform engineer and observability specialist. You read agent outputs
    and reconstruct what happened during a run. You flag anomalies, repeated failures,
    and missing outputs. Your reports help developers tune agent behavior.
  allow_delegation=False, max_iter=5
  Tools needed: file_read, file_list, file_write, mem_query

STEP 5 — CREATE: tasks/observability_task.py
Factory function: create_observability_task(observability_agent, goal, context=None) -> Task
  Description: Generate a run telemetry report. Goal: {{goal}}.
    Use List Output Files to enumerate all outputs/ files.
    Read each one that exists: research.md, deliverable.md, critique.md,
    deliverable_revised.md, qa_report.md, security_report.md, deploy_report.md.
    Write telemetry_report.md summarizing what ran, what verdicts were issued,
    and what to improve.
  Expected output: outputs/telemetry_report.md written.

After all writes, confirm each file exists.
""".format(root=str(_PROJECT_ROOT))


PHASE_1D_GOAL = """\
PHASE 1D: Create Infrastructure Modules — Checkpointing, Scratchpad, Per-Agent Routing

PROJECT ROOT: {root}
RULE: Read before writing. Use 'Read Project File' and 'Write Project File'.
RULE: Follow patterns from memory/memory_store.py and tools/file_tools.py exactly.

STEP 1 — READ FIRST:
  memory/memory_store.py
  tools/file_tools.py
  config/config.yaml
  crews/default_crew.py

STEP 2 — CREATE: memory/checkpoints.py
Purpose: Save and resume crew task state. Each task writes its output to a checkpoint
file so that if the run is interrupted, it can resume from the last completed task.

Implement:
  import json, uuid
  from pathlib import Path

  _CHECKPOINTS_DIR = Path(__file__).resolve().parent.parent / "outputs" / "checkpoints"

  class CheckpointManager:
    def __init__(self, run_id: str | None = None):
      self.run_id = run_id or str(uuid.uuid4())[:8]
      self.run_dir = _CHECKPOINTS_DIR / self.run_id
      self.run_dir.mkdir(parents=True, exist_ok=True)

    def save(self, task_name: str, output: str) -> str:
      path = self.run_dir / f"{{task_name}}.json"
      path.write_text(json.dumps({{"task": task_name, "output": output}}, indent=2))
      return str(path)

    def load(self, task_name: str) -> str | None:
      path = self.run_dir / f"{{task_name}}.json"
      if path.exists():
        return json.loads(path.read_text())["output"]
      return None

    def completed_tasks(self) -> list[str]:
      return [p.stem for p in sorted(self.run_dir.glob("*.json"))]

    def clear(self) -> None:
      for f in self.run_dir.glob("*.json"):
        f.unlink()

  # Module-level default instance (one per process)
  _default_manager: CheckpointManager | None = None

  def get_checkpoint_manager(run_id: str | None = None) -> CheckpointManager:
    global _default_manager
    if _default_manager is None:
      _default_manager = CheckpointManager(run_id)
    return _default_manager

STEP 3 — CREATE: memory/scratchpad.py
Purpose: Shared blackboard/scratchpad that all agents in a crew can read and write.
Each agent appends its section to the shared context. Other agents read it before acting.

Implement:
  import json, threading
  from pathlib import Path

  _SCRATCH_DIR = Path(__file__).resolve().parent.parent / "outputs" / "checkpoints"

  class Scratchpad:
    def __init__(self, run_id: str):
      _SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
      self._path = _SCRATCH_DIR / f"scratchpad_{{run_id}}.json"
      self._lock = threading.Lock()
      if not self._path.exists():
        self._path.write_text(json.dumps({{}}, indent=2))

    def write(self, agent_name: str, section: str, content: str) -> None:
      with self._lock:
        data = json.loads(self._path.read_text())
        if agent_name not in data:
          data[agent_name] = {{}}
        data[agent_name][section] = content
        self._path.write_text(json.dumps(data, indent=2))

    def read(self, agent_name: str | None = None) -> dict:
      with self._lock:
        data = json.loads(self._path.read_text())
        return data.get(agent_name, {{}}) if agent_name else data

    def read_all_as_text(self) -> str:
      data = self.read()
      lines = ["=== SHARED SCRATCHPAD ==="]
      for agent, sections in data.items():
        lines.append(f"\\n[{{agent}}]")
        for section, content in sections.items():
          lines.append(f"  {{section}}: {{content[:500]}}")
      return "\\n".join(lines)

    def clear(self) -> None:
      self._path.write_text(json.dumps({{}}, indent=2))

  _scratchpads: dict[str, Scratchpad] = {{}}

  def get_scratchpad(run_id: str) -> Scratchpad:
    if run_id not in _scratchpads:
      _scratchpads[run_id] = Scratchpad(run_id)
    return _scratchpads[run_id]

STEP 4 — UPDATE: config/config.yaml
Read the current file first (Read Project File: 'config/config.yaml').
Add a new section after crew_models:

agent_models:
  orchestrator: qwen2.5:32b      # planning requires full reasoning
  researcher:   qwen2.5:32b      # synthesis across large context
  builder:      qwen2.5-coder:14b  # code generation
  critic:       qwen2.5:14b      # pattern recognition
  qa_agent:     llama3.1:8b      # pass/fail output, low reasoning needed
  security_agent: qwen2.5:14b   # pattern matching for vulns
  docs_agent:   llama3.1:8b      # template filling, low reasoning
  memory_agent: llama3.1:8b      # classification task
  deploy_agent: qwen2.5:14b      # compile checking
  observability_agent: llama3.1:8b  # report aggregation

STEP 5 — UPDATE: config/loader.py
Read current file (Read Project File: 'config/loader.py').
Add function:
  def get_agent_model(config: dict, agent_name: str) -> str:
    \"\"\"Return the model assigned to a specific agent, falling back to crew default or fallback.\"\"\"
    agent_models = config.get("agent_models", {{}})
    if agent_name in agent_models:
      return agent_models[agent_name]
    return config.get("llm_fallback", {{}}).get("model", "llama3.1:8b")

Keep ALL existing code in loader.py — only add this new function.

After all writes, confirm them.
""".format(root=str(_PROJECT_ROOT))


PHASE_1E_GOAL = """\
PHASE 1E: Integration — Wire All New Agents Into All Three Crews, Update Orchestrator and README

PROJECT ROOT: {root}
RULE: Read every file before modifying it.
RULE: Preserve ALL existing code — only add new imports, tool inits, agent inits, tasks, and list entries.
RULE: Follow the EXACT same code style as the existing file.

STEP 1 — READ ALL THESE FILES FIRST:
  agents/orchestrator.py
  agents/docs_agent.py
  agents/memory_agent.py
  agents/deploy_agent.py
  agents/observability_agent.py
  agents/qa_agent.py
  agents/security_agent.py
  tasks/docs_task.py
  tasks/memory_task.py
  tasks/deploy_task.py
  tasks/observability_task.py
  tasks/qa_task.py
  tasks/security_task.py
  crews/default_crew.py
  crews/plc_crew.py
  crews/react_crew.py
  config/loader.py
  README.md

STEP 2 — IMPLEMENT REFLEXION LOOP IN: crews/default_crew.py
Read it first. After the existing critique_task and revise_task:
  - Check if critique_task output contains "APPROVED"
  - If not APPROVED (i.e., NEEDS REVISION), run revise_task again (up to 2 more times = 3 total)
  - This is done by checking a loop count in a wrapper, not by modifying the LLM prompt
  - Implement as a Python loop BEFORE Crew() creation:
      approved = False
      loop_count = 0
      max_loops = 3
      tasks = [plan_task, research_task, build_task, critique_task]
      # ... reflexion is handled by the Crew sequential process with
      # the critique task providing context to revise_task
      # Simply add revise_task2 = create_revise_task(builder, approved_goal, context=[plan_task, build_task, critique_task])
      # and revise_task3 = create_revise_task(builder, approved_goal, context=[plan_task, build_task, critique_task])
      # Then a second critique_task2 = create_critique_task(critic, approved_goal, context=[plan_task, revise_task2])
      # The full task chain becomes: plan → research → build → critique → revise → critique2 → revise2 → qa → security → docs → memory → observability
  - DO NOT break existing functionality

STEP 3 — UPDATE: agents/orchestrator.py
Read it first. In the goal and backstory, add recognition of the new roles:
  "QA Sentinel, Security Reviewer, Documentation Writer, Memory Manager,
   Deployment Validator, and Observability Monitor agents are available
   for QA validation, security review, documentation, memory management,
   deployment readiness checking, and run telemetry respectively."
Keep all existing text.

STEP 4 — COMPLETE: crews/default_crew.py
After the reflexion loop, add full integration of ALL new agents:
  - Import from agents/docs_agent.py, agents/memory_agent.py, agents/deploy_agent.py,
    agents/observability_agent.py (qa and security already added in Phase 1A)
  - Import tasks for all new agents
  - Import get_agent_model from config/loader.py
  - Create per-agent LLM instances using get_agent_model():
      llm_qa = LLM(model=f"ollama/{{get_agent_model(config, 'qa_agent')}}", ...)
      llm_security = LLM(model=f"ollama/{{get_agent_model(config, 'security_agent')}}", ...)
      (etc. for all new agents)
  - Import CodeExecutorTool from tools/code_executor.py
  - Add all new agents and their tasks to the crew

STEP 5 — COMPLETE: crews/plc_crew.py
Read it. Add QA, Security, and Deploy agents after the safety reviewer revise step.
Use per-agent model routing (get_agent_model).

STEP 6 — COMPLETE: crews/react_crew.py
Read it. Add QA, Security, and Deploy agents after the ui_reviewer revise step.
Use per-agent model routing (get_agent_model).

STEP 7 — UPDATE: README.md
Read it. Find the agent table (if any) or create one under a "## Agent Team" heading.
Replace or add the full expanded team table:

## Agent Team

| Agent | Role | Crew | Model Tier |
|-------|------|------|------------|
| Orchestrator | Plans and decomposes goals | Default | 32B |
| Researcher | Gathers information | Default | 32B |
| Builder | Produces deliverables | Default | 14B-Coder |
| Critic | Reviews output quality | Default | 14B |
| QA Sentinel | Executes code, blocks on failures | All | 8B |
| Security Reviewer | OWASP/vulnerability scanning | All | 14B |
| Documentation Writer | Generates structured docs | Default | 8B |
| Memory Manager | Consolidates run knowledge | Default | 8B |
| Deployment Validator | Compile and deploy checks | All | 14B |
| Observability Monitor | Run telemetry and audit | Default | 8B |
| PLC Planner | PLC program structure | PLC | 14B |
| PLC Developer | Ladder logic / AOI code | PLC | 14B-Coder |
| PLC Safety Reviewer | NFPA/IEC safety compliance | PLC | 14B |
| UI Planner | React component design | React | 14B |
| UI Builder | React/MUI component code | React | 14B-Coder |
| UI Reviewer | React code quality review | React | 14B |

STEP 8 — GIT COMMIT
After all files are written and confirmed:
  1. Use Git Status to verify there are staged/unstaged changes
  2. Use Git Stage Files with paths='.' to stage everything
  3. Use Git Commit with message:
     "Phase 1: expand agent team with QA, security, docs, memory, deploy, observability"
  4. Use Git Push to push to origin

Confirm each file was written before the commit.
""".format(root=str(_PROJECT_ROOT))


# ── Crew Runner ───────────────────────────────────────────────────────────────

def build_expansion_crew(phase_goal: str, config: dict) -> Crew:
    """Build a crew with full project-write access for expansion tasks."""
    llm_cfg = config["llm"]
    base_url = llm_cfg.get("base_url", "http://localhost:11434")
    verbose = config["crew"].get("verbose", True)

    # All agents use qwen2.5-coder:14b — fits fully in VRAM, 10-20x faster
    # than 32b which only places 7GB in VRAM and runs the rest from RAM.
    llm_plan = LLM(
        model="ollama/qwen2.5-coder:14b",
        base_url=base_url,
        temperature=0.3,
        timeout=600,
    )
    llm_code = LLM(
        model="ollama/qwen2.5-coder:14b",
        base_url=base_url,
        temperature=0.2,
        timeout=600,
    )
    llm_review = LLM(
        model="ollama/qwen2.5:14b",
        base_url=base_url,
        temperature=0.2,
        timeout=600,
    )

    # ── Tool set (all tools including project write) ──────────────────────────
    file_read   = FileReadTool()
    file_write  = FileWriteTool()
    file_list   = FileListTool()
    web_search  = WebSearchTool()
    web_fetch   = WebFetchTool()
    proj_write  = ProjectFileWriteTool()
    proj_read   = ProjectFileReadTool()
    proj_list   = ProjectListTool()
    git_status  = GitStatusTool(repo_path=str(_PROJECT_ROOT))
    git_stage   = GitStageTool(repo_path=str(_PROJECT_ROOT))
    git_commit  = GitCommitTool(repo_path=str(_PROJECT_ROOT))
    git_push    = GitPushTool(repo_path=str(_PROJECT_ROOT))
    mem_store, mem_query = create_memory_tools(config)

    # ── Agents ────────────────────────────────────────────────────────────────
    orchestrator = create_orchestrator(
        llm=llm_plan,
        tools=[proj_list, proj_read, file_list, mem_query],
        verbose=verbose,
    )
    researcher = create_researcher(
        llm=llm_code,
        tools=[proj_read, proj_list, web_search, web_fetch,
               file_write, file_list, mem_store, mem_query],
        verbose=verbose,
    )
    builder = create_builder(
        llm=llm_code,
        tools=[proj_write, proj_read, proj_list,
               file_read, file_write, file_list,
               mem_store, mem_query],
        verbose=verbose,
    )
    critic = create_critic(
        llm=llm_review,
        tools=[proj_read, proj_list, file_read, file_write, file_list,
               git_status, git_stage, git_commit, git_push, mem_query],
        verbose=verbose,
    )

    # ── Tasks ─────────────────────────────────────────────────────────────────
    plan_task = Task(
        description=(
            f"Analyze the expansion task and create a detailed step-by-step plan.\n\n"
            f"EXPANSION TASK:\n{phase_goal}\n\n"
            "Your plan must list:\n"
            "1. Every file to read (which existing files to study first)\n"
            "2. Every file to create (exact filepath and purpose)\n"
            "3. Every file to modify (exact filepath and what to change)\n"
            "4. The order to do everything\n"
            "5. How to verify success\n\n"
            "Use List Project Directory and Read Project File tools to examine "
            "the existing code structure before finalizing the plan."
        ),
        expected_output=(
            "A numbered execution plan listing files to read, files to create, "
            "files to modify, and how to verify each step."
        ),
        agent=orchestrator,
    )

    research_task = Task(
        description=(
            "Read all existing project source files listed in the plan to understand "
            "the code patterns. Do NOT use web search for this task — read the actual "
            "project files using Read Project File.\n\n"
            "Read AT MINIMUM:\n"
            "  agents/builder.py, agents/critic.py, agents/orchestrator.py\n"
            "  crews/default_crew.py, crews/plc_crew.py, crews/react_crew.py\n"
            "  tasks/build.py, tasks/critique.py, tasks/revise.py\n"
            "  memory/memory_store.py, tools/file_tools.py, config/config.yaml\n\n"
            "Summarize the patterns you find:\n"
            "- Agent factory function signature\n"
            "- Task factory function signature\n"
            "- Crew builder structure\n"
            "- Import style\n"
            "- Docstring style\n\n"
            "Save your summary to research.md using Write Output File."
        ),
        expected_output=(
            "research.md written with code pattern summary from all existing files."
        ),
        agent=researcher,
        context=[plan_task],
    )

    build_task = Task(
        description=(
            f"Execute the expansion plan. Create ALL files specified in the plan "
            f"following the patterns documented in research.md.\n\n"
            f"FULL SPECIFICATION:\n{phase_goal}\n\n"
            "RULES:\n"
            "1. Read research.md FIRST using Read Output File to recall all patterns.\n"
            "2. For each file to create: use Write Project File with the exact filepath.\n"
            "3. For each file to modify: use Read Project File first, then Write Project File "
            "   with the complete updated content (not a diff — the full file).\n"
            "4. After writing each file, immediately use Read Project File to verify it exists.\n"
            "5. Do NOT skip any file from the specification.\n"
            "6. Do NOT write placeholder code — every file must be complete and importable.\n\n"
            "Write a build_log.md to outputs/ listing every file you wrote with its path and status."
        ),
        expected_output=(
            "All specified files created/modified. build_log.md written listing every file."
        ),
        agent=builder,
        context=[plan_task, research_task],
    )

    critique_task = Task(
        description=(
            "Verify all created files exist and are complete.\n\n"
            "For each file the Builder was supposed to create:\n"
            "1. Use Read Project File to read it.\n"
            "2. Check: does it have the correct factory function name and signature?\n"
            "3. Check: are all imports at the top?\n"
            "4. Check: does it follow the same pattern as existing files?\n"
            "5. If modifying an existing crew file: does it still contain ALL original code?\n\n"
            "Read build_log.md from outputs/ to see what the Builder claims to have written.\n\n"
            "Issue verdict:\n"
            "  APPROVED — all files present and correct\n"
            "  NEEDS REVISION — list exact files with exact issues\n\n"
            "Write your critique to critique.md."
        ),
        expected_output=(
            "critique.md written with APPROVED or NEEDS REVISION plus specific issues."
        ),
        agent=critic,
        context=[plan_task, build_task],
    )

    revise_task = Task(
        description=(
            "Fix any issues identified in the critique.\n\n"
            "Read critique.md using Read Output File.\n"
            "For each NEEDS REVISION item:\n"
            "  - Read the file that has the issue using Read Project File\n"
            "  - Fix the specific issue\n"
            "  - Write the complete corrected file using Write Project File\n\n"
            "If verdict was APPROVED, confirm and proceed to commit.\n\n"
            "After all fixes: use Git Status, Git Stage Files with paths='.', "
            "Git Commit with message from the phase specification, then Git Push."
        ),
        expected_output=(
            "All issues fixed. Git commit and push completed."
        ),
        agent=builder,
        context=[plan_task, build_task, critique_task],
    )

    return Crew(
        agents=[orchestrator, researcher, builder, critic],
        tasks=[plan_task, research_task, build_task, critique_task, revise_task],
        process=Process.sequential,
        verbose=verbose,
        max_rpm=config["crew"].get("max_rpm", 10),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

PHASES = {
    "1a": PHASE_1A_GOAL,
    "1b": PHASE_1B_GOAL,
    "1c": PHASE_1C_GOAL,
    "1d": PHASE_1D_GOAL,
    "1e": PHASE_1E_GOAL,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Smith_Agentic Phase 1 expansion crew."
    )
    parser.add_argument(
        "--phase",
        default="1a",
        choices=list(PHASES.keys()),
        help="Which Phase 1 sub-task to run (default: 1a)",
    )
    args = parser.parse_args()

    config = load_config()
    config["crew"]["hitl"] = False
    config["crew"]["verbose"] = True

    goal = PHASES[args.phase]
    print(f"\n{'='*60}")
    print(f"  Smith_Agentic Phase {args.phase.upper()} Expansion")
    print(f"{'='*60}\n")
    print(f"Running phase {args.phase}...")

    crew = build_expansion_crew(goal, config)
    result = crew.kickoff()

    print(f"\n{'='*60}")
    print(f"  Phase {args.phase.upper()} Complete")
    print(f"{'='*60}")
    print(result)
    print(f"\nCheck outputs/ for build_log.md and critique.md.")


if __name__ == "__main__":
    main()
