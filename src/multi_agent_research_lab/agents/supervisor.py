"""Supervisor / router implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self) -> None:
        self.settings = get_settings()

    def determine_next_route(self, state: ResearchState) -> str:
        """Determine next agent or stop condition based on shared state."""
        # 1. Guardrail: Max iterations check
        if state.iteration >= self.settings.max_iterations:
            logger.info(
                f"Supervisor guardrail triggered: max iterations reached ({state.iteration})"
            )
            return "done"

        # 2. Check missing fields in progression order
        if not state.sources or not state.research_notes:
            return "researcher"
        elif not state.analysis_notes:
            return "analyst"
        elif not state.final_answer:
            return "writer"
        else:
            return "done"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route."""
        next_route = self.determine_next_route(state)
        state.record_route(next_route)
        state.add_trace_event(
            "supervisor_routed",
            {"iteration": state.iteration, "routed_to": next_route},
        )
        return state
