

AVAILABLE_STATES = {
    "initial":{
        "name": "InitialState",
        "description": "The initial state of the agent workflow.",
        "allowed_tools": [],
        "allowed_handoffs": ["InsultAgent"],
        "prompt_name": "initial_prompt",
        "question": "What is your name?"
    },
    "wellness_check":{
        "name": "WellnessCheckState",
        "description": "Checks how well the user is doing.",
        "allowed_tools": [],
        "allowed_handoffs": [],
        "prompt_name": "wellness_check_prompt",
        "question": "How are you feeling today?"
    }
}
