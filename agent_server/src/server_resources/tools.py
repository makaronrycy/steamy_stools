from ..neo4j_retriever import Neo4jRetriever
from .. import MCP_SERVER
from .models import (
    NameEntity, Message,
    GetProjectGradesRequest, GetMemberGradesRequest, IsLeaderRequest,
    GetProjectMembersRequest, GetUserInfoRequest, HasGradedAllMembersRequest,
    GetUngradedMembersRequest, HasGradedAllProjectsRequest, GetUngradedProjectsRequest,
    GetStudentCompletionStatusRequest, IdentifyTeammateByNameRequest,
    IdentifyTeammateBySurnameRequest,
    SetSelfGradeRequest, SetTeammateGradeRequest, SetLeaderGradeRequest,
    SetProjectGradeRequest, SetProjectObjectivesGradeRequest,
)

@MCP_SERVER.tool(
    name="example_tool",
    description="An example tool that does something useful.",
    tags=set(['example', 'utility']),
)
async def example_tool(param: Message) -> str:
    # Implement the tool's functionality here
    return f"Tool executed with param: {param.content}"

@MCP_SERVER.tool(
    name="check_name_tool",
    description="Narzędzie sprawdzające, czy podane imię i nazwisko istnieje w bazie danych.",
    tags=set(['verification', 'database']),
)
async def check_name_tool(param: NameEntity ) -> str:
    # Przykładowa implementacja - w rzeczywistości sprawdź w bazie danych
    database = {
        ("Jan", "Kowalski"),
        ("Anna", "Nowak"),
        ("Piotr", "Wiśniewski"),
    }
    try:
        data = param.model_dump()
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        if (first_name, last_name) in database:
            return "FOUND"
        else:
            return "NOT_FOUND"
    except Exception as e:
        return f"ERROR: {str(e)}"

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
    description="Zwraca podstawowe informacje o użytkowniku.",
    tags=set(['retrieval', 'user']),
)
async def get_user_info_tool(param: GetUserInfoRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        info = retriever.get_user_info(index=param.index)
        retriever.close()
        if not info:
            return f"No user found for index {param.index}"
        return (
            f"User {param.index}: {info['name']} {info['surname']}\n"
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
async def get_ungraded_members_tool(param: GetUngradedMembersRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        lst = retriever.get_ungraded_members(index=param.index)
        retriever.close()
        return f"Ungraded teammates for {param.index}: {lst}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="has_graded_all_projects_tool",
    description="Sprawdza, czy użytkownik ocenił wszystkie projekty.",
    tags=set(['retrieval', 'progress']),
)
async def has_graded_all_projects_tool(param: HasGradedAllProjectsRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        flag = retriever.has_graded_all_projects(index=param.index)
        retriever.close()
        return "TRUE" if flag else "FALSE"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="get_ungraded_projects_tool",
    description="Zwraca projekty, których użytkownik jeszcze nie ocenił.",
    tags=set(['retrieval', 'progress']),
)
async def get_ungraded_projects_tool(param: GetUngradedProjectsRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        lst = retriever.get_ungraded_projects(index=param.index)
        retriever.close()
        return f"Ungraded projects for {param.index}: {lst}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="get_student_completion_status_tool",
    description="Zwraca status kompletności ocen studenta.",
    tags=set(['retrieval', 'status']),
)
async def get_student_completion_status_tool(param: GetStudentCompletionStatusRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        status = retriever.get_student_completion_status(index=param.index)
        retriever.close()
        return str(status)
    except Exception as e:
        return f"ERROR: {str(e)}"

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
        retriever = Neo4jRetriever()
        data = param.model_dump()
        
        result = retriever.set_self_grade(
            grading_person_index=data['grading_person_index'],
            grade=data['grade'],
            description=data['description']
        )
        
        retriever.close()
        
        return f"SUCCESS: Self-grade {data['grade']} set for student {data['grading_person_index']}"
    except Exception as e:
        return f"ERROR: {str(e)}"
@MCP_SERVER.tool(
    name="identify_teammate_by_name_tool",
    description="Wyszukuje członków zespołu po imieniu (case-insensitive).",
    tags=set(['retrieval', 'teammate', 'search']),
)
async def identify_teammate_by_name_tool(param: IdentifyTeammateByNameRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        teammates = retriever.identify_teammate_by_name(
            grader_index=param.grader_index,
            name=param.name
        )
        retriever.close()
        if not teammates:
            return f"No teammates found with name '{param.name}'"
        result = [f"Teammates named {param.name}:"]
        for t in teammates:
            result.append(f"- {t['name']} {t['surname']} ({t['index']})")
        return "\n".join(result)
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="identify_teammate_by_surname_tool",
    description="Wyszukuje członków zespołu po nazwisku (case-insensitive).",
    tags=set(['retrieval', 'teammate', 'search']),
)
async def identify_teammate_by_surname_tool(param: IdentifyTeammateBySurnameRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        teammates = retriever.identify_teammate_by_surname(
            grader_index=param.grader_index,
            surname=param.surname
        )
        retriever.close()
        if not teammates:
            return f"No teammates found with surname '{param.surname}'"
        result = [f"Teammates with surname {param.surname}:"]
        for t in teammates:
            result.append(f"- {t['name']} {t['surname']} ({t['index']})")
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
        retriever.set_teammate_grade(
            grading_person_index=param.grading_person_index,
            graded_person_index=param.graded_person_index,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: {param.grading_person_index} graded {param.graded_person_index} with {param.grade}"
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
        retriever.set_leader_grade(
            grading_person_index=param.grading_person_index,
            project_id=param.project_id,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: leader of project {param.project_id} graded {param.grade} by {param.grading_person_index}"
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
        retriever.set_project_grade(
            grading_person_index=param.grading_person_index,
            project_id=param.project_id,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: project {param.project_id} graded {param.grade} by {param.grading_person_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@MCP_SERVER.tool(
    name="set_project_objectives_grade_tool",
    description="Zapisuje ocenę celów projektu.",
    tags=set(['grading', 'objectives']),
)
async def set_project_objectives_grade_tool(param: SetProjectObjectivesGradeRequest) -> str:
    try:
        retriever = Neo4jRetriever()
        retriever.set_project_objectives_grade(
            grading_person_index=param.grading_person_index,
            project_id=param.project_id,
            grade=param.grade,
            description=param.description
        )
        retriever.close()
        return f"SUCCESS: objectives of project {param.project_id} graded {param.grade} by {param.grading_person_index}"
    except Exception as e:
        return f"ERROR: {str(e)}"
