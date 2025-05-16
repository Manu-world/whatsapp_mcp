
from typing import Dict, Any
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from mcp.server.fastmcp import FastMCP
from app.mcp_servers.gdrive.server.agent import create_drive_agent
# Create MCP server
mcp = FastMCP("GoogleDriveAgent")

@mcp.tool()
async def interact_with_drive(query: str) -> str:
    """
    Interact with Google Drive using natural language.
    
    Args:
        query: The user's query about Google Drive operations
        
    Returns:
        str: The agent's response to the query
    """
    try:
        # Create the agent
        agent = create_drive_agent()
        
        # Invoke the agent with the query
        response = agent.invoke({"input": query})
        
        return response['output']
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # Run the MCP server
    print("gdrive mcp running...")
    mcp.run(transport="stdio") 