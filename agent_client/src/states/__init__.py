from pydantic import BaseModel

class State(BaseModel):
    name: str
    description: str
    allowed_tools: list[str]
    prompt_name: str
    verification_prompt_name: str
    question: str
    next_state: str

AVAILABLE_STATES = {
    "initial": State(
        name="initial",
        description="The initial state of the agent workflow.",
        allowed_tools=[],
        prompt_name="initial_prompt",
        verification_prompt_name="verification_prompt",
        question="Cześć! Jak masz na imię?",
        next_state="mood"
    ),
    "mood": State(
        name="mood",
        description="Asks about how the user feels.",
        allowed_tools=[],
        prompt_name="mood_question_prompt",
        verification_prompt_name="mood_classify_prompt",
        question="Jak się dziś czujesz?",
        next_state="done" # Narazie loop
    )
}

