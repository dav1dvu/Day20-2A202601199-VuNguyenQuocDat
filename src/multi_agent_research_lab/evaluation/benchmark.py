"""Benchmark framework for single-agent vs multi-agent."""

import re
from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def compute_citation_coverage(state: ResearchState) -> float:
    """Compute percentage of retrieved sources referenced in the final answer."""
    if not state.sources or not state.final_answer:
        return 0.0

    cited_count = 0
    answer_lower = state.final_answer.lower()

    for src in state.sources:
        title_core = src.title.split("] ")[-1].lower() if "] " in src.title else src.title.lower()
        source_id = src.metadata.get("source_id", "").lower()

        # Check if source_id like [A01] or title or url is mentioned in answer
        id_match = source_id and (source_id in answer_lower or f"[{source_id}]" in answer_lower)
        title_match = len(title_core) > 5 and (
            title_core[:25] in answer_lower or title_core in answer_lower
        )
        url_match = bool(src.url and src.url in state.final_answer)

        if id_match or title_match or url_match:
            cited_count += 1

    return min(1.0, cited_count / len(state.sources))


def compute_total_cost(state: ResearchState) -> float:
    """Sum estimated token costs across all agent completions."""
    total_cost = 0.0
    for res in state.agent_results:
        cost = res.metadata.get("cost_usd")
        if cost is not None:
            total_cost += cost
    return total_cost


def estimate_quality_score(state: ResearchState) -> float:
    """Heuristic quality scoring from 0 to 10 based on length, citations, and structure."""
    if not state.final_answer:
        return 0.0

    score = 5.0
    length = len(state.final_answer)

    # Length & depth check
    if length > 1500:
        score += 2.0
    elif length > 800:
        score += 1.0

    # Section structure
    sections = ["Background", "Analysis", "Trade-off", "Recommendation", "Citation", "Executive"]
    matched_sections = sum(1 for s in sections if s.lower() in state.final_answer.lower())
    score += min(2.0, matched_sections * 0.4)

    # Citation presence
    citations = re.findall(r"\[[A-Za-z0-9_-]+\]", state.final_answer)
    if len(citations) >= 3:
        score += 1.0

    return min(10.0, score)


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Execute runner and compute complete benchmark metrics."""
    started = perf_counter()
    failure_rate = 0.0
    error_note = ""

    try:
        state = runner(query)
    except Exception as exc:
        failure_rate = 1.0
        error_note = f"Failed: {exc}"
        state = ResearchState(request={"query": query})
        state.errors.append(str(exc))

    latency = perf_counter() - started
    cost = compute_total_cost(state)
    quality = estimate_quality_score(state)
    citation_coverage = compute_citation_coverage(state)

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=cost if cost > 0 else None,
        quality_score=quality if failure_rate == 0.0 else 0.0,
        citation_coverage=citation_coverage,
        failure_rate=failure_rate,
        notes=error_note or f"Completed in {state.iteration} iterations",
    )
    return state, metrics
