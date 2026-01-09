from .. import MCP_SERVER
from .models import (
    NameEntity, Message,
    GetProjectGradesRequest, GetMemberGradesRequest, IsLeaderRequest,
    GetProjectMembersRequest, GetUserInfoRequest, HasGradedAllMembersRequest,
    GetUngradedMembersRequest, HasGradedAllProjectsRequest, GetUngradedProjectsRequest,
    GetStudentCompletionStatusRequest, IdentifyTeammateByNameRequest,
    SetSelfGradeRequest, SetTeammateGradeRequest, SetLeaderGradeRequest,
    SetProjectGradeRequest, SetProjectObjectivesGradeRequest,
    SetOpenAnswerRequest,
)
from starlette.requests import Request
from fastmcp.server.dependencies import get_http_request
from ..neo4j_retriever import Neo4jRetriever
import json

# 🔥 MOCKUP DATABASE - WSZYSTKO W PAMIĘCI
MOCK_STUDENTS = {
    "2001": {"name": "Jan", "surname": "Kowalski", "index": "2001", "project_id": "1", "project_name": "System zarządzania zadaniami", "role": "leader"},
    "2002": {"name": "Anna", "surname": "Nowak", "index": "2002", "project_id": "1", "project_name": "System zarządzania zadaniami", "role": "member"},
    "2003": {"name": "Piotr", "surname": "Wiśniewski", "index": "2003", "project_id": "1", "project_name": "System zarządzania zadaniami", "role": "member"},
    "2004": {"name": "Maria", "surname": "Kowalczyk", "index": "2004", "project_id": "1", "project_name": "System zarządzania zadaniami", "role": "member"},
    "2005": {"name": "Tomasz", "surname": "Kamiński", "index": "2005", "project_id": "1", "project_name": "System zarządzania zadaniami", "role": "member"},
    "2006": {"name": "Katarzyna", "surname": "Lewandowska", "index": "2006", "project_id": "2", "project_name": "Aplikacja do nauki języków", "role": "leader"},
    "2007": {"name": "Michał", "surname": "Zieliński", "index": "2007", "project_id": "2", "project_name": "Aplikacja do nauki języków", "role": "member"},
    "2008": {"name": "Magdalena", "surname": "Szymańska", "index": "2008", "project_id": "2", "project_name": "Aplikacja do nauki języków", "role": "member"},
    "2009": {"name": "Jakub", "surname": "Woźniak", "index": "2009", "project_id": "2", "project_name": "Aplikacja do nauki języków", "role": "member"},
    "2010": {"name": "Alicja", "surname": "Dąbrowska", "index": "2010", "project_id": "2", "project_name": "Aplikacja do nauki języków", "role": "member"},
}

MOCK_GRADES = {
    "self": {},  # {student_index: {"grade": 4.5, "description": "..."}}
    "teammate": {},  # {f"{grader_index}_{graded_index}": {"grade": 4.0, "description": "..."}}
    "leader": {},  # {f"{grader_index}_{project_id}": {"grade": 4.0, "description": "..."}}
    "project": {},  # {f"{grader_index}_{project_id}": {"grade": 4.0, "description": "..."}}
    "objectives": {},  # {f"{grader_index}_{project_id}": {"grade": 4.0, "description": "..."}}
}


#     _   ____________  __ __  _      __              __    
#    / | / / ____/ __ \/ // / (_)    / /_____  ____  / /____
#   /  |/ / __/ / / / / // /_/ /    / __/ __ \/ __ \/ / ___/
#  / /|  / /___/ /_/ /__  __/ /    / /_/ /_/ / /_/ / (__  ) 
# /_/ |_/_____/\____/  /_/_/ /     \__/\____/\____/_/____/  
#                       /___/                               

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------GET METHOD TOOLS----------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@MCP_SERVER.tool(
    name="get_project_grades_tool",
    description="Narzędzie pobierające wszystkie oceny dla danego projektu z informacją czy oceniający był członkiem projektu.",
    tags=set(['retrieval', 'grades', 'project']),
)
async def get_project_grades_tool(param: GetProjectGradesRequest) -> str:
    """
    Pobiera oceny projektu wraz z informacją o członkostwie oceniającego.
    """
    try:
        
        retriever = Neo4jRetriever()
        request = get_http_request()
        project_id = request.headers.get("project_id")
        data = param.model_dump()
        
        grades = retriever.get_project_grades(project_id=data['project_id'])
        retriever.close()
        
        if not grades:
            return f"No grades found for project {data['project_id']}"
        
        result = f"Grades for project {data['project_id']}:\n"
        for grade_info in grades:
            member_status = "Member" if grade_info['was_member'] else "Non-member"
            result += f"- Grade: {grade_info['grade']} by {grade_info['grader_index']} ({member_status})\n"
            result += f"  Explanation: {grade_info['explanation']}\n"
        
        return result
    except Exception as e:
        return f"ERROR: {str(e)}"

@MCP_SERVER.tool(
    name="get_member_grades_tool",
    description="Pobiera oceny dla wskazanego członka zespołu z rozróżnieniem, czy oceniający był liderem.",
    tags=set(['retrieval', 'grades', 'member']),
)
async def get_member_grades_tool(param: GetMemberGradesRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        grades = retriever.get_member_grades(index=param.index)
        retriever.close()

        if not grades:
            return f"No grades found for member {param.index}"

        result = [f"Grades for member {param.index}:"]
        for g in grades:
            leader = "LEADER" if g['is_leader'] else "member"
            result.append(f"- {g['grader_index']} ({leader}) -> {g['grade']}")
            result.append(f"  Explanation: {g['explanation']}")
        return "\n".join(result)
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="is_leader_tool",
    description="Sprawdza, czy student jest liderem projektu.",
    tags=set(['retrieval', 'role']),
)
async def is_leader_tool(param: IsLeaderRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        flag = retriever.is_leader(index=param.index)
        retriever.close()
        return "TRUE" if flag else "FALSE"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="get_project_members_tool",
    description="Zwraca indeksy członków projektu.",
    tags=set(['retrieval', 'project']),
)
async def get_project_members_tool(param: GetProjectMembersRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        members = retriever.get_project_members(project_id=param.project_id)
        retriever.close()
        return f"Members of project {param.project_id}: {members}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="get_user_info_tool",
    description="Pobiera info o użytkowniku.",
    tags=set(['retrieval']),
)
async def get_user_info_tool() -> str:
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return json.dumps({"error": "'user_id' header not found"}, ensure_ascii=False)

        info = retriever.get_user_info(index=user_index)
        retriever.close()

        if not info:
            return json.dumps({"error": f"No user found for index {user_index}"}, ensure_ascii=False)

        
        payload = {
            "index": user_index,
            "name": info.get("name"),
            "surname": info.get("surname"),
            "github": info.get("github"),
            "project_id": info.get("project_id"),
            "project_name": info.get("project_name"),
        }
        return json.dumps(payload, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)



@MCP_SERVER.tool(
    name="has_graded_all_members_tool",
    description="Sprawdza, czy użytkownik ocenił wszystkich członków zespołu.",
    tags=set(['retrieval', 'progress']),
)
async def has_graded_all_members_tool(param: HasGradedAllMembersRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        flag = retriever.has_graded_all_members(index=param.index)
        retriever.close()
        return "TRUE" if flag else "FALSE"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="get_ungraded_members_tool",
    description="Zwraca listę nieocenionych kolegów z zespołu.",
    tags=set(['retrieval', 'progress']),
)
async def get_ungraded_members_tool() -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_index' header not found"
        retriever = Neo4jRetriever()
        lst = retriever.get_ungraded_members(index=user_index)
        retriever.close()
        return f"Ungraded teammates for {user_index}: {lst}"
    except Exception as e:
        return f"ERROR: {str(e)}"
    
@MCP_SERVER.tool(
    name="get_random_ungraded_member_tool",
    description="Zwraca (deterministycznie) kolejnego nieocenionego członka zespołu.",
    tags=set(['retrieval', 'progress']),
)
async def get_random_ungraded_member_tool() -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return json.dumps({"error": "'user_id' header not found"}, ensure_ascii=False)

        retriever = Neo4jRetriever()
        member = retriever.get_random_ungraded_member(index=user_index)
        retriever.close()

        # Zwracamy JSON: dict albo null
        return json.dumps(member, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@MCP_SERVER.tool(
    name="has_graded_all_projects_tool",
    description="Sprawdza, czy użytkownik ocenił wszystkie projekty.",
    tags=set(['retrieval', 'progress']),
)
async def has_graded_all_projects_tool() -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_index' header not found"
        retriever = Neo4jRetriever()
        flag = retriever.has_graded_all_projects(index=user_index)
        retriever.close()
        return "TRUE" if flag else "FALSE"
    except Exception as e:
        return f"ERROR: {str(e)}"

@MCP_SERVER.tool(
    name="get_leader_info_tool",
    description="Zwraca dane lidera projektu użytkownika oraz project_id potrzebny do zapisania oceny.",
    tags=set(['retrieval', 'role']),
)
async def get_leader_info_tool() -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return json.dumps({"error": "'user_id' header not found"}, ensure_ascii=False)

        retriever = Neo4jRetriever()
        leader_data = retriever.get_leader_of_student(index=user_index)
        retriever.close()

        return json.dumps(leader_data, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@MCP_SERVER.tool(
    name="get_ungraded_projects_tool",
    description="Zwraca listę nieocenionych projektów.",
    tags=set(['retrieval', 'progress']),
)
async def get_ungraded_projects_tool() -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return json.dumps({"error": "'user_id' header not found"}, ensure_ascii=False)

        retriever = Neo4jRetriever()
        lst = retriever.get_ungraded_projects(index=user_index)
        retriever.close()

        return json.dumps(lst, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)



@MCP_SERVER.tool(
    name="get_student_completion_status_tool",
    description="Zwraca status kompletności.",
    tags=set(['retrieval']),
)
async def get_student_completion_status_tool() -> str:
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_index' header not found"
        status = retriever.get_student_completion_status(index=user_index)
        retriever.close()
        return str(status)
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="get_next_required_state_tool",
    description="Determines the next required conversation state based on the student's completion status. Returns the state name, reason, contextual details, and last_state from the session.",
    tags=set(['retrieval', 'state', 'workflow']),
)
async def get_next_required_state_tool() -> dict:
    """
    Determines the next state based on what assessments are incomplete.
    Uses completion status to intelligently determine workflow progression.
    Also returns the last_state from the conversation session for verification purposes.
    """
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return {"error": "'user_id' header not found"}

        next_state_info = retriever.get_next_required_state(student_index=user_index)

        # Also get the session to retrieve last_state and current state
        session = retriever.get_or_create_session(student_index=user_index)
        if session:
            next_state_info["last_state"] = session.get("last_state")
            next_state_info["session_id"] = session.get("session_id")
            next_state_info["current_state_in_session"] = session.get("current_state")
            next_state_info["pending_target_json"] = session.get("pending_target_json")
            next_state_info["pending_substate_json"] = session.get("pending_substate_json")

        else:
            next_state_info["last_state"] = None
            next_state_info["session_id"] = None
            next_state_info["current_state_in_session"] = None
            next_state_info["pending_target_json"] = None
            next_state_info["pending_substate_json"] = None



        # Rename 'state' to 'next_state' for clarity (it represents the next required state)
        if "state" in next_state_info:
            next_state_info["next_state"] = next_state_info.pop("state")

        retriever.close()

        return next_state_info
    except Exception as e:
        return {"error": str(e)}

@MCP_SERVER.tool(
    name="get_conversation_context_tool",
    description="Retrieves the current conversation session and history for the user. Returns session info, current state, and recent conversation messages.",
    tags=set(['retrieval', 'conversation', 'session']),
)
async def get_conversation_context_tool() -> dict:
    """
    Gets or creates a conversation session and retrieves the conversation history.
    """
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return {"error": "'user_id' header not found"}

        # Get or create session
        session = retriever.get_or_create_session(student_index=user_index)

        if not session:
            retriever.close()
            return {"error": "Could not retrieve or create session"}

        # Get conversation history (last 10 messages)
        history = retriever.get_conversation_history(session_id=session['session_id'], limit=5)

        retriever.close()

        if history:
            result = {
                "messages": history
            }
        else:
            result = {
                "messages": []
            }
        return result
    except Exception as e:
        return {"error": str(e)}
@MCP_SERVER.tool(
    name="save_conversation_message_tool",
    description="Saves a conversation message (user or assistant) to the session history.",
    tags=set(['conversation', 'session', 'history']),
)
async def save_conversation_message_tool(session_id: str, role: str, content: str, state_at_time: str) -> dict:
    """
    Saves a conversation message to the session history.

    Args:
        session_id: The session ID
        role: The role (user or assistant)
        content: The message content
        state_at_time: The state when this message was sent

    Returns:
        dict: Saved message information
    """
    try:
        retriever = Neo4jRetriever()

        message = retriever.save_conversation_message(
            session_id=session_id,
            role=role,
            content=content,
            state_at_time=state_at_time
        )

        retriever.close()

        if message:
            return {
                "success": True,
                "message_id": message.get("message_id"),
                "role": role,
                "state_at_time": state_at_time
            }
        else:
            return {"error": "Failed to save message"}

    except Exception as e:
        return {"error": str(e)}

@MCP_SERVER.tool(
    name="update_session_state_tool",
    description="Updates the conversation session state after completing a step. Also persists pending_target and optional pending_substate.",
    tags=set(['state', 'session', 'workflow']),
)
async def update_session_state_tool(new_state: str, pending_target: dict | None = None, pending_substate: dict | None = None) -> dict:
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return {"error": "'user_id' header not found"}

        session = retriever.get_or_create_session(student_index=user_index)
        if not session:
            return {"error": "Could not retrieve session"}

        session_id = session["session_id"]
        previous_state = session["current_state"]

        pending_target_json = json.dumps(pending_target, ensure_ascii=False) if pending_target else None
        pending_substate_json = json.dumps(pending_substate, ensure_ascii=False) if pending_substate else None

        updated = retriever.update_session_state(
            session_id=session_id,
            new_state=new_state,
            pending_target_json=pending_target_json,
            pending_substate_json=pending_substate_json,
        )

        retriever.close()

        if updated:
            return {
                "success": True,
                "session_id": session_id,
                "previous_state": previous_state,
                "new_state": new_state,
                "pending_target_json": pending_target_json,
                "pending_substate_json": pending_substate_json,
            }
        else:
            return {"error": "Failed to update session state"}

    except Exception as e:
        return {"error": str(e)}


#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------SET METHOD TOOLS----------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@MCP_SERVER.tool(
    name="set_self_grade_tool",
    description="Zapisuje samoocenę.",
    tags=set(['grading']),
)
async def set_self_grade_tool(param: SetSelfGradeRequest) -> str:
    """
    Ustawia samoocenę studenta.
    """
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        retriever = Neo4jRetriever()
        data = param.model_dump()
        if not user_index:
            return "ERROR: 'user_id' header not found"
        result = retriever.set_self_grade(
            grading_person_index=user_index,
            grade=data['grade'],
            description=data['description']
        )
        
        retriever.close()
        
        return f"SUCCESS: Self-grade {data['grade']} set for student {user_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"
@MCP_SERVER.tool(
    name="identify_teammate_by_name_tool",
    description="Wyszukuje członków zespołu po imieniu (case-insensitive).",
    tags=set(['retrieval', 'teammate', 'search']),
)
async def identify_teammate_by_name_tool(param: IdentifyTeammateByNameRequest) -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_id' header not found"
        retriever = Neo4jRetriever()
        teammates = retriever.identify_teammate_by_name(
            grader_index=user_index,
            name=param.name,
            surname=param.surname
        )
        retriever.close()
        if not teammates:
            return f"No teammates found with name '{param.name}'"
        result = [f"Teammates named {param.name}:"]
        for t in teammates:
            result.append(f"- {t['name']} {t['surname']} -{t['index']}")
        return "\n".join(result)
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="set_teammate_grade_tool",
    description="Zapisuje ocenę kolegi.",
    tags=set(['grading']),
)
async def set_teammate_grade_tool(param: SetTeammateGradeRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_id' header not found"
        retriever.set_teammate_grade(
            grading_person_index=user_index,
            graded_person_index=param.graded_person_index,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: {user_index} graded {param.graded_person_index} with {param.grade}"
    except Exception as e:
        return f"ERROR: {str(e)}"

@MCP_SERVER.tool(
    name="set_leader_grade_tool",
    description="Zapisuje ocenę lidera.",
    tags=set(['grading']),
)
async def set_leader_grade_tool(param: SetLeaderGradeRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_id' header not found"
        retriever.set_leader_grade(
            grading_person_index=user_index,
            project_id=param.project_id,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: leader of project {param.project_id} graded {param.grade} by {user_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="set_project_grade_tool",
    description="Zapisuje ocenę projektu.",
    tags=set(['grading']),
)
async def set_project_grade_tool(param: SetProjectGradeRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_id' header not found"
        retriever.set_project_grade(
            grading_person_index=user_index,
            project_id=param.project_id,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: project {param.project_id} graded {param.grade} by {user_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="set_project_objectives_grade_tool",
    description="Zapisuje ocenę celów projektu użytkownika (automatycznie pobiera project_id).",
    tags=set(['grading']),
)
async def set_project_objectives_grade_tool(param: SetProjectObjectivesGradeRequest) -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_id' header not found"
        retriever = Neo4jRetriever()
        
        # Auto-fetch project_id from user's project
        user_project = retriever.get_student_project(user_index)
        if not user_project:
            retriever.close()
            return f"ERROR: No project found for user {user_index}"
        project_id = user_project.get("project_id")
        
        retriever.set_project_objectives_grade(
            grading_person_index=user_index,
            project_id=project_id,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: objectives of project {project_id} graded {param.grade} by {user_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="set_masters_intent_tool",
    description="Zapisuje odpowiedź na pytanie o pozostanie na magisterce.",
    tags=set(['grading', 'interview', 'open_answer']),
)
async def set_masters_intent_tool(param: SetOpenAnswerRequest) -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_id' header not found"

        retriever = Neo4jRetriever()
        data = param.model_dump()
        retriever.set_open_answer(
            student_index=user_index,
            question_type="masters_intent",
            answer=data["answer"],
        )
        retriever.close()
        return f"SUCCESS: masters_intent saved for student {user_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="set_study_program_feedback_tool",
    description="Zapisuje uwagi do kierunku studiów.",
    tags=set(['grading', 'interview', 'open_answer']),
)
async def set_study_program_feedback_tool(param: SetOpenAnswerRequest) -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_id' header not found"

        retriever = Neo4jRetriever()
        data = param.model_dump()
        retriever.set_open_answer(
            student_index=user_index,
            question_type="study_program_feedback",
            answer=data["answer"],
        )
        retriever.close()
        return f"SUCCESS: study_program_feedback saved for student {user_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"
    
@MCP_SERVER.tool(
    name="check_teammate_outlier_tool",
    description="Checks if current user's teammate grade is an outlier vs peers. Returns JSON.",
    tags=set(['retrieval', 'analysis']),
)
async def check_teammate_outlier_tool(graded_person_index: str, threshold: float = 1.0, min_peers: int = 3) -> str:
    try:
        request = get_http_request()
        grader_index = request.headers.get("user_id")
        if not grader_index:
            return json.dumps({"error": "'user_id' header not found"}, ensure_ascii=False)

        retriever = Neo4jRetriever()

        # all grades given to graded_person_index
        grades = retriever.get_member_grades(index=str(graded_person_index)) or []

        # find user's latest answer meta (also tells if followup already done)
        meta = retriever.get_latest_teammate_answer_meta(grading_person_index=str(grader_index), graded_person_index=str(graded_person_index))
        if not meta or meta.get("grade") is None:
            retriever.close()
            return json.dumps({"eligible": False, "is_outlier": False, "reason": "No user grade found yet."}, ensure_ascii=False)

        if meta.get("outlier_followup_done"):
            retriever.close()
            return json.dumps({"eligible": True, "is_outlier": False, "reason": "Outlier follow-up already done."}, ensure_ascii=False)

        user_grade = float(meta["grade"])

        peers = []
        for g in grades:
            try:
                if str(g.get("grader_index")) == str(grader_index):
                    continue
                if g.get("grade") is None:
                    continue
                peers.append(float(g["grade"]))
            except Exception:
                continue

        if len(peers) < int(min_peers):
            retriever.close()
            return json.dumps({
                "eligible": False,
                "is_outlier": False,
                "reason": f"Not enough peer grades (need {min_peers}, have {len(peers)}).",
                "user_grade": user_grade,
                "peer_count": len(peers),
            }, ensure_ascii=False)

        peers_sorted = sorted(peers)
        n = len(peers_sorted)
        if n % 2 == 1:
            median = peers_sorted[n // 2]
        else:
            median = (peers_sorted[n // 2 - 1] + peers_sorted[n // 2]) / 2.0

        mean = sum(peers_sorted) / n
        diff = user_grade - median

        is_outlier = abs(diff) >= float(threshold)

        followup = None
        if is_outlier:
            direction = "wyżej" if diff > 0 else "niżej"
            followup = (
                f"Widzę, że dałeś/aś ocenę **{user_grade:.1f}**, a mediana ocen innych osób to około **{median:.1f}** "
                f"(Twoja ocena jest {direction}). Możesz krótko wyjaśnić, **co konkretnie** uzasadnia tę różnicę? "
                f"Podaj 1–2 przykłady zachowań/kontrybucji tej osoby."
            )

        retriever.close()
        return json.dumps({
            "eligible": True,
            "is_outlier": is_outlier,
            "user_grade": user_grade,
            "peer_count": n,
            "peer_median": median,
            "peer_mean": mean,
            "threshold": float(threshold),
            "followup_question": followup,
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    
@MCP_SERVER.tool(
    name="append_teammate_outlier_followup_tool",
    description="Appends outlier follow-up to the latest teammate assessment Answer for (grader->graded).",
    tags=set(['set', 'write']),
)
async def append_teammate_outlier_followup_tool(graded_person_index: str, followup: str) -> str:
    try:
        request = get_http_request()
        grader_index = request.headers.get("user_id")
        if not grader_index:
            return json.dumps({"error": "'user_id' header not found"}, ensure_ascii=False)

        retriever = Neo4jRetriever()
        ok = retriever.append_teammate_outlier_followup(
            grading_person_index=str(grader_index),
            graded_person_index=str(graded_person_index),
            followup=followup
        )
        retriever.close()

        return json.dumps({"success": bool(ok)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


