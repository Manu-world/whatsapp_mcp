import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid
from langchain_core.messages import AIMessage

from app.core.agent_service import init_agent, close_agent, process_message, mcp_client, agent

# Reset the global variables before each test
@pytest.fixture(autouse=True)
def reset_agent_globals():
    global mcp_client, agent
    original_mcp_client = mcp_client
    original_agent = agent
    mcp_client = None
    agent = None
    yield # Run the test
    # Restore the original state or reset to None explicitly if needed
    mcp_client = original_mcp_client
    agent = original_agent


@pytest.mark.asyncio
async def test_init_agent(mocker):
    """Tests the initialization of the agent."""
    mock_mcp_client_instance = AsyncMock()

    mock_mcp_client_instance.get_tools.return_value = ["tool1", "tool2"]

    mock_mcp_client_cls = mocker.patch('app.core.agent_service.MultiServerMCPClient', return_value=mock_mcp_client_instance)

    mock_chat_openai_instance = MagicMock()
    mock_chat_openai_cls = mocker.patch('app.core.agent_service.ChatOpenAI', return_value=mock_chat_openai_instance)

    mock_memory_saver_instance = MagicMock()
    mock_memory_saver_cls = mocker.patch('app.core.agent_service.MemorySaver', return_value=mock_memory_saver_instance)

    mock_create_react_agent = mocker.patch('app.core.agent_service.create_react_agent')

    mock_mcp_config = {"server_url": "http://mock.com"}
    mocker.patch('app.core.agent_service.MCP_CONFIG', mock_mcp_config)

    await init_agent()

    mock_mcp_client_cls.assert_called_once_with(mock_mcp_config)
    mock_mcp_client_instance.__aenter__.assert_awaited_once()
    mock_chat_openai_cls.assert_called_once_with(model="gpt-4o")
    mock_memory_saver_cls.assert_called_once()
    mock_mcp_client_instance.get_tools.assert_called_once() # Ensure tools are retrieved

    # Get the arguments the mock was called with
    args, kwargs = mock_create_react_agent.call_args
    # Assert the positional arguments
    assert args[0] == mock_chat_openai_instance
    # Assert that the second positional argument is a coroutine object or awaitable
    import inspect
    assert inspect.isawaitable(args[1]) or inspect.iscoroutine(args[1])

    # Assert the keyword arguments
    assert kwargs == {"checkpointer": mock_memory_saver_instance}

    # Verify globals are set
    from app.core.agent_service import mcp_client as global_mcp_client
    from app.core.agent_service import agent as global_agent
    assert global_mcp_client == mock_mcp_client_instance
    assert global_agent == mock_create_react_agent.return_value


@pytest.mark.asyncio
async def test_close_agent_when_initialized(mocker):
    """Tests closing the agent when it has been initialized."""
    mock_mcp_client_instance = AsyncMock()
    mocker.patch('app.core.agent_service.mcp_client', mock_mcp_client_instance) # Set global mcp_client

    await close_agent()

    mock_mcp_client_instance.__aexit__.assert_awaited_once_with(None, None, None)

@pytest.mark.asyncio
async def test_close_agent_when_not_initialized(mocker):
    """Tests closing the agent when it has not been initialized."""
    mocker.patch('app.core.agent_service.mcp_client', None) # Ensure global mcp_client is None

    await close_agent()

    pass # No assertion needed, just verify it doesn't crash


@pytest.mark.asyncio
async def test_process_message_agent_not_initialized(mocker):
    """Tests process_message when the agent is not initialized."""
    mocker.patch('app.core.agent_service.agent', None) # Ensure global agent is None

    response = await process_message("Hello")

    assert response == "Agent is not initialized."

@pytest.mark.asyncio
async def test_process_message_with_thread_id(mocker):
    """Tests process_message with a provided thread_id."""
    mock_agent_instance = AsyncMock()
    # Mock the agent's ainvoke method to return a sample response with actual AIMessage
    mock_agent_instance.ainvoke.return_value = {"messages": [MagicMock(), AIMessage(content="Processed response")]} # Return a dict with messages
    mocker.patch('app.core.agent_service.agent', mock_agent_instance)

    test_thread_id = "test-thread-123"
    message = "User message"

    response = await process_message(message, thread_id=test_thread_id)

    mock_agent_instance.ainvoke.assert_awaited_once_with(
        {"messages": message},
        config={"configurable": {"thread_id": test_thread_id}}
    )
    assert response == "Processed response"

@pytest.mark.asyncio
async def test_process_message_without_thread_id(mocker):
    """Tests process_message without a provided thread_id."""
    mock_agent_instance = AsyncMock()
    mock_ai_message = AIMessage(content="Processed response generated UUID") # Use actual AIMessage
    mock_agent_instance.ainvoke.return_value = {"messages": [mock_ai_message]}
    mocker.patch('app.core.agent_service.agent', mock_agent_instance)

    mock_uuid_mock = mocker.patch('uuid.uuid4', return_value=MagicMock(__str__=lambda self: "mock-uuid-456"))

    message = "Another user message"

    response = await process_message(message)

    # uuid.uuid4 should be called once on the stored mock object
    mock_uuid_mock.assert_called_once()
    mock_agent_instance.ainvoke.assert_awaited_once_with(
        {"messages": message},
        config={"configurable": {"thread_id": "mock-uuid-456"}} # Check if the generated UUID is used
    )
    assert response == "Processed response generated UUID"

@pytest.mark.asyncio
async def test_process_message_returns_non_dict(mocker):
    """Tests process_message when agent.ainvoke returns something other than a dict."""
    mock_agent_instance = AsyncMock()
    mock_agent_instance.ainvoke.return_value = "Just a string"
    mocker.patch('app.core.agent_service.agent', mock_agent_instance)

    response = await process_message("Test message")

    assert response == "Just a string"

@pytest.mark.asyncio
async def test_process_message_returns_dict_without_messages(mocker):
    """Tests process_message when agent.ainvoke returns a dict without 'messages' key."""
    mock_agent_instance = AsyncMock()
    mock_agent_instance.ainvoke.return_value = {"other_key": "some_value"}
    mocker.patch('app.core.agent_service.agent', mock_agent_instance)

    response = await process_message("Test message")

    # Assert the actual string representation of the dictionary
    assert response == "{'other_key': 'some_value'}"

@pytest.mark.asyncio
async def test_process_message_returns_dict_with_non_message_list(mocker):
    """Tests process_message when agent.ainvoke returns a dict with 'messages' but not AIMessage instances."""
    mock_agent_instance = AsyncMock()
    # Ensure the list contains items that are not AIMessage instances
    mock_agent_instance.ainvoke.return_value = {"messages": [MagicMock(content="Not AIMessage"), MagicMock(content="Still not AIMessage")]}
    mocker.patch('app.core.agent_service.agent', mock_agent_instance)

    response = await process_message("Test message")

    assert response == "Couldn't generate a proper response."


@pytest.mark.asyncio
async def test_process_message_error_handling(mocker):
    """Tests error handling in process_message."""
    mock_agent_instance = AsyncMock()
    mock_agent_instance.ainvoke.side_effect = Exception("Something went wrong")
    mocker.patch('app.core.agent_service.agent', mock_agent_instance)

    response = await process_message("Error message")

    assert "Error: Something went wrong" in response
