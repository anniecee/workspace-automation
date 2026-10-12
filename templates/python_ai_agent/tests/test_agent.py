"""Unit tests for Agent."""

from {{package_name}}.agent import Agent


def test_agent_initialization():
    agent = Agent()
    assert agent.name == "{{project_name}}"


def test_agent_run():
    agent = Agent()
    result = agent.run("Test input")
    assert result["status"] == "success"
    assert "Test input" in result["output"]
