from .. import MCP_SERVER
# WYŁĄCZONE - nie używamy Neo4j póki co
from ..neo4j_retriever import Neo4jRetriever
import logging
from datetime import datetime
import os
from starlette.responses import JSONResponse

@MCP_SERVER.resource(
    name="example_resource",
    uri="resource://example_resource/{param}",
    description="An example resource that provides useful data.",
    tags=set(['example', 'data']),
    mime_type='application/json'
)
async def example_resource(param: str) -> dict:
    # Implement the resource's functionality here
    return {"message": f"Resource accessed with param: {param}"}

@MCP_SERVER.resource(
    uri='resource://database//schema//nodes',
    description='Get the list of node types with their fields in the database',
    mime_type='application/json'
)
async def get_node_types() -> dict:
    logging.warning(f'[get_node_types] {datetime.now()} started')
    connector = Neo4jRetriever(
        uri=os.environ['NEO4J_URI'],
        username=os.environ['NEO4J_USERNAME'],
        password=os.environ['NEO4J_PASSWORD'],
    )
    schema = connector.get_node_types()
    logging.warning(f'[get_node_types] {datetime.now()} finished')
    return schema

@MCP_SERVER.custom_route(path='/fill_db', methods=['POST'])
async def fill_database_endpoint(request):
    logging.warning(f'[fill_database_endpoint] {datetime.now()} started')
    data = request.json
    connector = Neo4jRetriever(
        uri=os.environ['NEO4J_URI'],
        username=os.environ['NEO4J_USERNAME'],
        password=os.environ['NEO4J_PASSWORD'],
    )
    if data.get("csv"):
        csv_data = data["csv"]
    else:
        return JSONResponse({"error": "No CSV data provided"}, status_code=400)
    if data.get("assumptions"):
        assumptions_data = data["assumptions"]
    else:
        return JSONResponse({"error": "No assumptions data provided"}, status_code=400)
    
    connector.fill_database_no_grades(csv_data)
    data = connector.generate_grades_with_assumptions(csv_data,assumptions_data)
    connector.fill_database_with_grades(data)

    logging.warning(f'[fill_database_endpoint] {datetime.now()} finished')
    return JSONResponse({"status": "Database filled successfully"}, status_code=200)
@MCP_SERVER.custom_route(path='/reset_db', methods=['POST'])
async def reset_database_endpoint(request):
    logging.warning(f'[reset_database_endpoint] {datetime.now()} started')
    connector = Neo4jRetriever(
        uri=os.environ['NEO4J_URI'],
        username=os.environ['NEO4J_USERNAME'],
        password=os.environ['NEO4J_PASSWORD'],
    )
    connector.clear_database()
    logging.warning(f'[reset_database_endpoint] {datetime.now()} finished')
    return JSONResponse({"status": "Database reset successfully"}, status_code=200)

@MCP_SERVER.custom_route(path='/list_people', methods=['GET'])
async def list_people_endpoint(request):
    logging.warning(f'[list_people_endpoint] {datetime.now()} started')
    connector = Neo4jRetriever(
        uri=os.environ['NEO4J_URI'],
        username=os.environ['NEO4J_USERNAME'],
        password=os.environ['NEO4J_PASSWORD'],
    )
    people = connector.list_people()
    logging.warning(f'[list_people_endpoint] {datetime.now()} finished')
    return JSONResponse(people, status_code=200)
@MCP_SERVER.custom_route(path='/completion_status', methods=['GET'])
async def completion_status_endpoint(request):
    logging.warning(f'[completion_status_endpoint] {datetime.now()} started')
    connector = Neo4jRetriever(
        uri=os.environ['NEO4J_URI'],
        username=os.environ['NEO4J_USERNAME'],
        password=os.environ['NEO4J_PASSWORD'],
    )
    status = connector.get_completion_status()
    logging.warning(f'[completion_status_endpoint] {datetime.now()} finished')
    return JSONResponse(status, status_code=200)