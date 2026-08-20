"""Unit tests for agents and supervisor routing policy."""

from unittest.mock import MagicMock

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMResponse


def test_supervisor_routing_policy() -> None:
    supervisor = SupervisorAgent()
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent architectures"))

    # Initial state -> needs researcher
    state = supervisor.run(state)
    assert state.route_history[-1] == "researcher"

    # With sources & notes -> needs analyst
    state.sources = [SourceDocument(title="Doc 1", snippet="Snippet 1")]
    state.research_notes = "Found evidence."
    state = supervisor.run(state)
    assert state.route_history[-1] == "analyst"

    # With analysis notes -> needs writer
    state.analysis_notes = "Analyzed trade-offs."
    state = supervisor.run(state)
    assert state.route_history[-1] == "writer"

    # With final answer -> done
    state.final_answer = "Final synthesized report."
    state = supervisor.run(state)
    assert state.route_history[-1] == "done"


def test_supervisor_max_iterations_guardrail() -> None:
    supervisor = SupervisorAgent()
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent architectures"))
    state.iteration = 10  # exceeds max_iterations (default 6)

    state = supervisor.run(state)
    assert state.route_history[-1] == "done"


def test_researcher_agent_with_mock() -> None:
    mock_search = MagicMock()
    mock_search.search.return_value = [SourceDocument(title="Doc A", snippet="Snippet A")]
    mock_llm = MagicMock()
    mock_llm.complete.return_value = LLMResponse(content="Mocked research notes")

    agent = ResearcherAgent(search_client=mock_search, llm_client=mock_llm)
    state = ResearchState(request=ResearchQuery(query="Test query"))
    state = agent.run(state)

    assert len(state.sources) == 1
    assert state.research_notes == "Mocked research notes"
    assert len(state.agent_results) == 1


def test_analyst_and_writer_agents_with_mock() -> None:
    mock_llm = MagicMock()
    mock_llm.complete.return_value = LLMResponse(content="Mocked response")

    analyst = AnalystAgent(llm_client=mock_llm)
    writer = WriterAgent(llm_client=mock_llm)

    state = ResearchState(request=ResearchQuery(query="Test query"))
    state.sources = [SourceDocument(title="Doc A", snippet="Snippet A")]
    state.research_notes = "Initial notes"

    state = analyst.run(state)
    assert state.analysis_notes == "Mocked response"

    state = writer.run(state)
    assert state.final_answer == "Mocked response"
