"""Command-line entrypoint for the research lab."""

from time import perf_counter
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _parse_query(query: str, max_sources: int = 5) -> ResearchQuery:
    try:
        return ResearchQuery(query=query, max_sources=max_sources)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def run_single_agent_baseline(query: str, max_sources: int = 5) -> ResearchState:
    """Run monolithic single-agent baseline."""
    request = _parse_query(query, max_sources=max_sources)
    state = ResearchState(request=request)

    search_client = SearchClient()
    llm_client = LLMClient()

    # 1. Retrieve sources
    sources = search_client.search(query=query, max_results=max_sources)
    state.sources = sources

    sources_text = "\n\n".join(f"--- Source: {s.title} ({s.url}) ---\n{s.snippet}" for s in sources)

    system_prompt = (
        "You are an all-in-one single agent research assistant. "
        "Your task is to analyze the research query, synthesize the provided evidence, "
        "and produce a comprehensive final research report with inline citations [source_id]."
    )

    user_prompt = (
        f"Research Question: {query}\n\n"
        f"Sources:\n{sources_text}\n\n"
        "Write a complete final report covering background, analysis, trade-offs, and citations."
    )

    started = perf_counter()
    response = llm_client.complete(system_prompt, user_prompt)
    latency = perf_counter() - started

    state.final_answer = response.content
    state.record_route("baseline_single_agent")
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=response.content,
            metadata={
                "latency_seconds": latency,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
    )
    return state


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    max_sources: Annotated[int, typer.Option("--max-sources", "-s", help="Max sources")] = 5,
) -> None:
    """Run a real single-agent baseline research call."""
    _init()
    started = perf_counter()
    state = run_single_agent_baseline(query, max_sources=max_sources)
    duration = perf_counter() - started

    panel_title = "[bold green]Single-Agent Baseline Result[/bold green]"
    console.print(Panel(state.final_answer or "No answer generated.", title=panel_title))
    status_str = (
        f"[bold cyan]Sources Retrieved:[/bold cyan] {len(state.sources)} | "
        f"[bold cyan]Latency:[/bold cyan] {duration:.2f}s"
    )
    console.print(status_str)


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    max_sources: Annotated[int, typer.Option("--max-sources", "-s", help="Max sources")] = 5,
) -> None:
    """Run the multi-agent workflow."""
    _init()
    state = ResearchState(request=_parse_query(query, max_sources=max_sources))
    workflow = MultiAgentWorkflow()

    started = perf_counter()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    duration = perf_counter() - started

    panel_title = "[bold green]Multi-Agent Workflow Result[/bold green]"
    console.print(Panel(result.final_answer or "No final answer generated.", title=panel_title))

    # Print Workflow summary table
    table = Table(title="Execution Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Total Iterations", str(result.iteration))
    table.add_row("Route History", " -> ".join(result.route_history))
    table.add_row("Sources Count", str(len(result.sources)))
    table.add_row("Agent Runs", str(len(result.agent_results)))
    table.add_row("Total Wall-Clock Latency", f"{duration:.2f}s")
    console.print(table)


if __name__ == "__main__":
    app()
