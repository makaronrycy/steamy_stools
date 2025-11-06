from .agent import AgentWorkflow
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from sanic import Sanic, response, request
from .conversation_flow import ConversationFlow
import logging 

def get_app() -> Sanic:
    app = Sanic("HotSeatsApp")
    
    # Przechowuj sesje rozmów
    conversation_flows = {}

    @app.route("/start_agent", methods=["POST"])
    async def start_agent(req: request.Request):
        data = req.json
        
        session_id = data.get("session_id", "default")
        user_answer = data.get("answer", "")
        
        # Pobierz/stwórz ConversationFlow - WSPÓŁDZIELONY między requestami
        if session_id in conversation_flows:
            flow = conversation_flows[session_id]
            logging.info(f"Loaded session {session_id}")
            logging.info(f"Current state: {flow.to_dict()}")
        else:
            flow = ConversationFlow()
            conversation_flows[session_id] = flow
            logging.info(f"New session {session_id}")
        
        # Połącz z MCP
        mcp_server = MCPServerStreamableHttp(
            params=MCPServerStreamableHttpParams(url='http://localhost:7000/mcp')
        )
        await mcp_server.connect()
        
        # Uruchom workflow
        workflow = AgentWorkflow(
            user_answer=user_answer,
            conversation_flow=flow,
            mcp_server=mcp_server
        )
        
        question_parts = []
        context = None
        
        # Stream odpowiedzi
        async for step in workflow.run():
            if step["state"] == "ANSWERING":
                question_parts.append(step["answer"])
            elif step["state"] == "DONE":
                context = step.get("context")
                logging.info(f"Received DONE with context: {context}")
        
        await mcp_server.cleanup()
        
        full_question = ''.join(question_parts)
        
        # Użyj context z ConversationFlow
        if not context:
            context = flow.to_dict()
            logging.info(f"Using flow.to_dict() as context: {context}")
        
        # Sprawdź czy zakończone (wszystkie oceny kompletne)
        is_complete = (
            context.get("verified") and
            context.get("has_self_grade") and
            len(context.get("graded_teammates", [])) > 0
        )
        
        res = {
            "status": "done" if is_complete else "in_progress",
            "question": full_question,
            "session_id": session_id,
            "context": context,
            "is_complete": is_complete,
        }
        # ZAPISZ flow do słownika PRZED returnem!
        conversation_flows[session_id] = flow
        logging.info(f"Saved session {session_id} state: {flow.to_dict()}")
        return response.json(res, ensure_ascii=False)
    
    @app.route("/reset_session", methods=["POST"])
    async def reset_session(req: request.Request):
        """Reset sesji"""
        session_id = req.json.get("session_id", "default")
        if session_id in conversation_flows:
            del conversation_flows[session_id]
        return response.json({"status": "reset"})

    return app
