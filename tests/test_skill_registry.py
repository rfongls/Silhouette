from silhouette_core.agent_loop import Agent

def test_skill_autoload():
    agent = Agent()
    assert 'http_get_json' in agent.tools._tools
