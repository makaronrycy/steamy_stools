from .. import MCP_SERVER
from .models import Message
@MCP_SERVER.tool(
    name="example_tool",
    description="An example tool that does something useful.",
    tags=set(['example', 'utility']),
)
async def example_tool(param: Message) -> str:
    # Implement the tool's functionality here
    return f"Tool executed with param: {param.content}"
