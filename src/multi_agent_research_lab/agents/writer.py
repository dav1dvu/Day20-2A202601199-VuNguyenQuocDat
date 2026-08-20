"""Writer agent implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes with citations."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""
        query = state.request.query
        research_notes = state.research_notes or ""
        analysis_notes = state.analysis_notes or ""

        sources_ref = "\n".join(f"- {s.title} ({s.url})" for s in state.sources)

        system_prompt = (
            "You are a Technical Writer synthesizing multi-agent research into a polished, "
            "rigorous report. You must ground your conclusions in the provided research and "
            "analysis notes, incorporate inline citations (e.g. [A01], [autogen], [metagpt]), "
            "and address the target audience clearly."
        )

        user_prompt = (
            f"Research Question: {query}\n"
            f"Target Audience: {state.request.audience}\n\n"
            f"Sources Bibliography:\n{sources_ref}\n\n"
            f"Research Notes:\n{research_notes}\n\n"
            f"Analysis Notes:\n{analysis_notes}\n\n"
            "Write a comprehensive, publication-ready research report with:\n"
            "1. Title & Executive Summary\n"
            "2. Core Architectural Concepts & Mechanisms\n"
            "3. Comparative Analysis & Trade-offs (including Latency, Cost, Quality)\n"
            "4. Practical Engineering Recommendations & Boundary Conditions\n"
            "5. References / Source Citations"
        )

        response = self.llm_client.complete(system_prompt, user_prompt)
        state.final_answer = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event("writer_completed", {"answer_length": len(response.content)})

        return state
