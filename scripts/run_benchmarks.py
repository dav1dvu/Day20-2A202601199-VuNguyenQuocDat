"""Script to run end-to-end benchmark comparison and write reports/benchmark_report.md."""

from pathlib import Path
from multi_agent_research_lab.cli import run_single_agent_baseline
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def run_multi_agent_wrapper(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query, max_sources=5))
    workflow = MultiAgentWorkflow()
    return workflow.run(state)


def main() -> None:
    query = "When does a multi-agent architecture produce better research reports than a single capable agent, after accounting for quality, cost, latency, and coordination failure?"

    print("Running Single-Agent Baseline benchmark...")
    state_baseline, metrics_baseline = run_benchmark(
        run_name="Single-Agent Baseline",
        query=query,
        runner=run_single_agent_baseline,
    )

    print("Running Multi-Agent Workflow benchmark...")
    state_multi, metrics_multi = run_benchmark(
        run_name="Multi-Agent Workflow",
        query=query,
        runner=run_multi_agent_wrapper,
    )

    report_content = render_markdown_report([metrics_baseline, metrics_multi])
    
    # Save to reports/benchmark_report.md
    report_path = Path("reports/benchmark_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Benchmark report generated successfully at {report_path.resolve()}!")
    print(report_content)


if __name__ == "__main__":
    main()
