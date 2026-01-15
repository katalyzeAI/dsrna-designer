"""LangGraph server entrypoint for dsRNA Designer Agent.

This module exports the compiled graph for use with `langgraph dev` or
`langgraph up`. The graph is created at module load time.

Usage:
    langgraph dev        # Development server with hot reload
    langgraph up         # Production server
"""

from dsrna_agent.agent import create_dsrna_agent

# Create the compiled graph at module load time
# LangGraph server imports this directly
graph = create_dsrna_agent()
