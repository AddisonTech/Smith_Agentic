"""
tools/git_tool.py
Git operations via GitPython — stage, commit, push, and status.

The repo_path is set at tool creation time and defaults to the parent
of smith_agentic/ (the Standards-PLC repo root). Agents cannot change the
working repo at runtime.
"""
from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Default repo: three levels up from this file (smith_agentic/tools/ → repo root)
_DEFAULT_REPO = Path(__file__).resolve().parent.parent.parent


class _StatusInput(BaseModel):
    pass


class _StageInput(BaseModel):
    paths: str = Field(
        description=(
            "Comma-separated list of file paths (relative to repo root) to stage. "
            "Use '.' to stage all changes."
        )
    )


class _CommitInput(BaseModel):
    message: str = Field(description="Commit message.")


class _PushInput(BaseModel):
    remote: str = Field(default="origin", description="Remote name (default: origin).")
    branch: str = Field(default="", description="Branch name. Leave empty to use current branch.")


class GitStatusTool(BaseTool):
    name: str = "Git Status"
    description: str = (
        "Show the current git status of the repository — staged, unstaged, and untracked files."
    )
    args_schema: Type[BaseModel] = _StatusInput
    repo_path: str = str(_DEFAULT_REPO)

    def _run(self, **kwargs) -> str:
        try:
            import git
            repo = git.Repo(self.repo_path)
            lines = []
            if repo.is_dirty(untracked_files=True):
                diff_staged = repo.index.diff("HEAD")
                diff_unstaged = repo.index.diff(None)
                untracked = repo.untracked_files
                if diff_staged:
                    lines.append("Staged:")
                    for d in diff_staged:
                        lines.append(f"  M {d.a_path}")
                if diff_unstaged:
                    lines.append("Unstaged:")
                    for d in diff_unstaged:
                        lines.append(f"  M {d.a_path}")
                if untracked:
                    lines.append("Untracked:")
                    for f in untracked:
                        lines.append(f"  ? {f}")
            else:
                lines.append("Working tree clean.")
            branch = repo.active_branch.name
            lines.insert(0, f"Branch: {branch}")
            return "\n".join(lines)
        except ImportError:
            return "GitPython not installed. Run: pip install gitpython"
        except Exception as e:
            return f"[ERROR] {e}"


class GitStageTool(BaseTool):
    name: str = "Git Stage Files"
    description: str = (
        "Stage one or more files for commit. "
        "Provide comma-separated paths relative to the repo root, or '.' for all changes."
    )
    args_schema: Type[BaseModel] = _StageInput
    repo_path: str = str(_DEFAULT_REPO)

    def _run(self, paths: str) -> str:
        try:
            import git
            repo = git.Repo(self.repo_path)
            path_list = [p.strip() for p in paths.split(",") if p.strip()]
            repo.index.add(path_list)
            staged = [d.a_path for d in repo.index.diff("HEAD")]
            return f"Staged {len(path_list)} path(s). Currently staged: {staged}"
        except ImportError:
            return "GitPython not installed. Run: pip install gitpython"
        except Exception as e:
            return f"[ERROR] {e}"


class GitCommitTool(BaseTool):
    name: str = "Git Commit"
    description: str = (
        "Create a commit with all currently staged changes. "
        "Stage files first using the Git Stage Files tool."
    )
    args_schema: Type[BaseModel] = _CommitInput
    repo_path: str = str(_DEFAULT_REPO)

    def _run(self, message: str) -> str:
        try:
            import git
            repo = git.Repo(self.repo_path)
            if not repo.index.diff("HEAD") and not repo.index.diff(None):
                return "Nothing staged to commit."
            commit = repo.index.commit(message)
            return f"Committed: {commit.hexsha[:8]} — {message}"
        except ImportError:
            return "GitPython not installed. Run: pip install gitpython"
        except Exception as e:
            return f"[ERROR] {e}"


class GitPushTool(BaseTool):
    name: str = "Git Push"
    description: str = (
        "Push committed changes to a remote. "
        "Defaults to origin and the current branch."
    )
    args_schema: Type[BaseModel] = _PushInput
    repo_path: str = str(_DEFAULT_REPO)

    def _run(self, remote: str = "origin", branch: str = "") -> str:
        try:
            import git
            repo = git.Repo(self.repo_path)
            target_branch = branch or repo.active_branch.name
            origin = repo.remote(remote)
            push_info = origin.push(refspec=f"refs/heads/{target_branch}")
            flags = push_info[0].flags if push_info else 0
            if flags & git.remote.PushInfo.ERROR:
                return f"[ERROR] Push failed. Flags: {flags}"
            return f"Pushed to {remote}/{target_branch} successfully."
        except ImportError:
            return "GitPython not installed. Run: pip install gitpython"
        except Exception as e:
            return f"[ERROR] {e}"
