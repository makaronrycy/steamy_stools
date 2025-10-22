from .agent import AgentWorkflow
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from sanic import Sanic,response,request
from .states import AVAILABLE_STATES

def get_app() -> Sanic:
    app = Sanic("AgentClientApp")

    @app.route("/start_agent", methods=["POST"])
    async def start_agent(request: request.Request):
        """Change agent according to request data and to the field stated there."""
        data = request.json
        state_key = data.get("state", "initial")
        state = AVAILABLE_STATES.get(state_key, AVAILABLE_STATES["initial"])
        user_anwser = data.get("anwser", "No anwser for last question.")

        mcp_server = MCPServerStreamableHttp(
            params=MCPServerStreamableHttpParams(
                url='http://localhost:7000/mcp'
            )
        )
        await mcp_server.connect()

        agent_workflow = AgentWorkflow(state=state, mcp_server=mcp_server,user_anwser=user_anwser)
        question = []
        async for step in agent_workflow.run():
            if step["state"] == "ANSWERING":
                question.append(step["answer"])

        await mcp_server.cleanup()
        res = {
            "status": "completed",
            "question": ' '.join(question)
        }
        return response.json(' '.join(question))

    return app
