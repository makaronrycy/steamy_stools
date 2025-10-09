from .. import MCP_SERVER


@MCP_SERVER.prompt(
    name="example_prompt",
    description="An example prompt that generates a greeting message.",
    tags=set(['example', 'greeting']),
)
async def example_prompt(name: str) -> str:
    return f"Hello, {name}! Welcome to our service."
