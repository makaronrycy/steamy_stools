from pydantic import BaseModel

class State(BaseModel):
    name: str
    description: str
    allowed_tools: list[str]
    tool_instructions: str = ""
    prompt_name: str
    verification_prompt_name: str|None
    question: str

AVAILABLE_STATES = {
    "initial": State(
        name="initial",
        description="The initial state of the agent workflow.",
        allowed_tools=[],
        prompt_name="initial_prompt",
        verification_prompt_name="initial_verification_prompt",
        question="Pytanie o imię i nazwisko użytkownika.",
    ),
    "self_evaluation": State(
        name="self_evaluation",
        description="Asks the user to evaluate themselves.",
        allowed_tools=["set_self_grade_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="self_evaluation_verification_prompt",
        question="Jak oceniasz swój wkład w projekcie i jakie były twoje zadania",
    ),
    "evaluate_teammate_grade":State(
        name="evaluate_teammate_grade",
        description="Asks the user to evaluate a teammate's grade.",
        allowed_tools=["get_random_ungraded_member_tool","set_teammate_grade_tool","identify_teammate_by_name_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="teammate_evaluation_verification_prompt",
        tool_instructions="Jeśli pytanie jest o członka zespołu, wylosuj nieocenionego członka zespołu używając get_random_ungraded_member_tool. Następnie wykorzystaj jego imię i nazwisko w dalszej rozmowie. Jeśli już jest w historii rozmowy, nie musisz ponownie losować, chyba że został oceniony. Nie wspominaj o losowaniu w rozmowie.",
        question="Jaką ocenę wystawiłbyś swojemu koledze z zespołu i dlaczego?",
    ),
    "evaluate_leader_grade":State(
        name="evaluate_leader_grade",
        description="Asks the user to evaluate the leader's grade.",
        allowed_tools=["get_leader_info_tool","set_leader_grade_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="leader_evaluation_verification_prompt",
        tool_instructions="Jeśli pytanie jest o lidera zespołu, użyj get_leader_info_tool aby uzyskać imię i nazwisko lidera zespołu. Następnie wykorzystaj jego imię i nazwisko w dalszej rozmowie. Nie wspominaj o użyciu narzędzia w rozmowie.",
        question="Jaką ocenę wystawiłbyś swojemu liderowi i dlaczego?",
    ),
    "evaluate_objectives":State(
        name="evaluate_objectives",
        description="Asks the user to evaluate the project objectives grade.",
        allowed_tools=["set_project_objectives_grade_tool","get_user_info_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="objectives_evaluation_verification_prompt",
        question="Czy cele projektu zostały osiągnięte? Jaką ocenę byś wystawił i dlaczego?",
    ),
    "evaluate_project_grade":State(
        name="evaluate_project_grade",
        description="Asks the user to evaluate the project grade.",
        allowed_tools=["get_ungraded_projects_tool","set_project_grade_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="project_evaluation_verification_prompt",
        tool_instructions="Jeśli pytanie jest o ocene projektu, wykorzystaj get_ungraded_project_tool aby uzyskać nazwę nieocenionych projektów. Następnie wybierz JEDEN z nich i zapytaj się o ocenienie go. Nie wspominaj o użyciu narzędzia w rozmowie.",
        question="Jaką ocenę wystawiłbyś projektowi i dlaczego?",
    ),
    "done": State(
        name="done",
        description="The final state of the agent workflow.",
        allowed_tools=[],
        prompt_name="done_prompt",
        verification_prompt_name=None,
        question="Dziękuję za udział w wywiadzie.",
    ),
}

