from .. import MCP_SERVER
from .models import NameEntity,Message,SelfGrade,TeammateGrade,ProjectGrade
from ..neo4j_retriever import Neo4jRetriever
import os
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

@MCP_SERVER.tool(
    name="self_grade_tool",
    description="Narzędzie do ustawiania oceny.",
    tags=set(['assessment', 'set']),
)
async def self_grade_tool(param: SelfGrade):
    neo4j_connector = Neo4jRetriever(
        uri = os.environ['NEO4J_URI'],
        username = os.environ['NEO4J_USERNAME'],
        password = os.environ['NEO4J_PASSWORD'],
    )
    graded_person_index = param.grading_person_index
    grade = param.grade
    description = param.description
    analysis = neo4j_connector.set_self_grade(
        grading_person_index=graded_person_index,
        grade=grade,
        description=description
    )
    return analysis

@MCP_SERVER.tool(
    name="teammate_grade_tool",
    description="Narzędzie do ustawiania oceny współpracownika.",
    tags=set(['assessment', 'set']),
)
async def teammate_grade_tool(param: TeammateGrade):
    neo4j_connector = Neo4jRetriever(
        uri = os.environ['NEO4J_URI'],
        username = os.environ['NEO4J_USERNAME'],
        password = os.environ['NEO4J_PASSWORD'],
    )
    grading_person_index = param.grading_person_index
    graded_person_index = param.graded_person_index
    grade = param.grade
    description = param.description
    analysis = neo4j_connector.set_teammate_grade(
        grading_person_index=grading_person_index,
        graded_person_index=graded_person_index,
        grade=grade,
        description=description
    )
    return analysis

@MCP_SERVER.tool(
    name="project_grade_tool",
    description="Narzędzie do ustawiania oceny projektu.",
    tags=set(['assessment', 'set']),
)
async def project_grade_tool(param: ProjectGrade):
    neo4j_connector = Neo4jRetriever(
        uri = os.environ['NEO4J_URI'],
        username = os.environ['NEO4J_USERNAME'],
        password = os.environ['NEO4J_PASSWORD'],
    )
    grading_person_index = param.grading_person_index
    project_id = param.project_id
    grade = param.grade
    description = param.description
    analysis = neo4j_connector.set_project_grade(
        grading_person_index=grading_person_index,
        project_id=project_id,
        grade=grade,
        description=description
    )
    return analysis


