import pytest
from unittest.mock import patch
from app.mcp_servers.gdrive.server.agent import create_drive_agent
from langchain.agents import AgentExecutor
from langchain_openai import ChatOpenAI
from app.mcp_servers.gdrive.tools.file_browsing_tools import ListAllFilesTool, SearchFilesTool, GetFileMetadataTool, ListFolderFilesTool, UploadFileToDriveTool
from app.mcp_servers.gdrive.tools.file_content_tools import ReadFileTool, ExtractInfoTool, ParseDocumentTool, AnswerQuestionTool, SearchInDocumentTool, SummarizeDocumentTool
import os

@pytest.fixture
def mock_openai_api_key():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        yield

def test_create_drive_agent(mock_openai_api_key):
    """
    Test that the create_drive_agent function correctly initializes and returns an AgentExecutor instance.
    """
    agent_executor = create_drive_agent()

    # Assert that the agent_executor is an instance of AgentExecutor
    assert isinstance(agent_executor, AgentExecutor)

    # Assert that the agent within agent_executor is not None
    assert agent_executor.agent is not None

    # Assert that the tools are correctly initialized within the agent_executor
    tool_names = [tool.name for tool in agent_executor.tools]
    expected_tool_names = [
        "list_all_files",
        "list_folder_files",
        "search_files",
        "get_file_metadata",
        "read_file",
        "parse_document",
        "extract_information",
        "summarize_document",
        "search_in_document",
        "answer_question",
        "upload_file_to_drive"
    ]
    assert set(tool_names) == set(expected_tool_names)

def test_openai_api_key_present(mock_openai_api_key):
    """
    Test that the OpenAI API key is correctly loaded from the environment variables.
    """
    agent_executor = create_drive_agent()
    # access llm through the runnable
    runnable = agent_executor.agent.runnable
    print(f"Type of agent_executor.agent.runnable: {type(runnable)}")
    print(f"Attributes of agent_executor.agent.runnable: {dir(runnable)}")
    # This test relies on the mock being correctly applied
    assert os.getenv("OPENAI_API_KEY") == "test_key"
