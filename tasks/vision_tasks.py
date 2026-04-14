"""
tasks/vision_tasks.py
Task factories for the Vision Crew: Analyst → Reporter → QA Validator.

Each factory follows the same pattern as existing task modules:
  create_<task>(agent, goal, context=[...]) -> Task
"""
from __future__ import annotations

from crewai import Agent, Task


# ── 1. Analysis task ──────────────────────────────────────────────────────────

def create_vision_analysis_task(
    analyst: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Run an inspection analysis pass for this goal:\n\n  GOAL: {goal}\n\n"
            "Step 1: Use 'Call Vision Inspect API' to GET http://localhost:8000/inspections "
            "and retrieve the latest batch of inspection results. "
            "If the endpoint returns paginated data, follow pagination until all records "
            "for the current batch are collected.\n\n"
            "Step 2: Parse each inspection record for the following fields:\n"
            "  - inspection_id\n"
            "  - timestamp\n"
            "  - result (pass/fail)\n"
            "  - defects (list of: type, severity, confidence, zone)\n"
            "  - model_version\n\n"
            "Step 3: Compute summary statistics:\n"
            "  - Total inspections, pass count, fail count, pass rate %\n"
            "  - Defect breakdown by type (counts + % of total fails)\n"
            "  - Defect breakdown by zone (counts)\n"
            "  - High-severity defects (severity >= 'high') — list with IDs\n"
            "  - Model versions seen in this batch\n\n"
            "Step 4: Use 'Write Output File' to save findings to 'vision_findings.md'. "
            "Format as markdown with a summary table and a detailed defects section.\n\n"
            "Do not give your final answer until vision_findings.md has been written."
        ),
        expected_output=(
            "vision_findings.md written via Write Output File. "
            "Contains: inspection statistics, defect breakdown by type and zone, "
            "high-severity defect list, and model version info."
        ),
        agent=analyst,
        context=context or [],
    )


# ── 2. Report task ────────────────────────────────────────────────────────────

def create_vision_report_task(
    reporter: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Produce a complete inspection report for this goal:\n\n  GOAL: {goal}\n\n"
            "Step 1: Use 'Read Output File' with filepath='vision_findings.md' to read "
            "the Analyst's findings.\n\n"
            "Step 2: Use 'Memory Query' to search for prior inspection data — query with "
            "topics like 'defect rate', 'inspection trend', 'zone failures'. "
            "If no prior memory exists, note that this is the first recorded session.\n\n"
            "Step 3: Write 'inspection_report.md' using 'Write Output File' with these "
            "sections:\n"
            "  ## Executive Summary\n"
            "  One paragraph: total run, pass rate, most common defect, any critical flags.\n\n"
            "  ## Inspection Statistics\n"
            "  Table: metric | this run | prior average (if available).\n\n"
            "  ## Defect Analysis\n"
            "  Per-defect-type breakdown with counts, severity distribution, top zones.\n\n"
            "  ## Trend Comparison\n"
            "  Compare this run against ChromaDB memory. If no prior data: state baseline.\n\n"
            "  ## Recommended Actions\n"
            "  Bulleted list of ≤5 actions, prioritized by severity.\n\n"
            "Step 4: Use 'Memory Store' to save a summary of this session with topic tag "
            "'vision_inspection_session'.\n\n"
            "Do not give your final answer until inspection_report.md has been written "
            "and the memory has been stored."
        ),
        expected_output=(
            "inspection_report.md written via Write Output File. "
            "Contains all 5 required sections. Memory stored for future trend analysis."
        ),
        agent=reporter,
        context=context or [],
    )


# ── 3. QA validation task ─────────────────────────────────────────────────────

def create_vision_qa_task(
    qa_agent: Agent,
    goal: str,
    context: list | None = None,
) -> Task:
    return Task(
        description=(
            f"Validate the Vision_Inspect pipeline for this goal:\n\n  GOAL: {goal}\n\n"
            "Step 1 — API health: use 'Call Vision Inspect API' to GET "
            "http://localhost:8000/health. Confirm 'status' == 'ok' and VLM model is "
            "loaded. On failure: record the error and set verdict to VISION_QA_BLOCK.\n\n"
            "Step 2 — Report completeness: use 'Read Output File' to read "
            "inspection_report.md. Verify all 5 sections are present and non-empty: "
            "Executive Summary, Inspection Statistics, Defect Analysis, "
            "Trend Comparison, Recommended Actions.\n\n"
            "Step 3 — Numeric consistency: verify pass_count + fail_count == total. "
            "Verify all confidence scores are in [0.0, 1.0]. "
            "Flag any count that is negative.\n\n"
            "Step 4 — Anomaly check: if defect rate == 0% and total_inspections > 10, "
            "use 'Memory Query' to retrieve historical defect rates. "
            "If the current rate is more than 3 standard deviations below historical mean, "
            "flag as ANOMALY.\n\n"
            "Step 5: Write 'vision_qa_report.md' with:\n"
            "  - VERDICT: VISION_QA_PASS or VISION_QA_BLOCK\n"
            "  - API_STATUS: ok / unreachable / model_not_loaded\n"
            "  - REPORT_COMPLETENESS: pass / fail (list missing sections)\n"
            "  - NUMERIC_CONSISTENCY: pass / fail (list violations)\n"
            "  - ANOMALIES_DETECTED: list of anomalies, or 'None'\n"
            "  - SUMMARY: one paragraph\n\n"
            "Do not give your final answer until vision_qa_report.md has been written."
        ),
        expected_output=(
            "vision_qa_report.md written via Write Output File. "
            "Returns VISION_QA_PASS or VISION_QA_BLOCK with full validation details."
        ),
        agent=qa_agent,
        context=context or [],
    )
