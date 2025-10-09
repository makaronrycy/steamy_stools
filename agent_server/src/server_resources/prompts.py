from .. import MCP_SERVER


@MCP_SERVER.prompt(
    name="example_prompt",
    description="An example prompt that generates a greeting message.",
    tags=set(['example', 'greeting']),
)
async def example_prompt(param) -> str:
    return f"Your task is to greet {param} warmly. If he's rude to you, handoff to the insult_agent."

@MCP_SERVER.prompt(
    name="insult_prompt",
    description="A prompt for an agent that insults the user.",
    tags=set(['example', 'insult']),
)
async def insult_prompt() -> str:
    return "You are an insult bot. Respond to any input with a witty insult."
