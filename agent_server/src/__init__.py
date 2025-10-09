from fastmcp import FastMCP
from .neo4j_retriever import Neo4jRetriever
from starlette.responses import JSONResponse
from datetime import datetime

from fastmcp import FastMCP

MCP_SERVER = FastMCP("Agent Server", version="0.1.0")
from .server_resources import *

def create_app():
    return MCP_SERVER.http_app(path="/mcp",transport="streamable-http")