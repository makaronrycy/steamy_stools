from agents import Agent, Runner, ModelSettings
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from sanic import Sanic, response, request
from .states import AVAILABLE_STATES,State
from .utils import context_aware_filter
from langfuse import Langfuse
import json
import os
import ast
import traceback

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:10000")
SAFE_WORD = os.getenv("SAFE_WORD", "KONIEC")


def get_app() -> Sanic:
    app = Sanic("AgentClientApp")

    # ---------------------- helpers ----------------------

    def _extract_tool_text(tool_result) -> str:
        data = tool_result.model_dump()
        try:
            return data["content"][0]["text"]
        except Exception:
            return ""

    def _parse_maybe_json(text: str):
        if not text or not isinstance(text, str):
            return None
        s = text.strip()
        if not s:
            return None

        # JSON first
        if s.startswith("{") or s.startswith("["):
            try:
                return json.loads(s)
            except Exception:
                pass

        # python-literal fallback
        try:
            return ast.literal_eval(s)
        except Exception:
            return None

    def _needs_target(state_key: str) -> bool:
        return state_key in ("evaluate_teammate_grade", "evaluate_project_grade", "evaluate_leader_grade", "evaluate_assumption")

    async def _compute_target_for_state(mcp_server: MCPServerStreamableHttp, state_key: str):
        """
        Picks the pending target for states that need it.
        IMPORTANT: relies on server tools returning JSON strings:
          - get_random_ungraded_member_tool -> dict or null
          - get_ungraded_projects_tool -> list[dict]
          - get_leader_info_tool -> dict
          - get_random_unevaluated_assumption_tool -> dict or null
        """
        if state_key == "evaluate_teammate_grade":
            r = await mcp_server.session.call_tool("get_random_ungraded_member_tool") 
            parsed = _parse_maybe_json(_extract_tool_text(r))
            return parsed if isinstance(parsed, dict) and parsed else None

        if state_key == "evaluate_project_grade":
            r = await mcp_server.session.call_tool("get_ungraded_projects_tool") 
            parsed = _parse_maybe_json(_extract_tool_text(r))
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                return parsed[0]
            return None

        if state_key == "evaluate_leader_grade":
            r = await mcp_server.session.call_tool("get_leader_info_tool") 
            parsed = _parse_maybe_json(_extract_tool_text(r))
            return parsed if isinstance(parsed, dict) and parsed else None

        if state_key == "evaluate_assumption":
            r = await mcp_server.session.call_tool("get_random_unevaluated_assumption_tool") 
            parsed = _parse_maybe_json(_extract_tool_text(r))
            return parsed if isinstance(parsed, dict) and parsed else None

        return None

    def _render_question_text(state_key: str, base_question: str, target: dict | None) -> str:
        if state_key == "evaluate_teammate_grade" and target:
            name = (target.get("name") or "").strip()
            surname = (target.get("surname") or "").strip()
            idx = target.get("index")
            return f"{base_question}\n\nOsoba: {name} {surname} (index: {idx})"

        if state_key == "evaluate_project_grade" and target:
            pname = (target.get("project_name") or "").strip()
            pid = target.get("project_id")
            return f"{base_question}\n\nProjekt: {pname} (id: {pid})"

        if state_key == "evaluate_leader_grade" and target:
            name = (target.get("name") or "").strip()
            surname = (target.get("surname") or "").strip()
            idx = target.get("index")
            pid = target.get("project_id")
            return f"{base_question}\n\nLider: {name} {surname} (index: {idx}), project_id: {pid}"

        if state_key == "evaluate_assumption" and target:
            assumption_name = (target.get("name") or "").strip()
            assumption_desc = (target.get("description") or "").strip()
            project_name = (target.get("project_name") or "").strip()
            # Bardziej naturalne pytanie
            if assumption_desc:
                return f"**{assumption_name}**\n_{assumption_desc}_\n\n{base_question}"
            return f"**{assumption_name}** (projekt: {project_name})\n\n{base_question}"

        return base_question

    def _is_yes(text: str) -> bool:
        t = (text or "").strip().lower()
        return (
            t in ("tak", "t", "yes", "y", "ok", "potwierdzam", "zgadza się", "zgadza sie", "to ja", "zgadza")
            or "tak" in t
        )

    def _is_safe_word(text: str) -> bool:
        return (text or "").strip().upper() == (SAFE_WORD or "KONIEC").strip().upper()

    async def _get_completion_status(mcp_server: MCPServerStreamableHttp) -> dict:
        r = await mcp_server.session.call_tool("get_student_completion_status_tool") 
        parsed = _parse_maybe_json(_extract_tool_text(r))
        return parsed if isinstance(parsed, dict) else {}

    async def _is_pending_state_completed(
        mcp_server: MCPServerStreamableHttp,
        pending_state_key: str,
        pending_target: dict | None
    ) -> tuple[bool, dict]:
        """
        DB-first completion check for the *pending* item.
        This prevents loops when model replied but tools didn't persist.
        Returns: (is_completed, completion_status)
        """
        st = await _get_completion_status(mcp_server)

        if pending_state_key == "self_evaluation":
            return bool(st.get("self_assessment", {}).get("is_complete")), st

        if pending_state_key == "evaluate_teammate_grade":
            if not pending_target or not pending_target.get("index"):
                return False, st
            tgt = str(pending_target.get("index"))
            incomplete = st.get("teammate_assessments", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("teammate_index")) == tgt:
                    return bool(d.get("has_grade")) and bool(d.get("has_explanation")), st
            return True, st

        if pending_state_key == "evaluate_project_grade":
            if not pending_target or not pending_target.get("project_id"):
                return False, st
            tgt = str(pending_target.get("project_id"))
            incomplete = st.get("project_assessments", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("project_id")) == tgt:
                    return bool(d.get("has_grade")) and bool(d.get("has_explanation")), st
            return True, st

        if pending_state_key == "evaluate_leader_grade":
            return bool(st.get("leadership_assessment", {}).get("is_complete")), st

        if pending_state_key == "evaluate_objectives":
            return bool(st.get("objectives_assessment", {}).get("is_complete")), st

        if pending_state_key == "evaluate_assumption":
            if not pending_target or not pending_target.get("assumption_id"):
                return False, st
            tgt = str(pending_target.get("assumption_id"))
            incomplete = st.get("assumption_evaluations", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("assumption_id")) == tgt:
                    return bool(d.get("has_evaluation")) and bool(d.get("has_explanation")), st
            return True, st

        if pending_state_key == "masters_intent":
            return bool(st.get("masters_intent", {}).get("is_complete")), st

        if pending_state_key == "study_program_feedback":
            return bool(st.get("study_program_feedback", {}).get("is_complete")), st

        return False, st

    def _missing_info_hint(pending_state_key: str, pending_target: dict | None, completion_status: dict) -> str:
        """
        Produces a clear clarification request based on DB completion flags.
        """
        if pending_state_key == "self_evaluation":
            det = completion_status.get("self_assessment", {})
            needs_grade = not det.get("has_grade", False)
            needs_exp = not det.get("has_explanation", False)
            if needs_grade and needs_exp:
                return "Podaj proszę **ocenę (2.0–5.0)** oraz **1–2 zdania uzasadnienia** w jednej wiadomości."
            if needs_grade:
                return "Podaj proszę **ocenę liczbową 2.0–5.0** (np. 4.5) + krótkie uzasadnienie (w jednej wiadomości)."
            if needs_exp:
                return "Dopisz proszę **1–2 zdania uzasadnienia** (razem z oceną w tej samej wiadomości)."

        if pending_state_key == "evaluate_teammate_grade":
            idx = pending_target.get("index") if pending_target else None
            incomplete = completion_status.get("teammate_assessments", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("teammate_index")) == str(idx):
                    needs_grade = not d.get("has_grade", False)
                    needs_exp = not d.get("has_explanation", False)
                    if needs_grade and needs_exp:
                        return "Podaj proszę **ocenę (2.0–5.0)** oraz **1–2 zdania uzasadnienia** w jednej wiadomości."
                    if needs_grade:
                        return "Podaj proszę **ocenę liczbową 2.0–5.0** + krótkie uzasadnienie (w jednej wiadomości)."
                    if needs_exp:
                        return "Dopisz proszę **1–2 zdania uzasadnienia** (razem z oceną w tej samej wiadomości)."
            return "Podaj proszę **ocenę (2.0–5.0)** oraz **krótkie uzasadnienie** (w jednej wiadomości)."

        if pending_state_key == "evaluate_project_grade":
            pid = pending_target.get("project_id") if pending_target else None
            incomplete = completion_status.get("project_assessments", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("project_id")) == str(pid):
                    needs_grade = not d.get("has_grade", False)
                    needs_exp = not d.get("has_explanation", False)
                    if needs_grade and needs_exp:
                        return "Podaj proszę **ocenę (2.0–5.0)** oraz **1–2 zdania uzasadnienia** w jednej wiadomości."
                    if needs_grade:
                        return "Podaj proszę **ocenę liczbową 2.0–5.0** + krótkie uzasadnienie (w jednej wiadomości)."
                    if needs_exp:
                        return "Dopisz proszę **1–2 zdania uzasadnienia** (razem z oceną w tej samej wiadomości)."
            return "Podaj proszę **ocenę (2.0–5.0)** oraz **krótkie uzasadnienie** (w jednej wiadomości)."

        if pending_state_key == "evaluate_leader_grade":
            det = completion_status.get("leadership_assessment", {})
            needs_grade = not det.get("has_grade", False)
            needs_exp = not det.get("has_explanation", False)
            if needs_grade and needs_exp:
                return "Podaj proszę **ocenę (2.0–5.0)** oraz **1–2 zdania uzasadnienia** (w jednej wiadomości)."
            if needs_grade:
                return "Podaj proszę **ocenę (2.0–5.0)** + krótkie uzasadnienie (w jednej wiadomości)."
            if needs_exp:
                return "Dopisz proszę **1–2 zdania uzasadnienia** (razem z oceną w tej samej wiadomości)."

        if pending_state_key == "evaluate_objectives":
            det = completion_status.get("objectives_assessment", {})
            needs_grade = not det.get("has_grade", False)
            needs_exp = not det.get("has_explanation", False)
            if needs_grade and needs_exp:
                return "Podaj proszę **ocenę (2.0–5.0)** oraz **1–2 zdania uzasadnienia** (w jednej wiadomości)."
            if needs_grade:
                return "Podaj proszę **ocenę (2.0–5.0)** + krótkie uzasadnienie (w jednej wiadomości)."
            if needs_exp:
                return "Dopisz proszę **1–2 zdania uzasadnienia** (razem z oceną w tej samej wiadomości)."

        if pending_state_key == "evaluate_assumption":
            assumption_id = pending_target.get("assumption_id") if pending_target else None
            incomplete = completion_status.get("assumption_evaluations", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("assumption_id")) == str(assumption_id):
                    needs_eval = not d.get("has_evaluation", False)
                    needs_exp = not d.get("has_explanation", False)
                    if needs_eval and needs_exp:
                        return "Podaj proszę **TAK lub NIE** (czy założenia są spełnione) oraz **1–2 zdania uzasadnienia**."
                    if needs_eval:
                        return "Podaj proszę jasną odpowiedź: **TAK** (spełnione) lub **NIE** (niespełnione) + krótkie uzasadnienie."
                    if needs_exp:
                        return "Dopisz proszę **1–2 zdania uzasadnienia** dlaczego założenia zostały/nie zostały spełnione."
            return "Podaj proszę **TAK lub NIE** (czy założenia są spełnione) oraz **krótkie uzasadnienie**."

        if pending_state_key == "masters_intent":
            # here we only need an answer + short reasoning, no numeric grade
            return "Napisz proszę **tak/nie** czy planujesz magisterkę i dodaj **1–2 zdania uzasadnienia**."

        if pending_state_key == "study_program_feedback":
            # here we only need feedback text
            return "Napisz proszę **1–3 zdania**: co Ci się podoba w programie studiów i/lub co byś zmienił(a)."

        return "Możesz doprecyzować odpowiedź? Odpowiedz proszę **konkretnie** (1–3 zdania), zgodnie z pytaniem."

    def _contextual_followup(pending_state_key: str, pending_target: dict | None, user_answer: str, completion_status: dict) -> str:
        """
        Human-friendly follow-up question based on user's last answer + what DB says is missing.
        Does NOT change state logic; only changes phrasing of clarification.
        """
        ua = (user_answer or "").strip()
        ua_low = ua.lower()

        def _self_missing():
            det = completion_status.get("self_assessment", {})
            return (not det.get("has_grade", False), not det.get("has_explanation", False))

        def _teammate_missing():
            idx = pending_target.get("index") if pending_target else None
            incomplete = completion_status.get("teammate_assessments", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("teammate_index")) == str(idx):
                    return (not d.get("has_grade", False), not d.get("has_explanation", False))
            return (True, True)

        def _project_missing():
            pid = pending_target.get("project_id") if pending_target else None
            incomplete = completion_status.get("project_assessments", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("project_id")) == str(pid):
                    return (not d.get("has_grade", False), not d.get("has_explanation", False))
            return (True, True)

        def _leader_missing():
            det = completion_status.get("leadership_assessment", {})
            return (not det.get("has_grade", False), not det.get("has_explanation", False))

        if pending_state_key == "self_evaluation":
            missing_grade, missing_exp = _self_missing()
            if missing_grade and missing_exp:
                return "OK — podaj proszę **ocenę (2.0–5.0)** oraz **1–2 zdania uzasadnienia** w jednej wiadomości."
            if missing_grade:
                return "Rozumiem. Podaj proszę jeszcze **konkretną ocenę 2.0–5.0** (np. 4.5)."
            if missing_exp:
                if any(x in ua_low for x in ["super", "świetn", "mega", "kozack", "git", "zajeb"]):
                    return "Brzmi mocno 🙂 Możesz rozwinąć **dlaczego** tak uważasz? Podaj 1–2 konkretne przykłady z projektu."
                return "Możesz dopisać **1–2 zdania uzasadnienia** i podać konkretne przykłady (co dokładnie zrobiłeś/aś)?"

        if pending_state_key == "evaluate_teammate_grade":
            missing_grade, missing_exp = _teammate_missing()
            name = ""
            if pending_target:
                name = f"{pending_target.get('name', '')} {pending_target.get('surname', '')}".strip()
            if missing_grade and missing_exp:
                return f"Jasne — podaj proszę **ocenę (2.0–5.0)** dla {name} oraz **krótkie uzasadnienie** (1–2 zdania)."
            if missing_grade:
                return f"Podaj proszę jeszcze samą **ocenę 2.0–5.0** dla {name}."
            if missing_exp:
                return f"Możesz krótko doprecyzować **dlaczego** taka ocena dla {name}? 1–2 konkretne przykłady."

        if pending_state_key == "evaluate_project_grade":
            missing_grade, missing_exp = _project_missing()
            pname = (pending_target.get("project_name") if pending_target else "") or "tego projektu"
            if missing_grade and missing_exp:
                return f"OK — podaj proszę **ocenę (2.0–5.0)** dla „{pname}” i **krótkie uzasadnienie** (1–2 zdania)."
            if missing_grade:
                return f"Podaj proszę jeszcze **ocenę 2.0–5.0** dla „{pname}”."
            if missing_exp:
                return f"Możesz dopisać **krótkie uzasadnienie** dla „{pname}”? Najlepiej 1–2 zdania (co działa / co nie)."

        if pending_state_key == "evaluate_leader_grade":
            missing_grade, missing_exp = _leader_missing()
            name = ""
            if pending_target:
                name = f"{pending_target.get('name', '')} {pending_target.get('surname', '')}".strip()
            if missing_grade and missing_exp:
                return f"OK — podaj proszę **ocenę (2.0–5.0)** dla lidera {name} i **krótkie uzasadnienie** (1–2 zdania)."
            if missing_grade:
                return f"Podaj proszę jeszcze **ocenę 2.0–5.0** dla lidera {name}."
            if missing_exp:
                return f"Możesz rozwinąć **dlaczego** taka ocena dla lidera {name}? Podaj 1–2 konkretne przykłady."

        if pending_state_key == "evaluate_assumption":
            def _assumption_missing():
                assumption_id = pending_target.get("assumption_id") if pending_target else None
                incomplete = completion_status.get("assumption_evaluations", {}).get("incomplete_details", []) or []
                for d in incomplete:
                    if str(d.get("assumption_id")) == str(assumption_id):
                        return (not d.get("has_evaluation", False), not d.get("has_explanation", False))
                return (True, True)
            
            missing_eval, missing_exp = _assumption_missing()
            assumption_name = (pending_target.get("name") if pending_target else "") or "założeń"
            if missing_eval and missing_exp:
                return f"OK - czy założenia '{assumption_name}' zostały spełnione? Podaj **TAK/NIE** i **krótkie uzasadnienie** (1-2 zdania)."
            if missing_eval:
                return f"Podaj proszę jasną odpowiedź: **TAK** (spełnione) lub **NIE** (niespełnione) dla '{assumption_name}'."
            if missing_exp:
                return f"Możesz dopisać **dlaczego** założenia '{assumption_name}' zostały/nie zostały spełnione? 1-2 konkretne przykłady.{pending_target.get("system_accepted")}"

        if pending_state_key == "masters_intent":
            # this state is NOT numeric; we just need an answer + short reason
            return "Odpowiedz proszę jasno: czy planujesz magisterkę (**tak/nie**) i dopisz krótko dlaczego (1–2 zdania)."

        if pending_state_key == "study_program_feedback":
            # this state is NOT numeric; we just need feedback
            if any(x in ua_low for x in ["nie mam", "brak", "wszystko ok", "w porzadku", "w porządku"]):
                return "OK — a czy jest coś, co **szczególnie** Ci się podoba (np. przedmiot / forma zajęć) albo co byś choć trochę usprawnił/a? 1–2 zdania."
            return "Możesz doprecyzować: **co byś zmienił/a** w programie studiów albo co najbardziej Ci się podoba? 1–3 zdania."

        return "Możesz doprecyzować odpowiedź? Odpowiedz proszę 1–3 zdaniami na pytanie."

    async def _build_verification_agent(mcp_server: MCPServerStreamableHttp, agent_name: str, prompt_name: str) -> Agent:

        p = await mcp_server.session.get_prompt(prompt_name)
        base_instructions = p.messages[0].content.text

        return Agent(
            name=agent_name,
            model="gpt-4o-mini",
            instructions=base_instructions.strip(),
            mcp_servers=[mcp_server],
            model_settings=ModelSettings(tool_choice="auto"),
        )

    async def _build_post_interview_chat_agent(mcp_server: MCPServerStreamableHttp) -> Agent:
        instructions = (
            "Wywiad został zakończony. Teraz prowadzisz luźny chitchat z użytkownikiem.\n"
            "- Odpowiadaj naturalnie, krótko i po ludzku.\n"
            "- Możesz nawiązywać do kontekstu rozmowy, ale NIE zmieniaj danych wywiadu w bazie.\n"
            f"- Jeśli użytkownik napisze dokładnie: {SAFE_WORD} (bez dodatkowych słów) -> zakończ rozmowę krótkim pożegnaniem.\n"
        )
        # IMPORTANT: no MCP servers here -> the model cannot call DB/tools during chit-chat.
        return Agent(
            name="PostInterviewChat",
            model="gpt-4o-mini",
            instructions=instructions.strip(),
        )

    async def _build_question_agent(
        mcp_server: MCPServerStreamableHttp,
        state: State,
        base_question: str,
        target: dict | None
    ) -> Agent:
        """
        Builds a QuestionAgent that uses the 'question_prompt' from MCP server
        to dynamically generate the question text to ask the user.
        """
        # Prepare the formatted question text with target info
        formatted_question = _render_question_text(state.name, base_question, target)
        if state.name in ["evaluate_teammate_grade","evaluate_leader_grade"] and target:
            target_text:str = f"{target.get('name','')} {target.get('surname','')}".strip()
        elif state.name == "evaluate_project_grade" and target:
            target_text:str  = f"{target.get('project_name','')}".strip()
        elif state.name == "evaluate_assumption" and target:
            target_text:str  = f"{target.get('description','')}".strip()
        else:
            target_text = ""

        # Fetch the question_prompt from MCP server with the question as argument
        p = await mcp_server.session.get_prompt(
            "question_prompt",
            {
                "question": formatted_question,
                "target": target_text
            }
        )
        base_instructions = p.messages[0].content.text

        return Agent(
            name=f"QuestionAgent/{state.name}",
            model="gpt-4o-mini",
            instructions=base_instructions.strip(),
            mcp_servers=[mcp_server],
            model_settings=ModelSettings(tool_choice="auto"),
        )

    async def _run_agent_text(agent: Agent, input_text: str, langfuse_client=None, pending_state: str | None = None) -> str:
        runner = Runner()
        result = runner.run_streamed(starting_agent=agent, input=input_text)

        out = []
        tool_calls = []  # Collect tool calls and their outputs
        current_tool_call = None

        async for ev in result.stream_events():
            if ev.type == "raw_response_event" and ev.data.type == "response.output_text.delta":
                out.append(ev.data.delta)

            elif ev.type == "run_item_stream_event":
                if ev.item.type == "tool_call_item":
                    # Start tracking a new tool call
                    current_tool_call = {
                        "name": getattr(ev.item, "tool_name", "unknown_tool"),
                        "input": ev.item.raw_item,
                        "output": None
                    }
                    tool_calls.append(current_tool_call)

                elif ev.item.type == "tool_call_output_item" and current_tool_call:
                    # Add output to the most recent tool call
                    current_tool_call["output"] = ev.item.raw_item.get("output", "")

        text = "".join(out).strip()
        if not text:
            try:
                text = (result.final_ or "").strip()
            except Exception:
                text = ""

        # Log to Langfuse
        if langfuse_client:
            try:
                # Determine generation name based on agent type and state
                agent_type = agent.name.split("/")[0] if "/" in agent.name else agent.name
                generation_name = f"{agent_type}/{pending_state}" if pending_state else agent_type

                # Use context manager to create generation observation
                with langfuse_client.start_as_current_observation(
                    as_type="generation",
                    name=generation_name,
                    model=agent.model,
                    metadata={"agent_name": agent.name, "pending_state": pending_state}
                ) as generation:
                    generation.update(
                        input=input_text,
                        output=text
                    )

                    # Log each tool call as a nested span
                    for tool_call in tool_calls:
                        try:
                            with langfuse_client.start_as_current_observation(
                                as_type="span",
                                name=f"tool/{tool_call['name']}"
                            ) as tool_span:
                                tool_span.update(
                                    input=tool_call["input"],
                                    output=tool_call["output"]
                                )
                        except Exception as e:
                            print(f"Failed to log tool call {tool_call['name']}: {e}")

                # Flush to ensure data is sent (important for short-lived requests)
                langfuse_client.flush()
            except Exception as e:
                print(f"Failed to log generation to Langfuse: {e}")

        return text

    async def _ask_initial_question(
        mcp_server: MCPServerStreamableHttp,
        session_id: str | None,
        user_id: int,
        state_key: str
    ) -> str:
        info_raw = _extract_tool_text(await mcp_server.session.call_tool("get_user_info_tool")) 
        info = _parse_maybe_json(info_raw) or {}
        if isinstance(info, dict) and not info.get("error"):
            q = (
                "Potwierdź proszę, że to Ty.\n\n"
                f"User {info.get('index', user_id)}: {info.get('name')} {info.get('surname')}\n"
                f"GitHub: {info.get('github')}\n"
                f"Project: {info.get('project_id')} ({info.get('project_name')})\n\n"
                "Odpowiedz: **tak** / **nie**."
            )
        else:
            q = (
                "Potwierdź proszę, że to Ty.\n\n"
                f"{info_raw}\n\n"
                "Odpowiedz: **tak** / **nie**."
            )

        if session_id:
            await mcp_server.session.call_tool( 
                "save_conversation_message_tool",
                arguments={
                    "session_id": session_id,
                    "role": "assistant",
                    "content": q,
                    "state_at_time": state_key,
                },
            )
        return q

    # ---------------------- endpoint ----------------------

    @app.route("/start_agent", methods=["POST"])
    async def start_agent(request: request.Request):
        # Initialize Langfuse
        langfuse = None
        try:
            langfuse = Langfuse(
                secret_key=os.environ.get('LANGFUSE_SECRET_KEY', ''),
                public_key=os.environ.get('LANGFUSE_PUBLIC_KEY', ''),
                host=os.environ.get('LANGFUSE_HOST', 'https://cloud.langfuse.com'),
                timeout=60,
            )
        except Exception as e:
            print(f"Failed to initialize Langfuse: {e}")

        try:
            data = request.json or {}
            print(f"Received data: {data}")

            user_id = data.get("user_id", 0)
            user_anwser = data.get("anwser", "No anwser for last question.")

            print(f"Connecting to MCP server at {MCP_SERVER_URL}/mcp...")

            mcp_server = MCPServerStreamableHttp(
                params=MCPServerStreamableHttpParams(
                    url=f"{MCP_SERVER_URL}/mcp",
                    headers={"user_id": str(user_id)},
                ),
                client_session_timeout_seconds=60.0,
                tool_filter=context_aware_filter,
            )
            await mcp_server.connect()
            print("MCP server connected successfully")

            # 1) Read session (DB is source of truth)
            state_tool_result = await mcp_server.session.call_tool("get_next_required_state_tool") 
            state_dict = _parse_maybe_json(_extract_tool_text(state_tool_result)) or {}

            session_id = state_dict.get("session_id")
            pending_state_key = state_dict.get("current_state_in_session", "initial")
            pending_target_json = state_dict.get("pending_target_json")
            pending_substate_json = state_dict.get("pending_substate_json")

            pending_target = None
            if pending_target_json:
                try:
                    pending_target = json.loads(pending_target_json)
                except Exception:
                    pending_target = _parse_maybe_json(pending_target_json)

            pending_substate = None
            if pending_substate_json:
                try:
                    pending_substate = json.loads(pending_substate_json)
                except Exception:
                    pending_substate = _parse_maybe_json(pending_substate_json)

            if pending_state_key not in AVAILABLE_STATES:
                pending_state_key = "initial"
            pending_state = AVAILABLE_STATES[pending_state_key]

            print(f"Pending state: {pending_state_key}")
            print(f"Pending target: {pending_target}")
            print(f"Pending substate: {pending_substate}")

            # Fetch conversation history once for reuse throughout the endpoint
            history_tool_result = await mcp_server.session.call_tool("get_conversation_context_tool")
            history_dict = _parse_maybe_json(_extract_tool_text(history_tool_result)) or {}
            history_messages = history_dict.get("messages", [])

                        # ---------------------- POST-INTERVIEW CHITCHAT MODE ----------------------
            # If interview is done (DB says "done"), keep chatting forever until SAFE_WORD.
            # IMPORTANT: persist "ended" flag in DB (pending_substate) so next requests won't restart chat.
            if pending_state_key == "done":

                # 0) If chat was already ended earlier -> always end (hard stop)
                if isinstance(pending_substate, dict) and pending_substate.get("type") == "chat_ended":
                    farewell = pending_substate.get("farewell") or "Dzięki za rozmowę i za udział w wywiadzie! 👋"
                    await mcp_server.cleanup()
                    return response.json(
                        {
                            "status": "completed",
                            "question": farewell,
                            "current_state": "done",
                            "next_state": "done",
                            "chat_mode": False,
                            "ended": True,
                        },
                        ensure_ascii=False,
                    )

                # 1) End conversation with safe word (persist in DB!)
                if _is_safe_word(user_anwser):
                    farewell = "Dzięki za rozmowę i za udział w wywiadzie! 👋"

                    # Save farewell + persist ended flag in DB so chat won't restart next turn
                    if session_id:
                        await mcp_server.session.call_tool( 
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": farewell,
                                "state_at_time": "done",
                            },
                        )
                        await mcp_server.session.call_tool( 
                            "update_session_state_tool",
                            arguments={
                                "new_state": "done",
                                "pending_target": None,
                                "pending_substate": {"type": "chat_ended", "farewell": farewell},
                            },
                        )

                    await mcp_server.cleanup()
                    return response.json(
                        {
                            "status": "completed",
                            "question": farewell,
                            "current_state": "done",
                            "next_state": "done",
                            "chat_mode": False,
                            "ended": True,
                        },
                        ensure_ascii=False,
                    )

                # 2) If no real answer -> show kickoff message
                has_real_answer = (user_anwser or "").strip() != "" and user_anwser != "No anwser for last question."
                if not has_real_answer:
                    kickoff = (
                        "Wywiad mamy już ogarnięty ✅\n\n"
                        "Możemy teraz pogadać luźno — o projekcie, studiach, planach, czymkolwiek.\n"
                        f"Żeby zakończyć definitywnie: wpisz **{SAFE_WORD}**."
                    )
                    if session_id:
                        await mcp_server.session.call_tool( 
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": kickoff,
                                "state_at_time": "done",
                            },
                        )
                    await mcp_server.cleanup()
                    return response.json(
                        {
                            "status": "completed",
                            "question": kickoff,
                            "current_state": "done",
                            "next_state": "done",
                            "chat_mode": True,
                        },
                        ensure_ascii=False,
                    )

                # 3) Save user message (as chat)
                if session_id:
                    await mcp_server.session.call_tool(
                        "save_conversation_message_tool",
                        arguments={
                            "session_id": session_id,
                            "role": "user",
                            "content": user_anwser,
                            "state_at_time": "done",
                        },
                    )
                    # Append to local history for consistency
                    history_messages.append({
                        "role": "user",
                        "content": user_anwser,
                        "state_at_time": "done",
                    })

                # 4) Generate chat reply (no DB writes except conversation log)
                chat_agent = await _build_post_interview_chat_agent(mcp_server)

                chat_input = (
                    f"HISTORIA (skrócona): {history_messages[-12:]}\n"
                    f"UŻYTKOWNIK: {user_anwser}\n"
                )
                chat_reply = await _run_agent_text(chat_agent, chat_input, langfuse_client=langfuse, pending_state="done")
                if not chat_reply:
                    chat_reply = "Jasne — o czym chcesz pogadać?"

                if session_id:
                    await mcp_server.session.call_tool( 
                        "save_conversation_message_tool",
                        arguments={
                            "session_id": session_id,
                            "role": "assistant",
                            "content": chat_reply,
                            "state_at_time": "done",
                        },
                    )

                await mcp_server.cleanup()
                return response.json(
                    {
                        "status": "completed",
                        "question": chat_reply,
                        "current_state": "done",
                        "next_state": "done",
                        "chat_mode": True,
                    },
                    ensure_ascii=False,
                )
            # -------------------- END POST-INTERVIEW CHITCHAT MODE --------------------


            # 2) Ensure target exists for target states
            if _needs_target(pending_state_key) and not pending_target:
                pending_target = await _compute_target_for_state(mcp_server, pending_state_key)
                await mcp_server.session.call_tool( 
                    "update_session_state_tool",
                    arguments={"new_state": pending_state_key, "pending_target": pending_target},
                )
                print(f"Persisted pending target for {pending_state_key}: {pending_target}")
        
            # 3) If no real answer -> ask pending question (DB-driven)
            has_real_answer = (user_anwser or "").strip() != "" and user_anwser != "No anwser for last question."
            if not has_real_answer:

                # --- 3B) SUBSTATE: outlier followup ---
                if isinstance(pending_substate, dict) and pending_substate.get("type") == "outlier_followup":
                    q = pending_substate.get("question")

                    if not q:
                        # fallback if question missing
                        if pending_state_key == "evaluate_teammate_grade" and pending_target and pending_target.get("index"):
                            r = await mcp_server.session.call_tool( 
                                "check_teammate_outlier_tool",
                                arguments={"graded_person_index": str(pending_target["index"])}
                            )
                            out = _parse_maybe_json(_extract_tool_text(r)) or {}
                            q = out.get("followup_question") or "Możesz doprecyzować uzasadnienie tej oceny (1–2 przykłady)?"
                        else:
                            q = "Możesz doprecyzować uzasadnienie tej oceny (1–2 przykłady)?"

                    final_q = q

                    if session_id:
                        await mcp_server.session.call_tool( 
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": final_q,
                                "state_at_time": pending_state_key,
                            },
                        )

                    await mcp_server.cleanup()
                    return response.json(
                        {
                            "status": "completed",
                            "question": final_q,
                            "current_state": pending_state_key,
                            "next_state": pending_state_key,
                        },
                        ensure_ascii=False,
                    )
                # --- END SUBSTATE ---

                # --- 3C) SUBSTATE: assumption ground truth followup ---
                if isinstance(pending_substate, dict) and pending_substate.get("type") == "assumption_ground_truth_followup":
                    q = pending_substate.get("question")

                    if not q:
                        # fallback if question missing
                        r = await mcp_server.session.call_tool( 
                            "check_assumption_evaluation_consensus_tool",
                            arguments={"min_evaluations": 1}
                        )
                        out = _parse_maybe_json(_extract_tool_text(r)) or {}
                        q = out.get("followup_question") or "Możesz doprecyzować uzasadnienie tej oceny założeń? Dlaczego Twoja ocena różni się od faktycznego stanu projektu?"

                    final_q = q

                    if session_id:
                        await mcp_server.session.call_tool( 
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": final_q,
                                "state_at_time": pending_state_key,
                            },
                        )

                    await mcp_server.cleanup()
                    return response.json(
                        {
                            "status": "completed",
                            "question": final_q,
                            "current_state": pending_state_key,
                            "next_state": pending_state_key,
                        },
                        ensure_ascii=False,
                    )
                # --- END ASSUMPTION SUBSTATE ---

                # normal question path (no substate)
                if pending_state_key == "initial":
                    final_q = await _ask_initial_question(mcp_server, session_id, user_id, pending_state_key)
                elif pending_state_key == "done":
                    # Instead of a goodbye message, start the open-ended post-interview chat.
                    final_q = (
                        "✅ Wywiad jest już ukończony. Możemy teraz pogadać o czymkolwiek 🙂\n"
                        f"Jeśli chcesz zakończyć rozmowę i dostać podsumowanie/pożegnanie, wpisz: **{SAFE_WORD}**."
                    )
                    if session_id:
                        await mcp_server.session.call_tool( 
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": final_q,
                                "state_at_time": pending_state_key,
                            },
                        )
                else:
                    # Use QuestionAgent to dynamically generate the question
                    question_agent = await _build_question_agent(
                        mcp_server=mcp_server,
                        state=pending_state,
                        base_question=pending_state.question,
                        target=pending_target
                    )
                    question_input = (
                        f"HISTORIA: {history_messages}\n"
                        f"Wygeneruj pytanie dla użytkownika."
                    )
                    final_q = await _run_agent_text(
                        question_agent,
                        question_input,
                        langfuse_client=langfuse,
                        pending_state=pending_state_key
                    )
                    if session_id:
                        await mcp_server.session.call_tool( 
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": final_q,
                                "state_at_time": pending_state_key,
                            },
                        )

                await mcp_server.cleanup()
                return response.json(
                    {
                        "status": "completed",
                        "question": final_q,
                        "current_state": pending_state_key,
                        "next_state": pending_state_key,
                    },
                    ensure_ascii=False,
                )

            # 4) Save user's message as response to pending state
            if session_id:
                await mcp_server.session.call_tool(
                    "save_conversation_message_tool",
                    arguments={
                        "session_id": session_id,
                        "role": "user",
                        "content": user_anwser,
                        "state_at_time": pending_state_key,
                    },
                )
                # Append to local history so verification/question agents have the latest context
                history_messages.append({
                    "role": "user",
                    "content": user_anwser,
                    "state_at_time": pending_state_key,
                })

            # -------- 4C) If we are answering an outlier followup, append it and clear substate --------
            saved = False
            verify_text = ""
            skip_verification = False
            completion_status = {}

            if isinstance(pending_substate, dict) and pending_substate.get("type") == "outlier_followup":
                if pending_state_key == "evaluate_teammate_grade" and pending_target and pending_target.get("index"):
                    await mcp_server.session.call_tool( 
                        "append_teammate_outlier_followup_tool",
                        arguments={
                            "graded_person_index": str(pending_target["index"]),
                            "followup": user_anwser,
                        },
                    )

                # clear substate, keep same state/target
                await mcp_server.session.call_tool( 
                    "update_session_state_tool",
                    arguments={
                        "new_state": pending_state_key,
                        "pending_target": pending_target,
                        "pending_substate": None,
                    },
                )

                # Treat as saved and skip normal verification
                saved = True
                verify_text = ""
                skip_verification = True

            # -------- 4D) If we are answering an assumption ground truth followup, save the followup and clear substate --------
            skip_assumption_gate = False
            if isinstance(pending_substate, dict) and pending_substate.get("type") == "assumption_ground_truth_followup":
                if pending_state_key == "evaluate_assumption" and pending_target and pending_target.get("assumption_id"):
                    await mcp_server.session.call_tool( 
                        "append_assumption_evaluation_followup_tool",
                        arguments={
                            "assumption_id": str(pending_target["assumption_id"]),
                            "followup": user_anwser,
                        },
                    )

                # clear substate, keep same state/target
                await mcp_server.session.call_tool( 
                    "update_session_state_tool",
                    arguments={
                        "new_state": pending_state_key,
                        "pending_target": pending_target,
                        "pending_substate": None,
                    },
                )

                # Treat as saved and skip normal verification
                saved = True
                verify_text = ""
                skip_verification = True
                skip_assumption_gate = True  # Don't re-trigger the gate after answering followup

            # 5) Verify + SAVE (verification tools write to DB)  [only if not skip_verification]
            if not skip_verification:
                if pending_state_key == "initial":
                    saved = _is_yes(user_anwser)
                    if not saved:
                        verify_text = (
                            "Według bazy tożsamość nie została potwierdzona.\n"
                            "Jeśli to Ty, wpisz: **tak**.\n"
                            "Jeśli to nie Ty, wpisz: **nie** (i uruchom rozmowę ponownie z poprawnym user_id)."
                        )
                else:
                    verify_prompt_name = pending_state.verification_prompt_name
                    if not verify_prompt_name:
                        saved = False
                        verify_text = "Brakuje prompta weryfikacyjnego dla tego stanu — nie mogę zapisać odpowiedzi."
                    else:
                        v_agent = await _build_verification_agent(
                            mcp_server=mcp_server,
                            agent_name=f"VerificationAgent/{pending_state_key}",
                            prompt_name=verify_prompt_name,
                        )

                        verify_input = (
                            f"HISTORIA: {history_messages}\n"
                            f"PENDING_STATE: {pending_state_key}\n"
                            f"PENDING_TARGET: {pending_target}\n"
                            f"ODPOWIEDŹ_UŻYTKOWNIKA: {user_anwser}\n"
                        )
                        print(f"Input to verification agent:\n{verify_input}")
                        verify_text = await _run_agent_text(v_agent, verify_input, langfuse_client=langfuse, pending_state=pending_state_key)

                        # DB-first: check completion after verifier runs
                        saved, completion_status = await _is_pending_state_completed(mcp_server, pending_state_key, pending_target)

                        # If not saved, append DB-derived precise hint to LLM response
                        if not saved:
                            hint = _contextual_followup(
                                pending_state_key,
                                pending_target or {},
                                user_anwser,
                                completion_status
                            )

                            if not (verify_text or "").strip():
                                verify_text = hint
                            else:
                                # Always append hint to provide clear guidance alongside LLM response
                                verify_text = f"{verify_text.strip()}\n\n{hint}"

            # 6) If not saved -> clarification, keep same state/target
            if not saved:
                final_q = (verify_text or "").strip()
                if not final_q:
                    final_q = _missing_info_hint(pending_state_key, pending_target or {}, completion_status)

                if session_id:
                    await mcp_server.session.call_tool( 
                        "save_conversation_message_tool",
                        arguments={
                            "session_id": session_id,
                            "role": "assistant",
                            "content": final_q,
                            "state_at_time": pending_state_key,
                        },
                    )

                await mcp_server.cleanup()
                return response.json(
                    {
                        "status": "completed",
                        "question": final_q,
                        "current_state": pending_state_key,
                        "next_state": pending_state_key,
                    },
                    ensure_ascii=False,
                )

            # -------- OUTLIER GATE (substate between states) --------
            if pending_state_key == "evaluate_teammate_grade" and pending_target and pending_target.get("index"):
                r = await mcp_server.session.call_tool( 
                    "check_teammate_outlier_tool",
                    arguments={
                        "graded_person_index": str(pending_target["index"]),
                        "threshold": 1.0,
                        "min_peers": 1,  # dla testów
                    },
                )
                out = _parse_maybe_json(_extract_tool_text(r)) or {}
                if out.get("eligible") and out.get("is_outlier") and out.get("followup_question"):
                    sub = {"type": "outlier_followup", "question": out["followup_question"]}
                    await mcp_server.session.call_tool( 
                        "update_session_state_tool",
                        arguments={
                            "new_state": pending_state_key,
                            "pending_target": pending_target,
                            "pending_substate": sub,
                        },
                    )

                    final_q = out["followup_question"]
                    if session_id:
                        await mcp_server.session.call_tool( 
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": final_q,
                                "state_at_time": pending_state_key,
                            },
                        )

                    await mcp_server.cleanup()
                    return response.json(
                        {
                            "status": "completed",
                            "question": final_q,
                            "current_state": pending_state_key,
                            "next_state": pending_state_key,
                        },
                        ensure_ascii=False,
                    )
            # -------- END OUTLIER GATE --------

            # -------- ASSUMPTION GROUND TRUTH GATE (substate between states) --------
            # Check if user's assumption evaluations differ from actual project assumption fulfillment status
            if pending_state_key == "evaluate_assumption" and not skip_assumption_gate:
                r = await mcp_server.session.call_tool( 
                    "check_assumption_evaluation_consensus_tool",
                    arguments={
                        "min_evaluations": 1,  # need at least 1 evaluation to check
                    },
                )
                out = _parse_maybe_json(_extract_tool_text(r)) or {}
                if out.get("eligible") and out.get("is_outlier") and out.get("followup_question"):
                    sub = {"type": "assumption_ground_truth_followup", "question": out["followup_question"], "mismatches": out.get("mismatches", [])}
                    await mcp_server.session.call_tool( 
                        "update_session_state_tool",
                        arguments={
                            "new_state": pending_state_key,
                            "pending_target": pending_target,
                            "pending_substate": sub,
                        },
                    )

                    final_q = out["followup_question"]
                    if session_id:
                        await mcp_server.session.call_tool( 
                            "save_conversation_message_tool",
                            arguments={
                                "session_id": session_id,
                                "role": "assistant",
                                "content": final_q,
                                "state_at_time": pending_state_key,
                            },
                        )

                    await mcp_server.cleanup()
                    return response.json(
                        {
                            "status": "completed",
                            "question": final_q,
                            "current_state": pending_state_key,
                            "next_state": pending_state_key,
                        },
                        ensure_ascii=False,
                    )
            # -------- END ASSUMPTION GROUND TRUTH GATE --------

            # 7) Saved -> compute next required state from DB, set as new pending, compute target, ask next
            next_state_result = await mcp_server.session.call_tool("get_next_required_state_tool") 
            next_state_dict = _parse_maybe_json(_extract_tool_text(next_state_result)) or {}
            next_state_key = next_state_dict.get("next_state", pending_state_key)

            if next_state_key not in AVAILABLE_STATES:
                next_state_key = pending_state_key
            next_state = AVAILABLE_STATES[next_state_key]

            next_target = None
            if _needs_target(next_state_key):
                next_target = await _compute_target_for_state(mcp_server, next_state_key)

            await mcp_server.session.call_tool( 
                "update_session_state_tool",
                arguments={
                    "new_state": next_state_key,
                    "pending_target": next_target,
                    "pending_substate": None,
                },
            )

            if next_state_key == "initial":
                final_q = await _ask_initial_question(mcp_server, session_id, user_id, next_state_key)

            elif next_state_key == "done":
                # Do NOT end — switch to chat kickoff (handled at top next turn)
                final_q = (
                    "Wywiad mamy już ogarnięty ✅\n\n"
                    "Możemy teraz pogadać luźno — o projekcie, studiach, planach, czymkolwiek.\n"
                    f"Żeby zakończyć definitywnie: wpisz **{SAFE_WORD}**."
                )
                if session_id:
                    await mcp_server.session.call_tool( 
                        "save_conversation_message_tool",
                        arguments={
                            "session_id": session_id,
                            "role": "assistant",
                            "content": final_q,
                            "state_at_time": "done",
                        },
                    )

            else:
                # Use QuestionAgent to dynamically generate the question
                question_agent = await _build_question_agent(
                    mcp_server=mcp_server,
                    state=next_state,
                    base_question=next_state.question,
                    target=next_target
                )
                question_input = (
                    f"HISTORIA: {history_messages}\n"
                    f"Wygeneruj pytanie dla użytkownika."
                )
                final_q = await _run_agent_text(
                    question_agent,
                    question_input,
                    langfuse_client=langfuse,
                    pending_state=next_state_key
                )
                if session_id:
                    await mcp_server.session.call_tool(  
                        "save_conversation_message_tool",
                        arguments={
                            "session_id": session_id,
                            "role": "assistant",
                            "content": final_q,
                            "state_at_time": next_state_key,
                        },
                    )

            await mcp_server.cleanup()
            return response.json(
                {
                    "status": "completed",
                    "question": final_q,
                    "current_state": next_state_key,
                    "next_state": next_state_key,
                    "chat_mode": (next_state_key == "done"),
                },
                ensure_ascii=False,
            )

        except Exception as e:
            print(f"ERROR in start_agent endpoint: {e}")
            traceback.print_exc()
            return response.json(
                {"status": "error", "error": str(e), "traceback": traceback.format_exc()},
                status=500,
            )

    return app
