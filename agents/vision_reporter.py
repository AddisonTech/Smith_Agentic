"""
agents/vision_reporter.py
Vision Reporter — synthesizes Vision Analyst findings into a structured, human-readable
inspection report suitable for quality management review.

The Reporter reads vision_findings.md produced by the Analyst, enriches it with
trend context from ChromaDB memory, and writes a final inspection_report.md.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_vision_reporter(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Vision Inspection Reporter",
        goal=(
            "Read 'vision_findings.md' from the output directory using the "
            "'Read Output File' tool. "
            "Query ChromaDB memory for prior inspection trends using the "
            "'Memory Query' tool — look for patterns in defect rates, recurring zones, "
            "and seasonal shifts. "
            "Synthesize findings + trend context into a complete inspection report "
            "structured as: Executive Summary, Inspection Statistics, Defect Analysis, "
            "Trend Comparison (vs. prior runs), and Recommended Actions. "
            "Write the report to 'inspection_report.md' using the 'Write Output File' tool. "
            "Store a summary of key insights in ChromaDB using the 'Memory Store' tool "
            "so future runs can reference this session. "
            "Do not give your final answer until both files have been written."
        ),
        backstory=(
            "You are a quality assurance technical writer with a background in "
            "industrial manufacturing. You specialize in turning machine-vision data "
            "into clear, structured reports that bridge the gap between raw inspection "
            "numbers and management decisions. You write for two audiences simultaneously: "
            "the engineer who needs exact defect counts and zones, and the plant manager "
            "who needs a one-paragraph summary and a short action list. "
            "Your reports are factual, never alarmist, and always include a comparison "
            "to prior runs when data is available."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=8,
    )
