from .agent import AgentWorkflow
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from sanic import Sanic,response,request
from .states import AVAILABLE_STATES
from langfuse import Langfuse
def get_app() -> Sanic:
    app = Sanic("AgentClientApp")

    @app.route("/start_agent", methods=["POST"])
    async def start_agent(request: request.Request):
        """Change agent according to request data and to the field stated there."""
        data = request.json
        print(f"Received data: {data}")
        state_key = data.get("state", "initial")
        last_state_key = data.get("last_state", None)
        print(f"State key: {state_key}, Last state key: {last_state_key}")
        state = AVAILABLE_STATES.get(state_key, AVAILABLE_STATES["initial"])
        
        if last_state_key:
            last_state = AVAILABLE_STATES.get(last_state_key, None)
            if last_state:
                next_state = last_state.name
            else:
                next_state = state.next_state
                print(f"Warning: last_state_key '{last_state_key}' not found in AVAILABLE_STATES")
        else:
            last_state = None
            next_state = state.next_state
        
        user_anwser = data.get("anwser", "No anwser for last question.")

        mcp_server = MCPServerStreamableHttp(
            params=MCPServerStreamableHttpParams(
                url='http://localhost:7000/mcp'
            )
        )
        await mcp_server.connect()
        
        agent_workflow = AgentWorkflow(state=state, mcp_server=mcp_server,user_anwser=user_anwser, last_state=last_state)
        question = []
        async for step in agent_workflow.run():
            if step["state"] == "ANSWERING":
                question.append(step["answer"])
            if step["state"] == "NEXT_QUESTION":
                #To znaczy że aktualne pytanie zostało zadane, więc przechodzimy do następnego stanu
                next_state = state.next_state
        await mcp_server.cleanup()
        res = {
            "status": "completed",
            "question": ' '.join(question),
            "next_state": next_state,
            "current_state": state.name
        }
        return response.json(res,ensure_ascii=False)

    return app
