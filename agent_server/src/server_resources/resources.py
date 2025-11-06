from .. import MCP_SERVER
# WYŁĄCZONE - nie używamy Neo4j póki co
# from .. import Neo4jRetriever
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