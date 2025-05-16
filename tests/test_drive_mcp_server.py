import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.mcp_servers.gdrive.server.drive_mcp_server import interact_with_drive 


@pytest.mark.asyncio
@patch("app.mcp_servers.gdrive.server.drive_mcp_server.create_drive_agent")
async def test_interact_with_drive_success(mock_create_agent):
    # Arrange
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"output": "Drive file created successfully."}
    mock_create_agent.return_value = mock_agent

    # Act
    result = await interact_with_drive("Create a new file named notes.txt")

    # Assert
    assert "created successfully" in result
    mock_create_agent.assert_called_once()
    mock_agent.invoke.assert_called_once_with({"input": "Create a new file named notes.txt"})


@pytest.mark.asyncio
@patch("app.mcp_servers.gdrive.server.drive_mcp_server.create_drive_agent")
async def test_interact_with_drive_error(mock_create_agent):
    # Arrange
    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = Exception("Simulated failure")
    mock_create_agent.return_value = mock_agent

    # Act
    result = await interact_with_drive("Delete all files")

    # Assert
    assert "Error: Simulated failure" in result
    mock_create_agent.assert_called_once()
    mock_agent.invoke.assert_called_once()
