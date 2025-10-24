from .. import MCP_SERVER
from .models import NameEntity,Message
@MCP_SERVER.tool(
    name="example_tool",
    description="An example tool that does something useful.",
    tags=set(['example', 'utility']),
)
async def example_tool(param: Message) -> str:
    # Implement the tool's functionality here
    return f"Tool executed with param: {param.content}"

@MCP_SERVER.tool(
    name="check_name_tool",
    description="Narzędzie sprawdzające, czy podane imię i nazwisko istnieje w bazie danych.",
    tags=set(['verification', 'database']),
)
async def check_name_tool(param: NameEntity ) -> str:
    # Przykładowa implementacja - w rzeczywistości sprawdź w bazie danych
    database = {
        ("Jan", "Kowalski"),
        ("Anna", "Nowak"),
        ("Piotr", "Wiśniewski"),
    }
    try:
        data = param.model_dump()
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        if (first_name, last_name) in database:
            return "FOUND"
        else:
            return "NOT_FOUND"
    except Exception as e:
        return f"ERROR: {str(e)}"