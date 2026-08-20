"""Analyst agent implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights and trade-off evaluations."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""
        query = state.request.query
        research_notes = state.research_notes or "No research notes provided."

        sources_summary = "\n".join(f"- {s.title}: {s.snippet[:200]}..." for s in state.sources)

        system_prompt = (
            "You are a Senior Research Systems Analyst. "
            "Your role is to critically analyze research findings, evaluate key tensions "
            "(e.g., specialization vs coordination overhead, cost vs quality), "
            "assess evidence strength, and identify failure modes or boundary conditions."
        )

        user_prompt = (
            f"Original Query: {query}\n\n"
            f"Available Sources:\n{sources_summary}\n\n"
            f"Researcher Notes:\n{research_notes}\n\n"
            "Produce comprehensive Analysis Notes covering:\n"
            "1. Critical Analysis & Comparison of Architectures / Approaches\n"
            "2. Trade-offs (Latency, Cost, Accuracy, Coordination Complexity)\n"
            "3. Evidence Quality Assessment (Strong vs Weak/Synthetic evidence)\n"
            "4. Boundary conditions: When to use which architecture."
        )

        response = self.llm_client.complete(system_prompt, user_prompt)
        state.analysis_notes = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event("analyst_completed", {"analysis_length": len(response.content)})

        return state
