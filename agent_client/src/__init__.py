from .agent import AgentWorkflow
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from sanic import Sanic,response,request
from .states import AVAILABLE_STATES
import json

def get_app() -> Sanic:
    app = Sanic("AgentClientApp")

    @app.route("/start_agent", methods=["POST"])
    async def start_agent(request: request.Request):
        """Change agent according to request data and to the field stated there."""
        data = request.json or {}
        state_key = data.get("state", "initial")
        state = AVAILABLE_STATES.get(state_key, AVAILABLE_STATES["initial"])
        user_anwser = (data.get("anwser") or "").strip()
        state_now     = (data.get("state") or "initial").strip().lower()
        came_from     = (data.get("last_state") or "none").strip().lower()   # "none" | "question" | "verify"
        last_question = (data.get("last_question") or "").strip()

        verification_prompt_name = state.get("verification_prompt_name", "verification_prompt")
        last_state_dict = {
            "question": last_question,
            "verification_prompt": verification_prompt_name,
        }
        question_prompt_name = state.get("prompt_name", "initial_prompt")


        mcp_server = MCPServerStreamableHttp(
            params=MCPServerStreamableHttpParams(
                url='http://localhost:7000/mcp'
            )
        )
        await mcp_server.connect()

        # 1) initial/question -> GENERUJEMY PYTANIE i idziemy do verify
        if state_now in ("initial", "question"):
            agent_workflow = AgentWorkflow(
                state={"name": state.get("name", "InitialState"), "prompt_name": question_prompt_name},
                mcp_server=mcp_server,
                user_anwser="",
                last_state={"question": state.get("question", ""),"verification_prompt": verification_prompt_name,}

            )
            question = []
            async for step in agent_workflow.run():
                if step["state"] == "ANSWERING":
                    question.append(step["answer"])

            await mcp_server.cleanup()
            reply = ''.join(question).strip()
            return response.json({"reply": reply, "state": "verify", "last_state": "question", "last_question": reply},ensure_ascii=False)


        # 2) verify (przyszliśmy z question) -> WERYFIKUJEMY ODPOWIEDŹ i wracamy po kolejne pytanie
        if state_now == "verify" and came_from == "question":
            agent_workflow = AgentWorkflow(
                state={"name": "VerifyState", "prompt_name": question_prompt_name},
                mcp_server=mcp_server,
                user_anwser=user_anwser,
                last_state=last_state_dict,   # ma {"question": last_question, "verification_prompt": ...}
            )
            chunks = []
            async for step in agent_workflow.run():
                if step.get("state") == "ANSWERING":
                    chunks.append(step["answer"])

            reply = "".join(chunks).strip()

           # --- jeśli weryfikowaliśmy IMIĘ i jest w pseudo-bazie, przejdź do pytania o nastrój ---
            allowed_names = {"filip", "maurycy", "antek"}
            is_known = (user_anwser or "").strip().lower() in allowed_names
            if "imię" in (last_question or "").lower():
                if not is_known:
                    # brak w bazie -> zadaj to samo pytanie ponownie (jak masz już zrobione – zostaw swój kod)
                    reask_wf = AgentWorkflow(
                        state={"name": state.get("name", "InitialState"), "prompt_name": question_prompt_name},
                        mcp_server=mcp_server,
                        user_anwser="",
                        last_state={"question": state.get("question", ""), "verification_prompt": verification_prompt_name},
                    )
                    q_parts = []
                    async for step in reask_wf.run():
                        if step.get("state") == "ANSWERING":
                            q_parts.append(step["answer"])
                    reask = "".join(q_parts).strip()
                    await mcp_server.cleanup()
                    return response.json({
                        "reply": f"Nie znalazłem osoby o imieniu „{user_anwser}”. Spróbuj jeszcze raz.\n{reask}",
                        "state": "verify",
                        "last_state": "question",
                        "last_question": reask
                    }, ensure_ascii=False)

                # jest w bazie -> WYGENERUJ PYTANIE O NASTRÓJ (stan 'mood')
                mood_q_wf = AgentWorkflow(
                    state={"name": "InitialState", "prompt_name": "mood_question_prompt"},
                    mcp_server=mcp_server,
                    user_anwser="",
                    last_state={
                        "question": AVAILABLE_STATES["mood"]["question"],
                        "verification_prompt": AVAILABLE_STATES["mood"]["verification_prompt_name"]  # = "mood_classify_prompt"
                    },
                )

                mood_parts = []
                async for step in mood_q_wf.run():
                    if step.get("state") == "ANSWERING":
                        mood_parts.append(step["answer"])
                mood_question = "".join(mood_parts).strip()
                await mcp_server.cleanup()
                return response.json({
                    "reply": f"{reply}\n\n{mood_question}",
                    "state": "verify",              # dalej weryfikujemy odpowiedź na nastrój
                    "last_state": "question",
                    "last_question": mood_question
                }, ensure_ascii=False)
            # --- jeśli weryfikujemy NAStrój (pytanie typu 'Jak się czujesz?') ---
            if any(s in (last_question or "").lower() for s in ["jak się", "czujesz"]):
                mood_verify_wf = AgentWorkflow(
                    state={"name": "VerifyState", "prompt_name": "mood_question_prompt"},
                    mcp_server=mcp_server,
                    user_anwser=user_anwser,
                    last_state={
                        "question": last_question,
                        "verification_prompt": AVAILABLE_STATES["mood"]["verification_prompt_name"] 
                    },
                )
                chunks2 = []
                async for step in mood_verify_wf.run():
                    if step.get("state") == "ANSWERING":
                        chunks2.append(step["answer"])
                mood_reply = "".join(chunks2).strip()

                label = "unknown"
                comment = mood_reply
                try:
                    parsed = json.loads(mood_reply)
                    label = (parsed.get("label") or "unknown").lower()
                    comment = parsed.get("comment") or comment
                except Exception:
                    pass

                FOLLOWUPS = {
                    "bad":   "Przykro to słyszeć. Co dokładnie się stało?",
                    "okay":  "Rozumiem. Co mogłoby choć trochę poprawić Twój dzień?",
                    "good":  "Super! Co dziś poszło najlepiej?"
                }
                next_q_text = FOLLOWUPS.get(label, "Opowiedz proszę trochę więcej — co masz na myśli?")

                # sformułuj to ładnie przez QuestionAgenta
                follow_wf = AgentWorkflow(
                    state={"name": state.get("name", "InitialState"), "prompt_name": question_prompt_name},
                    mcp_server=mcp_server,
                    user_anwser="",
                    last_state={"question": next_q_text, "verification_prompt": verification_prompt_name},
                )
                f_parts = []
                async for step in follow_wf.run():
                    if step.get("state") == "ANSWERING":
                        f_parts.append(step["answer"])
                follow_question = "".join(f_parts).strip()

                await mcp_server.cleanup()
                return response.json({
                    "reply": comment + "\n\n" + follow_question,
                    "state": "verify",
                    "last_state": "question",
                    "last_question": follow_question
                }, ensure_ascii=False)

        # 3) fallback – zachowuj się jak initial
        agent_workflow = AgentWorkflow(
            state={"name": state.get("name", "InitialState"), "prompt_name": question_prompt_name},
            mcp_server=mcp_server,
            user_anwser="",
            last_state={"question": "", "verification_prompt": verification_prompt_name},
        )
        question = []
        async for step in agent_workflow.run():
            if step["state"] == "ANSWERING":
                question.append(step["answer"])

        await mcp_server.cleanup()
        reply = ''.join(question).strip()
        return response.json({"reply": reply,"state": "verify","last_state": "question","last_question": reply}, ensure_ascii=False)


    return app
