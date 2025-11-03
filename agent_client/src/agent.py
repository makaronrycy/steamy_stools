
import asyncio
from typing import AsyncGenerator, Dict, Any
from agents.mcp import MCPServerStreamableHttp
from agents import Agent,Runner,handoff
import logging
from langfuse import Langfuse
from .states import State
import os
import logfire
import nest_asyncio
nest_asyncio.apply()
logfire.configure(
    service_name="Gorące Krzesła",
    send_to_logfire=False,

)
logfire.instrument_openai_agents()   # patchuje SDK i wysyła span-y do Langfuse

class AgentWorkflow:

    def __init__(self,user_id:int, user_anwser,last_state:State|None, state:State,mcp_server: MCPServerStreamableHttp,question_target:str="general"):
        self.user_id = user_id
        self.question_target = question_target
        self.user_anwser = user_anwser
        self.mcp_server = mcp_server
        self.state = state
        self.last_state = last_state
        self.model = "gpt-4o-mini"
    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            langfuse = Langfuse(
                secret_key=os.environ['LANGFUSE_SECRET_KEY'],
                public_key=os.environ['LANGFUSE_PUBLIC_KEY'],
                host=os.environ['LANGFUSE_HOST'],
                timeout=60,
            )
        except Exception as e:
            logging.error(f"Failed to initialize Langfuse: {e}")
        with langfuse.start_as_current_span(name ="AgentWorkflow Run") as span:
            yield {"state": "STARTING"}
            if self.state.name == "initial" or self.last_state.verification_prompt_name is None:
                agent = await self.prepare_question_agent(self.state.prompt_name)
            else:
                agent = await self.prepare_verification_agent(self.last_state.verification_prompt_name,self.state.prompt_name)

            runner =  Runner()
            ls = self.last_state if isinstance(self.last_state, dict) else {"question": str(self.last_state or "")}
            question_text = ls.get("question", "")
            prompt = f"Pytanie: {question_text}\nOdpowiedź użytkownika: {self.user_anwser}"
            langfuse.update_current_trace(
                user_id= str(self.user_id),
                input=prompt
            )
            result = runner.run_streamed(starting_agent=agent, input=prompt)

            async for step in result.stream_events():
                #logging.warning(f"Step: {step}")
                if step.type == "raw_response_event":
                    if step.data.type == 'response.output_text.delta':
                        yield {"state": "ANSWERING", "answer": step.data.delta}
                elif step.type == "agent_updated_stream_event":
                    yield {"state": "THINKING", "thought": step.type}
                    match step.new_agent.name:
                        case "VerificationAgent":
                            print("VerificationAgent handoff")
                            yield {"state": "VERIFYING"}
                        case "QuestionAgent":
                            print("QuestionAgent handoff")
                            yield {"state": "NEXT_QUESTION"}                    
                        case _:
                            yield {"state": "???"}
                elif step.type == "run_item_stream_event":
                    try:
                        if step.item.type == "tool_call_item":
                            yield {"state": "TOOL_CALL", "tool_name": step.item.raw_item}
                        elif step.item.type == "tool_call_output_item":
                            yield {"state": "TOOL_OUTPUT", "tool_output": step.item.raw_item["output"]}
                    except Exception as e:
                        logging.error(f"Error processing run item: {e}")

            try:
                langfuse.update_current_trace(
                    output ={
                        "final_answer": result.final_output,
                        "state": self.state.name,
                    }
                )
            except Exception as e:
                logging.error(f"Failed to update Langfuse trace: {e}")
            yield {"state": "DONE"}

    async def prepare_verification_agent(self,verification_prompt_name,question_prompt_name) ->Agent:
        try:
            #todo: dynamic handoffs based on allowed_handoffs
            agent_prompt = await self.mcp_server.session.get_prompt(verification_prompt_name)
            agent = Agent(
                name="VerificationAgent",
                model = self.model,
                instructions=agent_prompt.messages[0].content.text,
                handoffs=[
                    handoff(
                        tool_name_override="question_agent",
                        agent=await self.prepare_question_agent(question_prompt_name)
                    )
                ],
                mcp_servers=[self.mcp_server],
            )
            return agent
        except Exception as e:
            raise RuntimeError(f"Failed to prepare agent: {e}")
        
    async def prepare_question_agent(self,prompt_name) ->Agent:
        try:
            #todo: dynamic handoffs based on allowed_handoffs
            if prompt_name == "initial_prompt":
                agent_prompt = await self.mcp_server.session.get_prompt(prompt_name)
            else:
                agent_prompt = await self.mcp_server.session.get_prompt(prompt_name,{"question":self.state.question})
            agent = Agent(
                name="QuestionAgent",
                model = self.model,
                instructions=agent_prompt.messages[0].content.text,
                mcp_servers=[self.mcp_server],
            )
            return agent
        except Exception as e:
            raise RuntimeError(f"Failed to prepare agent: {e}")
