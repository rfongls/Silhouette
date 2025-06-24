# Multi-Agent Scenarios

These examples demonstrate how to work with multiple Silhouette agents.

## Spawn two agents and share memory

```bash
python -c "import agent_controller as ac; a=ac.spawn_agent(); b=ac.spawn_agent(); print(ac.list_agents()); ac.shutdown_agent(a); ac.shutdown_agent(b)"
```

## Fork and merge

```bash
python -c "import agent_controller as ac; a=ac.spawn_agent(); b=ac.fork_agent(a); ac.merge_agents(a, b); ac.shutdown_agent(a); ac.shutdown_agent(b)"
```

Messaging is currently stubbed in `agent_messaging.py` for future expansion.
