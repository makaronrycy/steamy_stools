from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams

import asyncio
from dotenv import load_dotenv
from src import AgentWorkflow

async def main():
    try:
        
        mcp_server = MCPServerStreamableHttp(
            params=MCPServerStreamableHttpParams(
                url='http://localhost:7000/mcp'
            )
        )
        await mcp_server.connect()
    
        task = "Fuck you, go to hell"
        agent = AgentWorkflow(task=task, mcp_server=mcp_server)
        async for x in agent.run():
            print(x['state'])
            if x['state'] == 'ANSWERING':
                print(x['answer'])

        await mcp_server.cleanup()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())