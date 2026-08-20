"""Test workflow building and graph compilation."""

from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_workflow_build() -> None:
    workflow = MultiAgentWorkflow()
    compiled = workflow.build()
    assert compiled is not None
