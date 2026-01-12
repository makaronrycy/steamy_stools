"""
MCP Resources and Custom HTTP Endpoints.

This module provides:
- MCP resources for database schema queries
- Custom HTTP endpoints for database management:
    - /fill_db: Populate database with CSV data and assumptions
    - /reset_db: Clear all database contents
    - /list_people: Get all students grouped by project
    - /completion_status: Get overall interview completion statistics
"""

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
    """
    Example resource demonstrating MCP resource pattern.
    
    Args:
        param (str): Parameter value from the resource URI.
    
    Returns:
        dict: Response containing the accessed parameter.
    """
    # Implement the resource's functionality here
    return {"message": f"Resource accessed with param: {param}"}

@MCP_SERVER.resource(
    uri='resource://database//schema//nodes',
    description='Get the list of node types with their fields in the database',
    mime_type='application/json'
)
async def get_node_types() -> dict:
    """
    Retrieves the database schema including all node types and their fields.
    
    Returns:
        dict: Database schema with node type definitions.
    """
    logging.warning(f'[get_node_types] {datetime.now()} started')
    connector = Neo4jRetriever(
        uri=os.environ['NEO4J_URI'],
        username=os.environ['NEO4J_USERNAME'],
        password=os.environ['NEO4J_PASSWORD'],
    )
    schema = connector.get_node_types()
    logging.warning(f'[get_node_types] {datetime.now()} finished')
    return schema

@MCP_SERVER.custom_route(path='/reset_db', methods=['POST'])
async def reset_database_endpoint(request):
    """
    Clears all data from the database.
    
    WARNING: This operation is destructive and cannot be undone.
    
    Args:
        request: Starlette request object.
    
    Returns:
        JSONResponse: Success confirmation message.
    """
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
    """
    Lists all students grouped by their projects.
    
    Args:
        request: Starlette request object.
    
    Returns:
        JSONResponse: List of projects with their members:
            [{project_id, project_name, people: [{name, surname, index}]}]
    """
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
    """
    Gets overall interview completion statistics.
    
    Args:
        request: Starlette request object.
    
    Returns:
        JSONResponse: Completion stats:
            {completed_students, total_students, remaining_students, completion_percentage}
    """
    logging.warning(f'[completion_status_endpoint] {datetime.now()} started')
    connector = Neo4jRetriever(
        uri=os.environ['NEO4J_URI'],
        username=os.environ['NEO4J_USERNAME'],
        password=os.environ['NEO4J_PASSWORD'],
    )
    status = connector.get_completion_status()
    logging.warning(f'[completion_status_endpoint] {datetime.now()} finished')
    return JSONResponse(status, status_code=200)

@MCP_SERVER.custom_route(path='/generate_reports', methods=['POST'])
async def generate_reports_endpoint(request):
    """
    Generates CSV reports from Neo4j database.
    Runs both generate_reports.py and generate_final_grades.py scripts.
    
    Returns:
        JSONResponse: Status and message with report generation results.
    """
    logging.warning(f'[generate_reports_endpoint] {datetime.now()} started')
    
    try:
        from ..neo4j_retriever.generate_reports import Neo4jReportGenerator
        from ..neo4j_retriever.generate_final_grades import FinalGradeCalculator
        
        # Generate all reports
        generator = Neo4jReportGenerator(
            uri=os.environ['NEO4J_URI'],
            username=os.environ['NEO4J_USERNAME'],
            password=os.environ['NEO4J_PASSWORD'],
        )
        try:
            reports = generator.generate_all_reports()
            reports_count = len(reports)
        finally:
            generator.close()
        
        # Generate final grades
        calculator = FinalGradeCalculator()
        grades_file = calculator.generate_report()
        
        logging.warning(f'[generate_reports_endpoint] {datetime.now()} finished')
        return JSONResponse({
            "status": "success",
            "message": f"Wygenerowano {reports_count} raportów oraz plik z ocenami końcowymi.",
            "reports_count": reports_count,
            "grades_file": grades_file
        }, status_code=200)
        
    except Exception as e:
        logging.error(f'[generate_reports_endpoint] Error: {str(e)}')
        return JSONResponse({
            "status": "error",
            "message": f"Błąd generowania raportów: {str(e)}"
        }, status_code=500)
