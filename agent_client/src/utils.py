from agents.mcp import ToolFilterContext
from .states import AVAILABLE_STATES

def context_aware_filter(context: ToolFilterContext, tool) -> bool:
    """
    Enforces deterministic tool access:
      - QuestionAgent/<state> -> allowed_tools_question
      - VerificationAgent/<state> -> allowed_tools_verification
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
