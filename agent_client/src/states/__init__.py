from pydantic import BaseModel
from typing import Optional, List

class State(BaseModel):
    name: str
    description: str
    prompt_name: str
    verification_prompt_name: Optional[str]
    question: str
    tool_instructions: str = ""

    # tool access split by phase
    allowed_tools_question: List[str] = []
    allowed_tools_verification: List[str] = []

AVAILABLE_STATES = {
    "initial": State(
        name="initial",
        description="Initial step - identify the user.",
        prompt_name="initial_prompt",
        verification_prompt_name=None,
        question="Na początek potwierdź proszę swoje dane.",
        allowed_tools_question=["get_user_info_tool"],
        allowed_tools_verification=[],
    ),

    "self_evaluation": State(
        name="self_evaluation",
        description="Self assessment.",
        prompt_name="question_prompt",
        verification_prompt_name="self_evaluation_verification_prompt",
        question="Jaką ocenę (2.0–5.0) wystawiłbyś sobie i dlaczego? Podaj ocenę i krótkie uzasadnienie.",
        allowed_tools_question=[],
        allowed_tools_verification=["set_self_grade_tool"],
    ),

    "evaluate_teammate_grade": State(
        name="evaluate_teammate_grade",
        description="Evaluate teammate.",
        prompt_name="question_prompt",
        verification_prompt_name="teammate_evaluation_verification_prompt",
        question="Jaką ocenę (2.0–5.0) wystawiłbyś swojemu koledze/koleżance (zależne od osoby) z zespołu i dlaczego? Podaj ocenę i krótkie uzasadnienie.",
        allowed_tools_question=["get_user_info_tool"],
        # NO random tool here – verification must save for the pending_target
        allowed_tools_verification=["set_teammate_grade_tool", "identify_teammate_by_name_tool"],
    ),

    "evaluate_project_grade": State(
        name="evaluate_project_grade",
        description="Evaluate projects.",
        prompt_name="question_prompt",
        verification_prompt_name="project_evaluation_verification_prompt",
        question="Jaką ocenę (2.0–5.0) wystawiłbyś projektowi i dlaczego? Podaj ocenę i krótkie uzasadnienie. Nie referuj do id projektu, tylko do jego nazwy.",
        allowed_tools_question=["get_user_info_tool"],
        allowed_tools_verification=["set_project_grade_tool", "get_user_info_tool"],
    ),

    "evaluate_leader_grade": State(
        name="evaluate_leader_grade",
        description="Evaluate leader.",
        prompt_name="question_prompt",
        verification_prompt_name="leader_evaluation_verification_prompt",
        question="Jaką ocenę (2.0–5.0) wystawiłbyś swojemu liderowi i dlaczego? Podaj ocenę i krótkie uzasadnienie.",
        allowed_tools_question=["get_user_info_tool"],
        allowed_tools_verification=["get_leader_info_tool", "set_leader_grade_tool"],
    ),

    "evaluate_objectives": State(
        name="evaluate_objectives",
        description="Evaluate objectives grade.",
        prompt_name="question_prompt",
        verification_prompt_name="objectives_evaluation_verification_prompt",
        question="Jak oceniasz realizację celów projektu (2.0–5.0) i dlaczego? Podaj ocenę i krótkie uzasadnienie.",
        allowed_tools_question=["get_user_info_tool"],
        allowed_tools_verification=["set_project_objectives_grade_tool"],
    ),

    "evaluate_assumption": State(
        name="evaluate_assumption",
        description="Evaluate project assumptions fulfillment.",
        prompt_name="question_prompt",
        verification_prompt_name="assumption_evaluation_verification_prompt",
        question="Czy to założenie zostało zrealizowane? Odpowiedz TAK lub NIE i uzasadnij w 1–2 zdaniach.",
        allowed_tools_question=["get_user_info_tool"],
        allowed_tools_verification=["set_assumption_evaluation_tool"],
    ),

    "masters_intent": State(
        name="masters_intent",
        description="Masters intent.",
        prompt_name="question_prompt",
        verification_prompt_name="masters_intent_verification_prompt",
        question="Czy planujesz kontynuować studia na magisterce? Uzasadnij krótko.",
        allowed_tools_question=["get_user_info_tool"],
        allowed_tools_verification=["set_masters_intent_tool"],
    ),

    "study_program_feedback": State(
        name="study_program_feedback",
        description="Feedback on program.",
        prompt_name="question_prompt",
        verification_prompt_name="study_program_feedback_verification_prompt",
        question="Jak oceniasz program studiów? Co byś zmienił/a? Odpowiedz krótko.",
        allowed_tools_question=["get_user_info_tool"],
        allowed_tools_verification=["set_study_program_feedback_tool"],
    ),

    "done": State(
        name="done",
        description="Final.",
        prompt_name="done_prompt",
        verification_prompt_name=None,
        question="Dziękuję za udział w wywiadzie.",
        allowed_tools_question=["get_user_info_tool"],
        allowed_tools_verification=[],
    ),
}
