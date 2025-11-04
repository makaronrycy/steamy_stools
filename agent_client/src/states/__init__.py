from pydantic import BaseModel

class State(BaseModel):
    name: str
    description: str
    allowed_tools: list[str]
    tool_instructions: str = ""
    prompt_name: str
    verification_prompt_name: str|None
    question: str
    next_state: str

AVAILABLE_STATES = {
    "initial": State(
        name="initial",
        description="The initial state of the agent workflow.",
        allowed_tools=[],
        prompt_name="initial_prompt",
        verification_prompt_name="initial_verification_prompt",
        question="Pytanie o imię i nazwisko użytkownika.",
        next_state="self_evaluation"
    ),
    "self_evaluation": State(
        name="self_evaluation",
        description="Asks the user to evaluate themselves.",
        allowed_tools=[],
        prompt_name="question_prompt",
        verification_prompt_name="self_evaluation_verification_prompt",
        question="Jak oceniasz swój wkład w projekcie i jakie były twoje zadania",
        next_state="evaluate_project_grade"
    ),
    "evaluate_teammate_grade":State(
        name="evaluate_teammate_grade",
        description="Asks the user to evaluate a teammate's grade.",
        allowed_tools=["get_ungraded_members_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="teamate_evaluation_verification_prompt",
        tool_instructions="Jeśli pytanie jest o członka zespołu, wylosuj nieocenionego członka zespołu używając get_ungraded_members_tool.",
        question="Jaką ocenę wystawiłbyś swojemu koledze z zespołu i dlaczego?",
        next_state="evaluate_project_grade"
    ),
    "evaluate_leader_grade":State(
        name="evaluate_leader_grade",
        description="Asks the user to evaluate the leader's grade.",
        allowed_tools=["get"],
        prompt_name="question_prompt",
        verification_prompt_name="leader_evaluation_verification_prompt",
        question="Jaką ocenę wystawiłbyś swojemu liderowi i dlaczego?",
        next_state="evaluate_project_grade"
    ),
    "evaluate_objectives_grade":State(
        name="evaluate_objectives_grade",
        description="Asks the user to evaluate the project objectives grade.",
        allowed_tools=[],
        prompt_name="question_prompt",
        verification_prompt_name="objectives_evaluation_verification_prompt",
        question="Czy cele projektu zostały osiągnięte? Jaką ocenę byś wystawił i dlaczego?",
        next_state="done"
    ),
    "evaluate_project_grade":State(
        name="evaluate_project_grade",
        description="Asks the user to evaluate the project grade.",
        allowed_tools=[],
        prompt_name="question_prompt",
        verification_prompt_name=None,
        question="Jaką ocenę wystawiłbyś projektowi i dlaczego?",
        next_state="done"
    ),
    "done": State(
        name="done",
        description="The final state of the agent workflow.",
        allowed_tools=[],
        prompt_name="done_prompt",
        verification_prompt_name=None,
        question="Dziękuję za udział w wywiadzie.",
        next_state="done"
    ),
}

