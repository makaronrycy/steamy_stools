from ..neo4j_retriever import Neo4jRetriever
from .. import MCP_SERVER
from .models import (
    NameEntity, Message,
    GetProjectGradesRequest, GetMemberGradesRequest, IsLeaderRequest,
    GetProjectMembersRequest, GetUserInfoRequest, HasGradedAllMembersRequest,
    GetUngradedMembersRequest, HasGradedAllProjectsRequest, GetUngradedProjectsRequest,
    GetStudentCompletionStatusRequest, IdentifyTeammateByNameRequest,
    SetSelfGradeRequest, SetTeammateGradeRequest, SetLeaderGradeRequest,
    SetProjectGradeRequest, SetProjectObjectivesGradeRequest,
)
from starlette.requests import Request
from fastmcp.server.dependencies import get_http_request

@MCP_SERVER.tool(
    name="example_tool",
    description="An example tool that does something useful.",
    tags=set(['example', 'utility']),
)
async def example_tool(param: Message) -> str:
    # Implement the tool's functionality here
    return f"Tool executed with param: {param.content}"


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
        grades = retriever.get_member_grades(name=param.name)
        retriever.close()

        if not grades:
            return f"No grades found for member {param.name}"

        result = [f"Grades for member {param.name}:"]
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
        flag = retriever.is_leader(name=param.name)
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
    description="Zwraca podstawowe informacje o użytkowniku.",
    tags=set(['retrieval', 'user']),
)
async def get_user_info_tool() -> str:
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_index' header not found"
            
        with retriever.driver.session() as session:
            res = session.run("MATCH (s:Student {index: $index}) RETURN s.name as name", index=user_index).single()
            user_name = res["name"] if res else None
            
        if not user_name:
             return f"No user found for index {user_index}"

        info = retriever.get_user_info(name=user_name)
        retriever.close()
        if not info:
            return f"No user found for index {user_index}"
        return (
            f"User {user_index}: {info['name']} {info['surname']}\n"
            f"GitHub: {info['github']}\n"
            f"Project: {info['project_id']} ({info['project_name']})"
        )
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="has_graded_all_members_tool",
    description="Sprawdza, czy użytkownik ocenił wszystkich członków zespołu.",
    tags=set(['retrieval', 'progress']),
)
async def has_graded_all_members_tool(param: HasGradedAllMembersRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        flag = retriever.has_graded_all_members(name=param.name)
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
        
        with retriever.driver.session() as session:
            res = session.run("MATCH (s:Student {index: $index}) RETURN s.name as name", index=user_index).single()
            user_name = res["name"] if res else None
            
        if not user_name:
             return f"No user found for index {user_index}"

        lst = retriever.get_ungraded_members(name=user_name)
        retriever.close()
        return f"Ungraded teammates for {user_index}: {lst}"
    except Exception as e:
        return f"ERROR: {str(e)}"
@MCP_SERVER.tool(
    name="get_random_ungraded_member_tool",
    description="Zwraca losowego nieocenionego kolegę z zespołu.",
    tags=set(['retrieval', 'progress']),
)
async def get_random_ungraded_member_tool() -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_index' header not found"
        retriever = Neo4jRetriever()
        
        with retriever.driver.session() as session:
            res = session.run("MATCH (s:Student {index: $index}) RETURN s.name as name", index=user_index).single()
            user_name = res["name"] if res else None
            
        if not user_name:
             return f"No user found for index {user_index}"

        member = retriever.get_random_ungraded_member(name=user_name)
        retriever.close()
        if not member:
            return f"All teammates have been graded by {user_index}"
        return f"Random ungraded teammate for {user_index}: {member}"
    except Exception as e:
        return f"ERROR: {str(e)}"

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
        
        with retriever.driver.session() as session:
            res = session.run("MATCH (s:Student {index: $index}) RETURN s.name as name", index=user_index).single()
            user_name = res["name"] if res else None
            
        if not user_name:
             return f"No user found for index {user_index}"

        flag = retriever.has_graded_all_projects(name=user_name)
        retriever.close()
        return "TRUE" if flag else "FALSE"
    except Exception as e:
        return f"ERROR: {str(e)}"

@MCP_SERVER.tool(
    name="get_leader_info_tool",
    description="Zwraca indeks lidera projektu użytkownika.",
    tags=set(['retrieval', 'role']),
)
async def get_leader_info_tool() -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_index' header not found"
        retriever = Neo4jRetriever()
        
        with retriever.driver.session() as session:
            res = session.run("MATCH (s:Student {index: $index}) RETURN s.name as name", index=user_index).single()
            user_name = res["name"] if res else None
            
        if not user_name:
             return f"No user found for index {user_index}"

        leader_data = retriever.get_leader_of_student(name=user_name)
        leader_index = leader_data.get("index") if leader_data else None
        leader_name = leader_data.get("name") if leader_data else None
        leader_surname = leader_data.get("surname") if leader_data else None

        retriever.close()
        if not leader_index:
            return f"No leader found for user {user_index}"
        return f"Leader of user {user_index} is {leader_index}, {leader_name} {leader_surname}"
    except Exception as e:
        return f"ERROR: {str(e)}"

@MCP_SERVER.tool(
    name="get_ungraded_projects_tool",
    description="Zwraca projekty, których użytkownik jeszcze nie ocenił.",
    tags=set(['retrieval', 'progress']),
)
async def get_ungraded_projects_tool() -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_index' header not found"
        retriever = Neo4jRetriever()
        
        with retriever.driver.session() as session:
            res = session.run("MATCH (s:Student {index: $index}) RETURN s.name as name", index=user_index).single()
            user_name = res["name"] if res else None
            
        if not user_name:
             return f"No user found for index {user_index}"

        lst = retriever.get_ungraded_projects(name=user_name)
        retriever.close()
        return f"Ungraded projects for {user_index}: {lst}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="get_student_completion_status_tool",
    description="Zwraca status kompletności ocen studenta.",
    tags=set(['retrieval', 'status']),
)
async def get_student_completion_status_tool() -> str:
    try:
        retriever = Neo4jRetriever()
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_index' header not found"
            
        with retriever.driver.session() as session:
            res = session.run("MATCH (s:Student {index: $index}) RETURN s.name as name", index=user_index).single()
            user_name = res["name"] if res else None
            
        if not user_name:
             return f"No user found for index {user_index}"

        status = retriever.get_student_completion_status(name=user_name)
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

        with retriever.driver.session() as session:
            res = session.run("MATCH (s:Student {index: $index}) RETURN s.name as name", index=user_index).single()
            user_name = res["name"] if res else None
            
        if not user_name:
             return {"error": f"No user found for index {user_index}"}

        next_state_info = retriever.get_next_required_state(name=user_name)

        # Also get the session to retrieve last_state and current state
        session = retriever.get_or_create_session(student_index=user_index)
        if session:
            next_state_info["last_state"] = session.get("last_state")
            next_state_info["session_id"] = session.get("session_id")
            next_state_info["current_state_in_session"] = session.get("current_state")
        else:
            next_state_info["last_state"] = None
            next_state_info["session_id"] = None
            next_state_info["current_state_in_session"] = None

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
    description="Updates the conversation session state after completing a state. Moves current_state to last_state and sets new current_state.",
    tags=set(['state', 'session', 'workflow']),
)
async def update_session_state_tool(new_state: str) -> dict:
    """
    Updates the session state after successfully completing a conversation state.
    Moves the current state to last_state and sets the new current_state.

    Args:
        new_state: The new state to set as current_state

    Returns:
        dict: Updated session information
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
            return {"error": "Could not retrieve session"}

        session_id = session['session_id']
        previous_state = session['current_state']

        # Update the session state
        updated = retriever.update_session_state(
            session_id=session_id,
            new_state=new_state,
            previous_state=previous_state
        )

        retriever.close()

        if updated:
            return {
                "success": True,
                "session_id": session_id,
                "previous_state": previous_state,
                "new_state": new_state,
                "last_state": previous_state  # The old current_state is now last_state
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
    description="Narzędzie do ustawiania samooceny studenta.",
    tags=set(['grading', 'self-assessment', 'database']),
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
    description="Zapisuje ocenę kolegi z zespołu.",
    tags=set(['grading', 'teammate']),
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
    description="Zapisuje ocenę lidera projektu.",
    tags=set(['grading', 'leader']),
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
    tags=set(['grading', 'project']),
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
    description="Zapisuje ocenę celów projektu.",
    tags=set(['grading', 'objectives']),
)
async def set_project_objectives_grade_tool(param: SetProjectObjectivesGradeRequest) -> str:
    try:
        request = get_http_request()
        user_index = request.headers.get("user_id")
        if not user_index:
            return "ERROR: 'user_id' header not found"
        retriever = Neo4jRetriever()
        retriever.set_project_objectives_grade(
            grading_person_index=user_index,
            project_id=param.project_id,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: objectives of project {param.project_id} graded {param.grade} by {user_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"
