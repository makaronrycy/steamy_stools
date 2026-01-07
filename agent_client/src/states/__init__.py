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
        allowed_tools=["get_user_info_tool"],
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
        tool_instructions="NAJPIERW wywołaj get_random_ungraded_member_tool aby sprawdzić kto jest do oceny. NIE WYMYŚLAJ IMION! Używaj TYLKO imion zwróconych przez narzędzie. Jeśli wszyscy ocenieni - przejdź dalej.",
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
    "masters_intent": State(
        name="masters_intent",
        description="Asks the user whether they plan to continue to master's studies.",
        allowed_tools=["set_masters_intent_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="masters_intent_verification_prompt",
        question="Czy zamierza pan/pani zostac na magisterke ?",
    ),
    "study_program_feedback": State(
        name="study_program_feedback",
        description="Asks the user for feedback on the study program.",
        allowed_tools=["set_study_program_feedback_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="study_program_feedback_verification_prompt",
        question="Jakie uwagi do kierunku studiow?",
    ),
    "evaluate_project_grade":State(
        name="evaluate_project_grade",
        description="Asks the user to evaluate the project grade.",
        allowed_tools=["get_ungraded_projects_tool","set_project_grade_tool"],
        prompt_name="question_prompt",
        verification_prompt_name="project_evaluation_verification_prompt",
        tool_instructions="NAJPIERW wywołaj get_ungraded_projects_tool aby uzyskać listę nieocenionych projektów z ich project_id. Następnie zapytaj użytkownika o ocenę JEDNEGO projektu. Nie wymyślaj nazw projektów - używaj TYLKO nazw z narzędzia!",
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

