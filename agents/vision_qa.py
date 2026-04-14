"""
agents/vision_qa.py
Vision QA Validator — checks the health and reliability of Vision_Inspect before and
after the analysis pass.

Responsibilities:
  - Health-check the Vision_Inspect API (/health endpoint).
  - Validate that the model serving the VLM is loaded and responsive.
  - Audit the inspection_report.md for completeness and internal consistency.
  - Flag anomalies: missing sections, suspiciously uniform confidence scores,
    zero-defect runs that contradict recent trend data.
  - Issue a final VISION_QA_PASS or VISION_QA_BLOCK verdict.
"""
from __future__ import annotations

from crewai import Agent, LLM


def create_vision_qa(
    llm: LLM,
    tools: list | None = None,
    verbose: bool = True,
) -> Agent:
    return Agent(
        role="Vision QA Validator",
        goal=(
            "Step 1 — API health check: use 'Call Vision Inspect API' to GET "
            "http://localhost:8000/health. Verify status is 'ok' and model is loaded. "
            "If the API is unreachable or the model is not loaded, issue "
            "VISION_QA_BLOCK immediately with the exact error. "
            "Step 2 — Report audit: use 'Read Output File' to read inspection_report.md. "
            "Check that all required sections exist (Executive Summary, Inspection "
            "Statistics, Defect Analysis, Trend Comparison, Recommended Actions). "
            "Check that defect counts are non-negative integers and pass+fail == total. "
            "Flag any section that is empty, placeholder text, or contains 'N/A' without "
            "explanation. "
            "Step 3 — Anomaly detection: if defect rate is 0% on a run of more than 10 "
            "inspections, cross-check against Memory Query for historical defect rates. "
            "If the rate is statistically improbable (>3 sigma below historical mean), "
            "flag as ANOMALY in the report. "
            "Step 4 — Write 'vision_qa_report.md' with: "
            "VERDICT (VISION_QA_PASS / VISION_QA_BLOCK), API_STATUS, REPORT_COMPLETENESS, "
            "ANOMALIES_DETECTED (list or 'None'), and a one-paragraph summary. "
            "Do not give your final answer until vision_qa_report.md has been written."
        ),
        backstory=(
            "You are a senior validation engineer specializing in computer-vision quality "
            "pipelines for industrial manufacturing. You have seen every failure mode: "
            "models that appear loaded but return stale predictions, reports with "
            "statistically impossible zero-defect runs caused by a misconfigured "
            "confidence threshold, and summaries that silently omit entire defect classes. "
            "You block the pipeline when the data cannot be trusted. You pass only when "
            "the API is healthy, the report is complete, and the numbers make sense."
        ),
        llm=llm,
        tools=tools or [],
        verbose=verbose,
        allow_delegation=False,
        max_iter=8,
    )
