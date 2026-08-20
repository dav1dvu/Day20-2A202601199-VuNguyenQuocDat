"""LangGraph workflow implementation."""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph with LangGraph."""

    def __init__(self) -> None:
        self.supervisor = SupervisorAgent()
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()
        self._compiled_graph: Any = None

    def build(self) -> Any:
        """Create and compile a LangGraph graph."""
        graph = StateGraph(ResearchState)

        def supervisor_node(state: ResearchState) -> ResearchState:
            return self.supervisor.run(state)

        def researcher_node(state: ResearchState) -> ResearchState:
            return self.researcher.run(state)

        def analyst_node(state: ResearchState) -> ResearchState:
            return self.analyst.run(state)

        def writer_node(state: ResearchState) -> ResearchState:
            return self.writer.run(state)

        graph.add_node("supervisor", supervisor_node)
        graph.add_node("researcher", researcher_node)
        graph.add_node("analyst", analyst_node)
        graph.add_node("writer", writer_node)

        def route_condition(state: ResearchState) -> str:
            if not state.route_history:
                return END
            last_route = state.route_history[-1]
            if last_route == "done":
                return END
            return last_route

        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            route_condition,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                END: END,
            },
        )
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")

        self._compiled_graph = graph.compile()
        return self._compiled_graph

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state."""
        if self._compiled_graph is None:
            self.build()

        result = self._compiled_graph.invoke(state)
        if isinstance(result, ResearchState):
            return result
        elif isinstance(result, dict):
            return ResearchState.model_validate(result)
        return state
