"""
memory/checkpoints.py
Task checkpoint manager — save and resume crew task state.

Each completed task writes its output to a JSON checkpoint file so that if the
run is interrupted, it can resume from the last completed task rather than
starting over.

Usage:
    from memory.checkpoints import get_checkpoint_manager

    cp = get_checkpoint_manager()          # one per process
    cp.save("plan_task", task_output)      # called after each task completes
    prior = cp.load("plan_task")           # returns None if not yet completed
    done  = cp.completed_tasks()           # list of completed task names
    cp.clear()                             # reset for a fresh run
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

_CHECKPOINTS_DIR = Path(__file__).resolve().parent.parent / "outputs" / "checkpoints"


class CheckpointManager:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.run_dir = _CHECKPOINTS_DIR / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def save(self, task_name: str, output: str) -> str:
        """Persist task output to disk. Returns the checkpoint file path."""
        path = self.run_dir / f"{task_name}.json"
        path.write_text(
            json.dumps({"task": task_name, "output": output}, indent=2),
            encoding="utf-8",
        )
        return str(path)

    def load(self, task_name: str) -> str | None:
        """Return saved output for task_name, or None if not yet checkpointed."""
        path = self.run_dir / f"{task_name}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["output"]
        return None

    def completed_tasks(self) -> list[str]:
        """Return sorted list of task names that have been checkpointed."""
        return [p.stem for p in sorted(self.run_dir.glob("*.json"))]

    def clear(self) -> None:
        """Delete all checkpoints for this run."""
        for f in self.run_dir.glob("*.json"):
            f.unlink()


# ── Module-level default (one manager per process) ────────────────────────────

_default_manager: CheckpointManager | None = None


def get_checkpoint_manager(run_id: str | None = None) -> CheckpointManager:
    """Return the process-level CheckpointManager, creating it on first call."""
    global _default_manager
    if _default_manager is None:
        _default_manager = CheckpointManager(run_id)
    return _default_manager
