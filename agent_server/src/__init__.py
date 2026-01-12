"""
Agent Server - MCP Server for managing student assessments.

This module provides the FastMCP server instance and application factory
for the grading interview system.

Components:
    - MCP_SERVER: FastMCP server instance for handling MCP protocol
    - create_app(): Factory function creating the HTTP application
"""

from fastmcp import FastMCP
from .neo4j_retriever import Neo4jRetriever
from datetime import datetime

from fastmcp import FastMCP

MCP_SERVER = FastMCP("Agent Server", version="0.1.0")
from .server_resources import *

def create_app():
    """
    Creates the HTTP application for the MCP server.
    
    Sets up the FastMCP server with streamable HTTP transport
    on the /mcp endpoint.
    
    Returns:
        Application: The configured HTTP application instance.
    """
    return MCP_SERVER.http_app(path="/mcp", transport="streamable-http") 