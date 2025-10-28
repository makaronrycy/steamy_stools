from ..neo4j_retriever import Neo4jRetriever
from .. import MCP_SERVER
from .models import NameEntity, Message, GetProjectGradesRequest, SetSelfGradeRequest

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