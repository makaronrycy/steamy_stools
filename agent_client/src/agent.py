
import asyncio
from typing import AsyncGenerator, Dict, Any
from agents.mcp import MCPServerStreamableHttp
class Agent:
    def __init__(self, task, mcp_server: MCPServerStreamableHttp):
        self.task = task
        self.mcp_server = mcp_server
    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"state": "STARTING"}
        await asyncio.sleep(1)
        yield {"state": "PROCESSING"}
        await asyncio.sleep(2)
        try:
            prompts = await self.mcp_server.list_prompts()
        except Exception as e:
            yield {"state": "ERROR", "error": str(e)}
            return
        yield {"state": "ANSWERING", "answer": f"Answer to '{prompts}' for task '{self.task}'"}
        yield {"state": "DONE"}