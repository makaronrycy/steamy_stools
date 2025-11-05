from agents.mcp import ToolFilterContext
from .states import AVAILABLE_STATES
def context_aware_filter(context: ToolFilterContext, tool) -> bool:
    """Filter tools based on context information."""
    agent_name = context.agent.name
    agent_state = agent_name.split("/")[1]  # Extract base agent name
    print(f"Filtering tool access for Agent: {agent_state}, Tool: {tool.name}")
    return filter_tools(agent_state, tool)

def filter_tools(agent_state,tool) ->bool:
    if agent_state not in AVAILABLE_STATES:
        print(f"Missing Agent name: {agent_state}")
        return False
    if tool.name not in AVAILABLE_STATES[agent_state].allowed_tools:
        print(f"Agent: {agent_state} Access denied to tool: {tool.name}")
        return False
    print(f"Agent: {agent_state} Access granted to tool: {tool.name}")
    return True