# scripts/archive

These scripts were used during initial development and expansion phases of
Smith_Agentic. They are kept here for reference but are not part of the
active codebase.

| File | What it was |
|---|---|
| `run_expansion.py` | One-shot script that generated Phase 1 expansion files (agents, tasks, memory modules) via an inline crew. Superseded by the permanent agent files in `agents/`, `tasks/`, `crews/`. |
| `run_vision_inspect.py` | Bootstrap script that built the Vision_Inspect FastAPI repository from scratch using an inline crew and `VisionInspectWriteTool`. Superseded by `crews/vision_crew.py`. |
| `run_vi_direct.py` | Thin CLI wrapper that called the Vision_Inspect API directly without a crew. Superseded by `VisionInspectAPITool` in `tools/vision_inspect_tool.py`. |

Use `python main.py --crew vision --goal "..."` to run Vision_Inspect analysis
through the standard crew interface.
