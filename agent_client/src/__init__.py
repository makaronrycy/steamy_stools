from .agent import AgentWorkflow
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from sanic import Sanic, response, request
from .states import AVAILABLE_STATES
from .utils import context_aware_filter
from langfuse import Langfuse
import json
import os

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:10000")

def get_app() -> Sanic:
    app = Sanic("AgentClientApp")

    @app.route("/start_agent", methods=["POST"])
    async def start_agent(request: request.Request):
        try:
            data = request.json

            print(f"Received data: {data}")

            # Only require user_id and answer
            user_id = data.get("user_id", 0)
            user_anwser = data.get("anwser", "No anwser for last question.")

            question_target = data.get("question_target", "general")

            print(f"Connecting to MCP server at {MCP_SERVER_URL}/mcp...")

            # Connect to MCP server
            try:
                mcp_server = MCPServerStreamableHttp(
                    params=MCPServerStreamableHttpParams(
                        url=f'{MCP_SERVER_URL}/mcp',
                        headers={
                            "user_id": str(user_id),
                        },
                    ),
                    client_session_timeout_seconds=60.0,
                    tool_filter=context_aware_filter
                )
                print(f"MCP server object created, attempting connection...")
                await mcp_server.connect()
                print("MCP server connected successfully")
            except Exception as mcp_error:
                print(f"FATAL: MCP server connection failed: {mcp_error}")
                import traceback
                traceback.print_exc()
                raise

            # Determine current state from server if not provided (new mode)
            session_last_state = None
            state_tool_result = await mcp_server.session.call_tool("get_next_required_state_tool")
            state_data = state_tool_result.model_dump()
            state_dict = json.loads(state_data["content"][0]["text"])

            print(f"State tool result: {state_data}")
            # Use current_state_in_session (what's in DB) not next_state (what should be next)
            session_current_state_key = state_dict.get("current_state_in_session", "initial")
            session_last_state = state_dict.get("last_state", None)
            print(f"Current state from session: {session_current_state_key}")
            print(f"Last state from session: {session_last_state}")
            print(f"Next required state (for reference): {state_dict.get('next_state', 'N/A')}")

            # Get state configuration – to jest stan, W KTÓRYM działa agent w tej turze
            print(f"Getting state configuration for: {session_current_state_key}")
            current_state = AVAILABLE_STATES.get(session_current_state_key, AVAILABLE_STATES["initial"])

            # last_state tylko jako kontekst – NIE nadpisujemy nim current_state
            last_state_key = data.get("last_state", None) or session_last_state
            last_state = AVAILABLE_STATES.get(last_state_key, None) if last_state_key else None

            # get history of conversation from server
            history_tool_result = await mcp_server.session.call_tool("get_conversation_context_tool")
            history_data = history_tool_result.model_dump()
            history_dict = json.loads(history_data["content"][0]["text"])
            print(f"Retrieved conversation history: {history_dict}")

            # Run agent workflow
            print("Starting agent workflow...")
            agent_workflow = AgentWorkflow(
                state=current_state,
                mcp_server=mcp_server,
                user_anwser=user_anwser,
                last_state=last_state,
                user_id=user_id,
                question_target=question_target,
                history=history_dict.get("messages", [])
            )

            question = []

            # ---------------- KLUCZOWE ZARZĄDZANIE STANAMI ----------------
            # Stan, z którego pochodzi pytanie (to chcemy pokazać jako current_state)
            question_state_key = current_state.name
            # Domyślnie: jeśli nie będzie przejścia stanu, to next_state = ten sam
            session_state_after = question_state_key
            next_state_key = question_state_key
            # ---------------------------------------------------------------

            async for step in agent_workflow.run():
                if step["state"] == "ANSWERING":
                    question.append(step.get("answer", ""))

                if step["state"] == "NEXT_QUESTION":
                    # Pytanie zostało zadane na stanie current_state
                    question_state_key = current_state.name

                    try:
                        # 1. Ustalamy, co powinno być następnym stanem
                        print(f"Determining next state after completing {question_state_key}")
                        next_state_result = await mcp_server.session.call_tool("get_next_required_state_tool")
                        next_state_data = next_state_result.model_dump()
                        next_state_dict = json.loads(next_state_data["content"][0]["text"])

                        # To jest logiczny "next_state" z punktu widzenia FSM
                        next_state_key = next_state_dict.get("next_state", question_state_key)
                        print(f"Next state determined: {next_state_key}")
                        print(f"Reason: {next_state_dict.get('reason', 'N/A')}")

                        # 2. Aktualizujemy sesję w DB: question_state -> last_state, next_state -> current_state
                        print(f"Updating session state: {question_state_key} -> last_state, {next_state_key} -> current_state")
                        update_result = await mcp_server.session.call_tool(
                            "update_session_state_tool",
                            arguments={"new_state": next_state_key}
                        )
                        update_data = update_result.model_dump()
                        update_dict = json.loads(update_data["content"][0]["text"])
                        if update_dict.get("success"):
                            session_state_after = next_state_key
                            print(
                                f"Session updated successfully: "
                                f"last_state={update_dict.get('last_state')}, "
                                f"current_state={update_dict.get('new_state')}"
                            )
                        else:
                            # Jeśli update się nie udał – zostajemy przy stanie, z którego padło pytanie
                            session_state_after = question_state_key
                            print(f"Warning: Session update returned error: {update_dict.get('error')}")
                            raise Exception(
                                f"Session state update failed, db probably empty: {update_dict.get('error')}"
                            )

                    except Exception as e:
                        # W razie błędu nie ruszamy session_state_after (zostaje question_state_key)
                        print(f"Error in state transition: {e}")
                        import traceback
                        traceback.print_exc()

            # Save conversation messages to history
            try:
                print("Saving conversation messages to history...")
                session_id = state_dict.get("session_id")
                if session_id:
                    # Save user's answer (if not empty/initial)
                    if user_anwser and user_anwser != "No anwser for last question.":
                        await mcp_server.session.call_tool(
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "user",
                                "content": user_anwser,
                                # stan, w którym użytkownik odpowiadał na to pytanie
                                "state_at_time": question_state_key,
                            }
                        )
                        print(f"User message saved")

                    # Save agent's question
                    agent_question = ''.join(question)
                    if agent_question and user_anwser != "No anwser for last question.":
                        await mcp_server.session.call_tool(
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": agent_question,
                                # to samo: pytanie należy do question_state
                                "state_at_time": question_state_key,
                            }
                        )
                        print(f"Agent message saved")
                else:
                    print("Warning: No session_id available, skipping message history save")
            except Exception as e:
                print(f"Error saving conversation history: {e}")
                import traceback
                traceback.print_exc()
                # Don't fail the request if history save fails

            await mcp_server.cleanup()

            # ---------------- ZWROTKA DO KLIENTA ----------------
            # current_state -> stan, z którego jest to pytanie
            # next_state    -> stan, który jest ustawiony w sesji PO tej turze
            res = {
                "status": "completed",
                "question": ''.join(question),
                "current_state": question_state_key,
                "next_state": session_state_after,
            }
            print(f"Returning response: {res}")
            return response.json(res, ensure_ascii=False)

        except Exception as e:
            print(f"ERROR in start_agent endpoint: {e}")
            import traceback
            traceback.print_exc()
            return response.json({
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }, status=500)

    return app
