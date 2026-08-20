"""Critic agent implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """Reviews final answer for hallucinations, citation support, and reasoning quality."""

    name = "critic"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Review `state.final_answer` against `state.sources`."""
        final_answer = state.final_answer or ""
        sources_summary = "\n".join(f"- {s.title}: {s.snippet[:200]}" for s in state.sources)

        system_prompt = (
            "You are a Quality & Verification Critic. "
            "Evaluate whether the final report is strictly grounded in the provided sources, "
            "whether citations are properly attributed, and whether claims are substantiated."
        )

        user_prompt = (
            f"Sources:\n{sources_summary}\n\n"
            f"Final Report to Evaluate:\n{final_answer}\n\n"
            "Provide a concise evaluation:\n"
            "1. Grounding and Factuality Check\n"
            "2. Citation Coverage and Accuracy\n"
            "3. Any unsupported generalizations or recommended adjustments"
        )

        response = self.llm_client.complete(system_prompt, user_prompt)

        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event("critic_completed", {"review_length": len(response.content)})

        return state
