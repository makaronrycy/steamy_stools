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

@MCP_SERVER.tool(
    name="check_name_tool",
    description="Sprawdza czy imię i nazwisko są w bazie.",
    tags=set(['verification']),
)
async def check_name_tool(param: NameEntity) -> str:
    data = param.model_dump()
    first = data.get("first_name", "").lower()
    last = data.get("last_name", "").lower()
    
    print(f"check_name_tool WYWOLANE! first={first}, last={last}")
    
    for student in MOCK_STUDENTS.values():
        if student["name"].lower() == first and student["surname"].lower() == last:
            result = f"FOUND - Student: {student['name']} {student['surname']}, index: {student['index']}"
            print(f"ZWRACAM: {result}")
            return result
    
    result = "NOT_FOUND - Nie znaleziono studenta"
    print(f"ZWRACAM: {result}")
    return result

@MCP_SERVER.tool(
    name="get_user_info_tool",
    description="Pobiera info o użytkowniku.",
    tags=set(['retrieval']),
)
async def get_user_info_tool(param: GetUserInfoRequest) -> str:
    student = MOCK_STUDENTS.get(param.index)
    if not student:
        return f"No user found for index {param.index}"
    
    return f"User {student['index']}: {student['name']} {student['surname']}\nProject: {student['project_id']} ({student['project_name']})"

@MCP_SERVER.tool(
    name="get_student_completion_status_tool",
    description="Zwraca status kompletności.",
    tags=set(['retrieval']),
)
async def get_student_completion_status_tool(param: GetStudentCompletionStatusRequest) -> str:
    idx = param.index
    
    # Sprawdź samoocenę
    has_self = idx in MOCK_GRADES["self"]
    
    # Sprawdź oceny kolegów
    student = MOCK_STUDENTS.get(idx)
    if student:
        project_members = [s["index"] for s in MOCK_STUDENTS.values() if s["project_id"] == student["project_id"] and s["index"] != idx]
        graded_teammates = [m for m in project_members if f"{idx}_{m}" in MOCK_GRADES["teammate"]]
        teammates_complete = len(graded_teammates) == len(project_members)
    else:
        teammates_complete = True
        project_members = []
        graded_teammates = []
    
    # Sprawdź oceny projektów (2 projekty)
    graded_projects = [p for p in ["1", "2"] if f"{idx}_{p}" in MOCK_GRADES["project"]]
    projects_complete = len(graded_projects) == 2
    
    # Sprawdź ocenę lidera
    has_leader = f"{idx}_{student['project_id']}" in MOCK_GRADES["leader"] if student else False
    
    # Sprawdź ocenę celów
    has_objectives = f"{idx}_{student['project_id']}" in MOCK_GRADES["objectives"] if student else False
    
    result = {
        "all_complete": has_self and teammates_complete and projects_complete and has_leader and has_objectives,
        "self_assessment": {"is_complete": has_self},
        "teammate_assessments": {
            "total_required": len(project_members),
            "completed": len(graded_teammates),
            "is_complete": teammates_complete
        },
        "project_assessments": {
            "total_required": 2,
            "completed": len(graded_projects),
            "is_complete": projects_complete
        },
        "leadership_assessment": {"required": True, "is_complete": has_leader},
        "objectives_assessment": {"is_complete": has_objectives}
    }
    
    import json
    return json.dumps(result)

@MCP_SERVER.tool(
    name="set_self_grade_tool",
    description="Zapisuje samoocenę.",
    tags=set(['grading']),
)
async def set_self_grade_tool(param: SetSelfGradeRequest) -> str:
    data = param.model_dump()
    MOCK_GRADES["self"][data["grading_person_index"]] = {
        "grade": data["grade"],
        "description": data["description"]
    }
    return f"SUCCESS: Self-grade {data['grade']} saved for {data['grading_person_index']}"

@MCP_SERVER.tool(
    name="set_teammate_grade_tool",
    description="Zapisuje ocenę kolegi.",
    tags=set(['grading']),
)
async def set_teammate_grade_tool(param: SetTeammateGradeRequest) -> str:
    data = param.model_dump()
    key = f"{data['grading_person_index']}_{data['graded_person_index']}"
    MOCK_GRADES["teammate"][key] = {
        "grade": data["grade"],
        "description": data["description"]
    }
    return f"SUCCESS: Teammate grade saved"

@MCP_SERVER.tool(
    name="set_leader_grade_tool",
    description="Zapisuje ocenę lidera.",
    tags=set(['grading']),
)
async def set_leader_grade_tool(param: SetLeaderGradeRequest) -> str:
    data = param.model_dump()
    key = f"{data['grading_person_index']}_{data['project_id']}"
    MOCK_GRADES["leader"][key] = {
        "grade": data["grade"],
        "description": data["description"]
    }
    return f"SUCCESS: Leader grade saved"

@MCP_SERVER.tool(
    name="set_project_grade_tool",
    description="Zapisuje ocenę projektu.",
    tags=set(['grading']),
)
async def set_project_grade_tool(param: SetProjectGradeRequest) -> str:
    data = param.model_dump()
    key = f"{data['grading_person_index']}_{data['project_id']}"
    MOCK_GRADES["project"][key] = {
        "grade": data["grade"],
        "description": data["description"]
    }
    return f"SUCCESS: Project {data['project_id']} graded"

@MCP_SERVER.tool(
    name="set_project_objectives_grade_tool",
    description="Zapisuje ocenę celów.",
    tags=set(['grading']),
)
async def set_project_objectives_grade_tool(param: SetProjectObjectivesGradeRequest) -> str:
    data = param.model_dump()
    key = f"{data['grading_person_index']}_{data['project_id']}"
    MOCK_GRADES["objectives"][key] = {
        "grade": data["grade"],
        "description": data["description"]
    }
    return f"SUCCESS: Objectives grade saved"

@MCP_SERVER.tool(
    name="get_ungraded_members_tool",
    description="Zwraca nieocenionych kolegów.",
    tags=set(['retrieval']),
)
async def get_ungraded_members_tool(param: GetUngradedMembersRequest) -> str:
    student = MOCK_STUDENTS.get(param.index)
    if not student:
        return f"[]"
    
    project_members = [s["index"] for s in MOCK_STUDENTS.values() if s["project_id"] == student["project_id"] and s["index"] != param.index]
    ungraded = [m for m in project_members if f"{param.index}_{m}" not in MOCK_GRADES["teammate"]]
    
    return f"Ungraded teammates: {ungraded}"

@MCP_SERVER.tool(
    name="get_ungraded_projects_tool",
    description="Zwraca nieocenione projekty.",
    tags=set(['retrieval']),
)
async def get_ungraded_projects_tool(param: GetUngradedProjectsRequest) -> str:
    all_projects = ["1", "2"]
    ungraded = [p for p in all_projects if f"{param.index}_{p}" not in MOCK_GRADES["project"]]
    return f"Ungraded projects: {ungraded}"
