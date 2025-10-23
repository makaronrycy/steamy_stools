

AVAILABLE_STATES = {
    "initial": {
        "name": "InitialState",
        "description": "The initial state of the agent workflow.",
        "allowed_tools": [],
        "prompt_name": "initial_prompt",
        "verification_prompt_name": "verification_prompt",
        "question": "Cześć! Jak masz na imię?"
    },
    "mood": {
        "name": "MoodState",
        "description": "Asks about how the user feels.",
        "allowed_tools": [],
        "prompt_name": "mood_question_prompt",
        "verification_prompt_name": "mood_classify_prompt",
        "question": "Jak się dziś czujesz?"
    }
}

