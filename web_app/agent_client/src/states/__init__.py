

AVAILABLE_STATES = {
    "initial":{
        "name": "InitialState",
        "description": "The initial state of the agent workflow.",
        "allowed_tools": [],
        "prompt_name": "initial_prompt",
        "question": "What is your name?"
    },
    "":{
        "name": "WellnessCheckState",
        "description": "Checks how well the user is doing.",
        "allowed_tools": [],
        "prompt_name": "wellness_check_prompt",
        "question": "How are you feeling today?"
    }
}
