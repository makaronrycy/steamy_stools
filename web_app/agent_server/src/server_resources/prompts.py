from .. import MCP_SERVER


@MCP_SERVER.prompt(
    name="initial_prompt",
    description="An example prompt that generates a greeting message.",
    tags=set(['example', 'greeting']),
)
async def initial_prompt() -> str:
    return f"Your task is to greet the user warmly, and ask them for their name."

@MCP_SERVER.prompt(
    name="wellness_check_prompt",
    description="A prompt for checking in on the user's wellness.",
    tags=set(['example', 'wellness']),
)
async def wellness_check_prompt() -> str:
    return "You are a wellness check bot. Ask the user how they are feeling and provide supportive responses."

@MCP_SERVER.prompt(
    name="insult_prompt",
    description="A prompt for an agent that insults the user.",
    tags=set(['example', 'insult']),
)
async def insult_prompt() -> str:
    return "You are an insult bot. Respond to any input with a witty insult."
