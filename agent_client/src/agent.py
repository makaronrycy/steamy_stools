import asyncio
from typing import AsyncGenerator, Dict, Any, List
from agents.mcp import MCPServerStreamableHttp
from agents import Agent,Runner,handoff,ModelSettings
import logging
from langfuse import Langfuse
from .states import State
from .conversation_flow import ConversationFlow
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

<<<<<<< HEAD
    def __init__(self, user_answer: str, conversation_flow: ConversationFlow, mcp_server: MCPServerStreamableHttp):
        self.user_answer = user_answer
=======
    def __init__(self,user_id:int, user_anwser,last_state:State|None, state:State,mcp_server: MCPServerStreamableHttp,question_target:str="general",history:list[Dict[str,Any]]=[]):
        self.user_id = user_id
        self.question_target = question_target
        self.user_anwser = user_anwser
>>>>>>> 4d5321619283b8dc8093911e785eb84038240694
        self.mcp_server = mcp_server
        self.flow = conversation_flow
        self.model = "gpt-4o-mini"
<<<<<<< HEAD
        
        # Trzymaj wyniki narzędzi
        self.tool_results = []
        
=======
        self.history = list(reversed(history))
>>>>>>> 4d5321619283b8dc8093911e785eb84038240694
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
<<<<<<< HEAD
        with langfuse.start_as_current_span(name="AgentWorkflow Run") as span:
            logging.info(f"=== WYWIAD START ===")
            logging.info(f"User: {self.user_answer}")
            
            yield {"state": "START"}
            
            # AI decyduje o kolejnym pytaniu
            prompt_name = self.flow.determine_next_question()
            logging.info(f"AI wybrało prompt: {prompt_name}")
            
            # Przygotuj agenta
            agent = await self.prepare_agent(prompt_name)
            runner = Runner()
            
            # Zbuduj input: KONTEKST + odpowiedź usera
            context_text = self.flow.get_context_for_prompt()
            prompt_text = f"{context_text}\n\n=== Odpowiedź użytkownika ===\n{self.user_answer if self.user_answer else '(pierwsze pytanie)'}"
            
            langfuse.update_current_trace(input=prompt_text)
            result = runner.run_streamed(starting_agent=agent, input=prompt_text)
=======
        with langfuse.start_as_current_span(name ="AgentWorkflow Run") as span:
            yield {"state": "STARTING"}
            if self.state.name == "initial" or self.state.name =="done" or self.last_state is None or self.last_state.verification_prompt_name is None:
                agent = await self.prepare_question_agent(self.state.prompt_name)
            else:
                agent = await self.prepare_verification_agent(self.last_state.verification_prompt_name,self.state.prompt_name)

            runner =  Runner()
            ls = self.last_state if isinstance(self.last_state, dict) else {"question": str(self.last_state or "")}
            prompt = f"Historia:{self.history}\nOdpowiedź użytkownika: {self.user_anwser}"
            langfuse.update_current_trace(
                user_id= str(self.user_id),
                input=prompt
            )
            result = runner.run_streamed(starting_agent=agent, input=prompt)
>>>>>>> 4d5321619283b8dc8093911e785eb84038240694

            # Stream odpowiedzi
            async for step in result.stream_events():
                if step.type == "raw_response_event":
                    if step.data.type == 'response.output_text.delta':
                        yield {"state": "ANSWERING", "answer": step.data.delta}
<<<<<<< HEAD
                        
=======
                elif step.type == "agent_updated_stream_event":
                    yield {"state": "THINKING", "thought": step.type}
                    agent_type = step.new_agent.name.split("/")[0]
                    match agent_type:
                        case "VerificationAgent":
                            print("VerificationAgent handoff")
                            yield {"state": "VERIFYING"}
                        case "QuestionAgent":
                            print("QuestionAgent handoff")
                            yield {"state": "NEXT_QUESTION"}                    
                        case _:
                            yield {"state": "???"}
>>>>>>> 4d5321619283b8dc8093911e785eb84038240694
                elif step.type == "run_item_stream_event":
                    try:
                        if step.item.type == "tool_call_item":
                            logging.info(f"TOOL_CALL: {step.item.raw_item}")
                            self.tool_results.append({"type": "call", "data": step.item.raw_item})
                        elif step.item.type == "tool_call_output_item":
                            logging.info(f"TOOL_OUTPUT: {step.item.raw_item}")
                            self.tool_results.append({"type": "output", "data": step.item.raw_item})
                    except Exception as e:
                        logging.error(f"Event error: {e}")

            # WYDOBĄDŹ INFO z odpowiedzi + narzędzi
            logging.info("Calling extract_info_from_response...")
            logging.info(f"tool_results length: {len(self.tool_results)}")
            
            extracted = self.flow.extract_info_from_response(self.user_answer, self._parse_tool_results())
            logging.info(f"Extracted: {extracted}")
            
            # Dodaj do historii
            if self.user_answer:
                self.flow.add_to_history("User", self.user_answer)
            self.flow.add_to_history("AI", result.final_output)
            
            logging.info(f"=== WYWIAD END ===")
            logging.info(f"Final flow state: {self.flow.to_dict()}")
            
            try:
                langfuse.update_current_trace(
                    output={"answer": result.final_output, "context": self.flow.to_dict()}
                )
            except Exception as e:
<<<<<<< HEAD
                logging.error(f"Langfuse error: {e}")
                
            yield {"state": "DONE", "context": self.flow.to_dict()}
    
    def _parse_tool_results(self) -> List[Dict]:
        """Parsuje wyniki narzędzi do jednolitego formatu"""
        parsed = []
=======
                logging.error(f"Failed to update Langfuse trace: {e}")
            yield {"state": "DONE"}

    async def prepare_verification_agent(self,verification_prompt_name,question_prompt_name) ->Agent:
        try:
            agent_prompt = await self.mcp_server.session.get_prompt(verification_prompt_name)
            agent = Agent(
                name=f"VerificationAgent/{self.last_state.name}",
                model = self.model,
                instructions=agent_prompt.messages[0].content.text,
                handoffs=[
                    handoff(
                        tool_name_override="question_agent",
                        agent=await self.prepare_question_agent(question_prompt_name)
                    )
                ],
                mcp_servers=[self.mcp_server],
                model_settings=ModelSettings(tool_choice="required")

            )
            return agent
        except Exception as e:
            raise RuntimeError(f"Failed to prepare agent: {e}")
>>>>>>> 4d5321619283b8dc8093911e785eb84038240694
        
        # Łącz call + output
        calls = [t["data"] for t in self.tool_results if t["type"] == "call"]
        outputs = [t["data"] for t in self.tool_results if t["type"] == "output"]
        
        for i, call in enumerate(calls):
            if hasattr(call, 'model_dump'):
                call_dict = call.model_dump()
            elif hasattr(call, 'dict'):
                call_dict = call.dict()
            elif hasattr(call, '__dict__'):
                call_dict = vars(call)
            else:
                logging.warning(f"Unknown call type: {type(call)}")
                call_dict = {}
            
            tool_name = call_dict.get("name", "")
            tool_input = call_dict.get("arguments", {})
            
            # Parse JSON jeśli string
            if isinstance(tool_input, str):
                import json
                try:
                    tool_input = json.loads(tool_input)
                except:
                    pass
            
            if i < len(outputs):
                output_item = outputs[i]
                if hasattr(output_item, 'model_dump'):
                    output_dict = output_item.model_dump()
                elif hasattr(output_item, 'dict'):
                    output_dict = output_item.dict()
                elif hasattr(output_item, '__dict__'):
                    output_dict = vars(output_item)
                elif isinstance(output_item, dict):
                    output_dict = output_item
                else:
                    logging.warning(f"Unknown output type: {type(output_item)}")
                    output_dict = {}
                
                tool_output = output_dict.get("output", "")
            else:
                tool_output = ""
            
            parsed.append({
                "name": tool_name,
                "input": tool_input,
                "output": tool_output,
            })
        
        return parsed

    async def prepare_agent(self, prompt_name: str) -> Agent:
        try:
            #todo: dynamic handoffs based on allowed_handoffs
            if prompt_name == "initial_prompt" or prompt_name == "done_prompt":
                agent_prompt = await self.mcp_server.session.get_prompt(prompt_name)
            else:
                agent_prompt = await self.mcp_server.session.get_prompt(prompt_name,{"question":self.state.question,"allowed_tools_instructions":self.state.tool_instructions})
            agent = Agent(
                name=f"QuestionAgent/{self.state.name}",
                model = self.model,
                instructions=agent_prompt.messages[0].content.text,
                mcp_servers=[self.mcp_server],
            )
            return agent
        except Exception as e:
            raise RuntimeError(f"Failed to prepare agent: {e}")
