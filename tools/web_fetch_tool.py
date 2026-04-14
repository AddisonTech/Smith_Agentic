"""
tools/web_fetch_tool.py
Fetches a URL and returns the full page body as clean plain text,
stripped of HTML tags and truncated to ~3000 tokens (~12,000 chars).

Designed to be used by the Researcher agent after WebSearchTool returns
URLs — fetch the top 2-3 results to get full article content rather than
relying on DuckDuckGo's short snippets.
"""
from __future__ import annotations

import re
from typing import Type

import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ~3000 tokens at ~4 chars/token
_MAX_CHARS = 12_000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Tags that add no readable content
_STRIP_TAGS = {
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "button", "svg", "img", "figure", "figcaption",
    "iframe", "meta", "link", "head",
}


class _FetchInput(BaseModel):
    url: str = Field(description="Full URL to fetch (must start with http:// or https://).")


class WebFetchTool(BaseTool):
    name: str = "Fetch Web Page"
    description: str = (
        "Fetch the full text content of a web page from a URL. "
        "Returns cleaned plain text stripped of HTML, truncated to ~3000 tokens. "
        "Use this after Web Search to read the full content of the top results "
        "rather than relying on short snippets. "
        "Pass one URL at a time."
    )
    args_schema: Type[BaseModel] = _FetchInput

    def _run(self, url: str) -> str:
        # Basic URL sanity check
        if not url.startswith(("http://", "https://")):
            return f"Error: Invalid URL '{url}' — must start with http:// or https://"

        try:
            response = requests.get(url, headers=_HEADERS, timeout=10, allow_redirects=True)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            return f"Error: Request timed out fetching {url}"
        except requests.exceptions.HTTPError as e:
            return f"Error: HTTP {e.response.status_code} fetching {url}"
        except requests.exceptions.RequestException as e:
            return f"Error: Could not fetch {url} — {e}"

        # Only parse HTML/text responses
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return f"Error: Non-HTML content type '{content_type}' at {url} — skipping."

        soup = BeautifulSoup(response.text, "lxml")

        # Remove noisy tags in-place
        for tag in soup.find_all(_STRIP_TAGS):
            tag.decompose()

        # Extract text, collapse whitespace
        raw_text = soup.get_text(separator="\n")
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        cleaned = "\n".join(lines)

        # Collapse runs of blank lines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # Truncate and label
        if len(cleaned) > _MAX_CHARS:
            cleaned = cleaned[:_MAX_CHARS] + "\n\n[... truncated at ~3000 tokens ...]"

        return f"Content from: {url}\n\n{cleaned}"
