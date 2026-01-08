from agents import Agent, Runner, ModelSettings
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from sanic import Sanic, response, request
from .states import AVAILABLE_STATES
from .utils import context_aware_filter
from langfuse import Langfuse
import json
import os
import ast
import traceback

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:10000")


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
        return state_key in ("evaluate_teammate_grade", "evaluate_project_grade", "evaluate_leader_grade")

    async def _compute_target_for_state(mcp_server: MCPServerStreamableHttp, state_key: str):
        """
        Picks the pending target for states that need it.
        IMPORTANT: relies on server tools returning JSON strings:
          - get_random_ungraded_member_tool -> dict or null
          - get_ungraded_projects_tool -> list[dict]
          - get_leader_info_tool -> dict
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

        return base_question

    def _is_yes(text: str) -> bool:
        t = (text or "").strip().lower()
        return (
            t in ("tak", "t", "yes", "y", "ok", "potwierdzam", "zgadza się", "zgadza sie", "to ja", "zgadza")
            or "tak" in t
        )

    async def _get_completion_status(mcp_server: MCPServerStreamableHttp) -> dict:
        r = await mcp_server.session.call_tool("get_student_completion_status_tool")
        parsed = _parse_maybe_json(_extract_tool_text(r))
        return parsed if isinstance(parsed, dict) else {}

    async def _is_pending_state_completed(mcp_server: MCPServerStreamableHttp, pending_state_key: str, pending_target: dict | None) -> bool:
        """
        DB-first completion check for the *pending* item.
        This prevents loops when model replied but tools didn't persist.
        """
        st = await _get_completion_status(mcp_server)

        if pending_state_key == "self_evaluation":
            return bool(st.get("self_assessment", {}).get("is_complete"))

        if pending_state_key == "evaluate_teammate_grade":
            if not pending_target or not pending_target.get("index"):
                return False
            tgt = str(pending_target.get("index"))
            incomplete = st.get("teammate_assessments", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("teammate_index")) == tgt:
                    return bool(d.get("has_grade")) and bool(d.get("has_explanation"))
            # not listed as incomplete => treat as complete
            return True

        if pending_state_key == "evaluate_project_grade":
            if not pending_target or not pending_target.get("project_id"):
                return False
            tgt = str(pending_target.get("project_id"))
            incomplete = st.get("project_assessments", {}).get("incomplete_details", []) or []
            for d in incomplete:
                if str(d.get("project_id")) == tgt:
                    return bool(d.get("has_grade")) and bool(d.get("has_explanation"))
            return True

        if pending_state_key == "evaluate_leader_grade":
            return bool(st.get("leadership_assessment", {}).get("is_complete"))

        if pending_state_key == "evaluate_objectives":
            return bool(st.get("objectives_assessment", {}).get("is_complete"))

        if pending_state_key == "masters_intent":
            return bool(st.get("masters_intent", {}).get("is_complete"))

        if pending_state_key == "study_program_feedback":
            return bool(st.get("study_program_feedback", {}).get("is_complete"))

        return False

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

        return "Podaj proszę brakujące informacje: **ocena 2.0–5.0** oraz **krótkie uzasadnienie** (w jednej wiadomości)."

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

    async def _run_agent_text(agent: Agent, input_text: str) -> str:
        runner = Runner()
        result = runner.run_streamed(starting_agent=agent, input=input_text)

        out = []
        async for ev in result.stream_events():
            if ev.type == "raw_response_event" and ev.data.type == "response.output_text.delta":
                out.append(ev.data.delta)

        text = "".join(out).strip()
        if not text:
            try:
                text = (result.final_ or "").strip()
            except Exception:
                text = ""
        return text

    async def _ask_initial_question(mcp_server: MCPServerStreamableHttp, session_id: str | None, user_id: int, state_key: str) -> str:
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

            pending_target = None
            if pending_target_json:
                try:
                    pending_target = json.loads(pending_target_json)
                except Exception:
                    pending_target = _parse_maybe_json(pending_target_json)

            if pending_state_key not in AVAILABLE_STATES:
                pending_state_key = "initial"
            pending_state = AVAILABLE_STATES[pending_state_key]

            print(f"Pending state: {pending_state_key}")
            print(f"Pending target: {pending_target}")

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
                if pending_state_key == "initial":
                    final_q = await _ask_initial_question(mcp_server, session_id, user_id, pending_state_key)
                elif pending_state_key == "done":
                    final_q = pending_state.question
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
                    final_q = _render_question_text(pending_state_key, pending_state.question, pending_target)
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

            # 5) Verify + SAVE (verification tools write to DB)
            saved = False
            verify_text = ""

            if pending_state_key == "initial":
                saved = _is_yes(user_anwser)
                if not saved:
                    verify_text = (
                        "Według bazy tożsamość nie została potwierdzona.\n"
                        "Jeśli to Ty, wpisz: **tak**.\n"
                        "Jeśli to nie Ty, wpisz: **nie** (i uruchom rozmowę ponownie z poprawnym user_id)."
                    )
            elif pending_state_key == "done":
                saved = True
                verify_text = ""
            else:
                verify_prompt_name = pending_state.verification_prompt_name
                if not verify_prompt_name:
                    saved = False
                    verify_text = "Brakuje prompta weryfikacyjnego dla tego stanu — nie mogę zapisać odpowiedzi."
                else:
                    history_tool_result = await mcp_server.session.call_tool("get_conversation_context_tool")
                    history_dict = _parse_maybe_json(_extract_tool_text(history_tool_result)) or {}
                    history_messages = history_dict.get("messages", [])

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
                    verify_text = await _run_agent_text(v_agent, verify_input)

                    # DB-first: check completion after verifier runs
                    saved = await _is_pending_state_completed(mcp_server, pending_state_key, pending_target)

                    # If not saved, add DB-derived precise hint
                    if not saved:
                        completion_status = await _get_completion_status(mcp_server)
                        hint = _missing_info_hint(pending_state_key, pending_target or {}, completion_status)
                        if not (verify_text or "").strip():
                            verify_text = hint
                        else:
                            low = verify_text.lower()
                            if ("doprecyz" in low) or ("brakuje" in low):
                                verify_text = f"{verify_text.strip()}\n\n{hint}"

            # 6) If not saved -> clarification, keep same state/target
            if not saved:
                final_q = (verify_text or "").strip()
                if not final_q:
                    completion_status = await _get_completion_status(mcp_server)
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
                arguments={"new_state": next_state_key, "pending_target": next_target},
            )

            if next_state_key == "initial":
                final_q = await _ask_initial_question(mcp_server, session_id, user_id, next_state_key)
            elif next_state_key == "done":
                final_q = next_state.question
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
            else:
                final_q = _render_question_text(next_state_key, next_state.question, next_target)
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
