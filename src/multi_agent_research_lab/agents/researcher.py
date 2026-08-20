"""Researcher agent implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(
        self,
        search_client: SearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""
        query = state.request.query
        max_sources = state.request.max_sources

        # 1. Fetch relevant sources
        sources = self.search_client.search(query=query, max_results=max_sources)
        state.sources = sources

        # 2. Prepare context for synthesis
        sources_text = "\n\n".join(
            f"--- Source: {s.title} (URL/ID: {s.url}) ---\n{s.snippet}" for s in sources
        )

        system_prompt = (
            "You are an expert Research Agent in a multi-agent system. "
            "Your task is to review the retrieved evidence and extract key findings, "
            "facts, architectural patterns, and relevant data points. "
            "Always cite the source titles or IDs in your notes."
        )

        user_prompt = (
            f"Research Question: {query}\n\n"
            f"Retrieved Sources:\n{sources_text}\n\n"
            "Provide structured Research Notes containing:\n"
            "1. Executive overview of findings\n"
            "2. Key architectural mechanisms and evidence discovered\n"
            "3. Relevant source citations"
        )

        response = self.llm_client.complete(system_prompt, user_prompt)
        state.research_notes = response.content

        # 3. Record agent output and trace
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=response.content,
                metadata={
                    "source_count": len(sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event("researcher_completed", {"sources_found": len(sources)})

        return state
