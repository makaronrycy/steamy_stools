from .. import MCP_SERVER,Neo4jRetriever
import logging
from datetime import datetime
import os

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