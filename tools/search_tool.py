"""
tools/search_tool.py
DuckDuckGo web search — no API key, no account, completely free.
Falls back gracefully if duckduckgo-search is not installed.
"""
from __future__ import annotations

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class _SearchInput(BaseModel):
    query: str = Field(description="Search query string.")
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return (1–20).",
    )


class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = (
        "Search the web using DuckDuckGo. Returns titles, URLs, and text snippets. "
        "Use this to research topics, find documentation, look up examples, "
        "or verify current information. No API key required."
    )
    args_schema: Type[BaseModel] = _SearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return (
                    "ddgs is not installed. "
                    "Run: pip install ddgs"
                )

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            return f"Search failed: {e}"

        if not results:
            return f"No results found for query: {query}"

        lines = [f"Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title', '(no title)')}")
            lines.append(f"   URL: {r.get('href', 'N/A')}")
            lines.append(f"   {r.get('body', '').strip()}")
            lines.append("")
        return "\n".join(lines)
