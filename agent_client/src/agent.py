
import asyncio
from typing import AsyncGenerator, Dict, Any
from agents.mcp import MCPServerStreamableHttp
from agents import Agent,Runner,handoff
import logging
class AgentWorkflow:
    def __init__(self, task, mcp_server: MCPServerStreamableHttp):
        self.task = task
        self.mcp_server = mcp_server
        self.model = "gpt-4o"
    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"state": "STARTING"}
        agent = await self.prepare_agent()
        runner =  Runner()
        prompt = f"""Zadanie użytkownika: {self.task}"""
        result = runner.run_streamed(starting_agent=agent, input=prompt)
        
        async for step in result.stream_events():
            #logging.warning(f"Step: {step}")
            if step.type == "raw_response_event":
                if step.data.type == 'response.output_text.delta':
                    yield {"state": "ANSWERING", "answer": step.data.delta}
            elif step.type == "agent_updated_stream_event":
                yield {"state": "THINKING", "thought": step.type}
                match step.new_agent.name:
                    case "InsultAgent":
                        yield {"state": "INSULTING"}
                    case _:
                        yield {"state": "THINKING"}
            elif step.type == "run_item_stream_event":
                try:
                    if step.item.type == "tool_call_item":
                        yield {"state": "TOOL_CALL", "tool_name": step.item.raw_item}
                    elif step.item.type == "tool_call_output_item":
                        yield {"state": "TOOL_OUTPUT", "tool_output": step.item.raw_item["output"]}
                except Exception as e:
                    logging.error(f"Error processing run item: {e}")


        yield {"state": "DONE"}

    async def prepare_agent(self) ->Agent:
        try:
            agent_prompt = await self.mcp_server.session.get_prompt("example_prompt",arguments={"param": "Studenciak"})
            agent = Agent(
                name="ExampleAgent",
                model = self.model,
                instructions=agent_prompt.messages[0].content.text,
                handoffs=[
                    handoff(
                        tool_name_override="insult_agent",
                        agent=await self.prepare_insult_agent()
                    )
                ],
                mcp_servers=[self.mcp_server],
            )
            return agent
        except Exception as e:
            raise RuntimeError(f"Failed to prepare agent: {e}")
    async def prepare_insult_agent(self) ->Agent:
        try:
            agent_prompt = await self.mcp_server.session.get_prompt("insult_prompt")
            agent = Agent(
                name="InsultAgent",
                model = self.model,
                instructions=agent_prompt.messages[0].content.text,
            )
            return agent
        except Exception as e:
            raise RuntimeError(f"Failed to prepare agent: {e}")