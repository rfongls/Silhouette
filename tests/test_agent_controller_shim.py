from silhouette_core.agent_controller import run_agent_loop


def test_agent_controller_shim_imports():
    assert callable(run_agent_loop)
