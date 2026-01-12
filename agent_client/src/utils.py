from agents.mcp import ToolFilterContext
from .states import AVAILABLE_STATES

def context_aware_filter(context: ToolFilterContext, tool) -> bool:
    """
    Enforces deterministic tool access based on agent type and current state.
    
    This filter ensures that agents can only access tools that are explicitly
    allowed for their current state, preventing unauthorized tool usage.
    
    Args:
        context (ToolFilterContext): The context containing the agent information,
            including the agent name in format "AgentType/state_key".
        tool: The tool object being checked, must have a 'name' attribute.
    
    Returns:
        bool: True if the tool is allowed for the current agent/state combination,
              False otherwise.
    
    Examples:
        - QuestionAgent/self_evaluation -> uses allowed_tools_question from state
        - VerificationAgent/evaluate_teammate_grade -> uses allowed_tools_verification from state
    """
    agent_name = context.agent.name  # e.g. "VerificationAgent/evaluate_teammate_grade"
    try:
        agent_type, state_key = agent_name.split("/", 1)
    except ValueError:
        return False

    state = AVAILABLE_STATES.get(state_key)
    if not state:
        return False

    allowed = state.allowed_tools_verification if agent_type == "VerificationAgent" else state.allowed_tools_question
    return tool.name in allowed
