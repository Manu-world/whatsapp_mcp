import pytest
import os
import json
from unittest.mock import MagicMock, patch, call
import logging
import sys

# Fixture to clean environment variables
@pytest.fixture(autouse=True)
def clean_env():
    """Clears and restores environment variables after each test."""
    original_environ = dict(os.environ)
    os.environ.clear() # Clear environment variables for isolation
    yield # Run the test
    os.environ.clear()
    os.environ.update(original_environ)

# Fixture to mock boto3 client and methods globally for config tests
@pytest.fixture
def mock_boto3_secretsmanager_global(mocker):
    """Mocks boto3.client and secrets manager methods for module-level patching."""
    mock_client = MagicMock()
    # Patch boto3.client globally, but don't use before_import here.
    # Individual tests will manage patching before_import if needed for module import.
    mock_boto3 = mocker.patch('boto3.client', return_value=mock_client)
    mock_get_secret_value = mock_client.get_secret_value
    return mock_boto3, mock_get_secret_value

# Fixture to mock dotenv.load_dotenv globally for config tests
@pytest.fixture
def mock_load_dotenv_global(mocker):
    """Mocks dotenv.load_dotenv for module-level patching."""
    # Patch dotenv.load_dotenv globally
    mock_load_dotenv = mocker.patch('dotenv.load_dotenv')
    return mock_load_dotenv

# Fixture to mock the twilio Client globally for config tests
@pytest.fixture
def mock_twilio_client_global(mocker):
    """Mocks twilio.rest.Client for module-level patching."""
    # Patch twilio.rest.Client globally
    mock_client_cls = mocker.patch('twilio.rest.Client')
    return mock_client_cls

# Helper to import the config module after patching
def import_config(env_vars=None, patches=None):
    """Imports the config module after necessary patches are applied,
       optionally setting temporary environment variables and applying patches."""
    original_environ = dict(os.environ)
    if env_vars:
        os.environ.update(env_vars)

    # Apply patches before importing
    applied_patchers = []
    applied_mocks = []
    if patches:
        for patch_target, patch_return in patches:
            if isinstance(patch_return, dict):
                # Handle dictionary specification for mock behavior
                if 'return_value' in patch_return:
                    patcher = patch(patch_target, return_value=patch_return['return_value'])
                elif 'side_effect' in patch_return:
                    patcher = patch(patch_target, side_effect=patch_return['side_effect'])
                else:
                    # Create a MagicMock for empty specs
                    mock = MagicMock()
                    patcher = patch(patch_target, return_value=mock)
            else:
                # Use the provided mock object directly
                patcher = patch(patch_target, new=patch_return)

            mock_obj = patcher.start()
            applied_patchers.append(patcher)
            applied_mocks.append(mock_obj)

    # Need to remove from sys.modules if it was already imported in a previous test
    if 'app.core.config' in sys.modules:
        del sys.modules['app.core.config']

    config = None # Initialize config to None
    try:
        from app.core import config as imported_config
        config = imported_config # Assign imported module to config
    finally:
        # Stop patches after import
        for patcher in reversed(applied_patchers):
            patcher.stop()
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(original_environ)

    # Return both the config module and the applied mocks for assertions
    return config, applied_mocks


def test_load_secrets_manager_success(mock_boto3_secretsmanager_global, mocker):
    """Tests successful loading of secrets from AWS Secrets Manager."""
    _, mock_get_secret_value = mock_boto3_secretsmanager_global
    mock_secret_string = json.dumps({"key": "value", "list": [1, 2]})
    mock_get_secret_value.return_value = {"SecretString": mock_secret_string}

    # Create a MagicMock for bootstrap_config that does nothing
    mock_bootstrap = MagicMock()

    # Mock bootstrap_config before import to prevent its call during import
    patches = [('app.core.config.bootstrap_config', mock_bootstrap)]

    # Import the module after patching, providing necessary env vars
    config, mocks = import_config({'OPENAI_API_KEY': 'dummy_key'}, patches=patches)

    # Reset the mock to clear any calls during import
    mock_get_secret_value.reset_mock()

    # Now, call load_secrets_manager directly in the test
    result = config.load_secrets_manager("test-secret")

    # Assert that get_secret_value was called only once by the direct call
    mock_get_secret_value.assert_called_once_with(SecretId="test-secret")

    # Verify the result
    assert result == {"key": "value", "list": [1, 2]}


def test_load_secrets_manager_failure(mock_boto3_secretsmanager_global, mocker):
    """Tests failure to load secrets from AWS Secrets Manager."""
    _, mock_get_secret_value = mock_boto3_secretsmanager_global
    mock_get_secret_value.side_effect = Exception("AWS error")

    # Create a MagicMock for bootstrap_config that does nothing
    mock_bootstrap = MagicMock()

    # Mock bootstrap_config before import
    patches = [('app.core.config.bootstrap_config', mock_bootstrap)]

    # Import the module after patching, providing necessary env vars
    config, mocks = import_config({'OPENAI_API_KEY': 'dummy_key'}, patches=patches)

    # Reset the mock to clear any calls during import
    mock_get_secret_value.reset_mock()

    # Now test the direct call to load_secrets_manager
    with pytest.raises(Exception, match="AWS error"):
        config.load_secrets_manager("test-secret")

    # Assert that get_secret_value was called only once by the direct call
    mock_get_secret_value.assert_called_once_with(SecretId="test-secret")


def test_apply_env_vars():
    """Tests that apply_env_vars correctly sets environment variables."""
    env_dict = {"VAR1": "value1", "VAR2": "value2"}
    # Import to get the function definition, no special env needed for this function test itself
    config, _ = import_config({'OPENAI_API_KEY': 'dummy_key'}) # Added dummy key for successful import
    config.apply_env_vars(env_dict)

    assert os.environ.get("VAR1") == "value1"
    assert os.environ.get("VAR2") == "value2"
    assert "VAR3" not in os.environ


def test_bootstrap_config_aws_success(
    mock_boto3_secretsmanager_global, mock_load_dotenv_global, mocker
):
    """Tests bootstrap_config when loading secrets from AWS succeeds."""
    # 1. Mock os.getenv for critical values needed during config.py import or direct call
    #    OPENAI_API_KEY is set at module level in config.py
    mocker.patch(
        "os.getenv",
        side_effect=lambda key, default=None: "dummy_openai_key"
        if key == "OPENAI_API_KEY"
        else os.environ.get(key, default),  # Fallback to actual env or default
    )

    # 2. Mock os.environ.__setitem__ for safe assignment (already present and good)
    orig_setitem = os.environ.__setitem__

    def safe_setitem(key, value):
        if value is not None:
            orig_setitem(key, value)

    mocker.patch.object(os.environ, "__setitem__", side_effect=safe_setitem)

    # 3. Mock print to avoid console output during test
    mocker.patch("builtins.print")

    # 4. Import the config module.
    #    `bootstrap_config()` runs at import. It might call `load_dotenv` if AWS part fails.
    #    `mock_boto3_secretsmanager_global` is active. If its `get_secret_value` isn't
    #    pre-configured with a side_effect to handle both secret IDs with valid JSON,
    #    the import-time `bootstrap_config` will likely fall into its except block.
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    from app.core import config as config_module

    # 5. Set up mocks for the *direct* call to bootstrap_config
    #    Define side_effect for our patched load_secrets_manager
    def mock_load_secrets_side_effect(secret_name):
        if secret_name == "google_drive_mcp_secrets":
            return {"ENV_VARS": {"AWS_VAR": "aws_value"}, "other_key": "other_value"}
        elif secret_name == "gcp-oauth-keys":  # This is called by process_secret
            return {"GCP_OAUTH_KEYS": json.dumps({"web": {"client_id": "test-id"}})}
        raise Exception(
            f"Unexpected secret_name in mock_load_secrets_side_effect: {secret_name}"
        )

    mock_load_secrets_manager = mocker.patch.object(
        config_module, "load_secrets_manager", side_effect=mock_load_secrets_side_effect
    )

    # Spy on process_secret to let its original code run (which calls load_secrets_manager again)
    mock_process_secret = mocker.spy(config_module, "process_secret")

    # Mock builtins.open to prevent actual file I/O by the spied process_secret
    mock_file_open = mocker.patch("builtins.open", mocker.mock_open())

    # Spy on apply_env_vars
    mock_apply_env_vars = mocker.spy(config_module, "apply_env_vars")

    # 6. Reset mocks to clear calls from import phase or patching setup
    mock_load_secrets_manager.reset_mock()
    mock_apply_env_vars.reset_mock()
    mock_load_dotenv_global.reset_mock()  # Crucial: was likely called during import
    mock_process_secret.reset_mock()
    mock_file_open.reset_mock()

    # 7. Call bootstrap_config directly
    config_module.bootstrap_config()

    # 8. Assertions
    assert mock_load_secrets_manager.call_count == 2
    mock_load_secrets_manager.assert_has_calls(
        [call("google_drive_mcp_secrets"), call("gcp-oauth-keys")],
        any_order=False,  # process_secret is called after the first load, so order is specific
    )
    mock_apply_env_vars.assert_called_once_with({"AWS_VAR": "aws_value"})
    mock_process_secret.assert_called_once_with("gcp-oauth-keys")
    mock_file_open.assert_called_once_with("gcp-oauth.keys.json", "w")
    mock_load_dotenv_global.assert_not_called()


def test_bootstrap_config_aws_failure_fallback_dotenv(mock_boto3_secretsmanager_global, mocker):
    """Tests bootstrap_config when AWS secrets loading fails and it falls back to dotenv."""
    # First patch os.getenv to return a dummy key for OPENAI_API_KEY
    mocker.patch('os.getenv', side_effect=lambda key, default=None:
                'dummy_key' if key == 'OPENAI_API_KEY' else default)

    # Patch os.environ.__setitem__ to handle the None value case
    orig_setitem = os.environ.__setitem__
    def safe_setitem(key, value):
        # Only set environment variables with non-None values
        if value is not None:
            orig_setitem(key, value)
    mocker.patch.object(os.environ, '__setitem__', side_effect=safe_setitem)

    # Important: Do NOT use the fixture mock_load_dotenv_global here
    # We'll create our own mock for dotenv.load_dotenv before importing the module
    mock_load_dotenv = mocker.patch('dotenv.load_dotenv')

    # Import the module - bootstrap_config will run during import
    if 'app.core.config' in sys.modules:
        del sys.modules['app.core.config']

    # When the module is imported, we need to temporarily patch bootstrap_config
    # to prevent it from running during import (we'll test it directly)
    with patch('app.core.config.bootstrap_config', autospec=True):
        from app.core import config as config_module

    # Now that the module is imported, patch load_secrets_manager to raise an exception
    mock_load_secrets_manager = mocker.patch.object(
        config_module,
        'load_secrets_manager',
        side_effect=Exception("AWS connection error")
    )

    mock_apply_env_vars = mocker.spy(config_module, 'apply_env_vars')

    # Reset the mock_load_dotenv to clear any calls during import
    mock_load_dotenv.reset_mock()

    # Call bootstrap_config directly to test it
    config_module.bootstrap_config()

    # Assert on the mocks
    mock_load_secrets_manager.assert_called_once()
    mock_apply_env_vars.assert_not_called()
    mock_load_dotenv.assert_called_once_with(override=False)


def test_setup_logging_production(mocker, clean_env):
    """Tests setup_logging in production environment."""
    # Create a patched bootstrap_config to prevent its execution during import
    mock_bootstrap = mocker.patch('app.core.config.bootstrap_config', autospec=True)
    patches = [('app.core.config.bootstrap_config', mock_bootstrap)]

    # Set ENVIRONMENT to production before importing
    config, _ = import_config({'ENVIRONMENT': 'production', 'OPENAI_API_KEY': 'dummy_key'}, patches=patches)

    # Reset the environment variable to make sure it's read correctly inside setup_logging
    os.environ['ENVIRONMENT'] = 'production'

    mock_get_logger = mocker.patch('logging.getLogger')
    mock_logger_instance = mocker.MagicMock()
    mock_get_logger.return_value = mock_logger_instance
    mock_stream_handler_cls = mocker.patch('logging.StreamHandler')
    mock_stream_handler_instance = mocker.MagicMock()
    mock_stream_handler_cls.return_value = mock_stream_handler_instance
    mock_formatter_cls = mocker.patch('logging.Formatter')
    mock_formatter_instance = mocker.MagicMock()
    mock_formatter_cls.return_value = mock_formatter_instance

    # Call setup_logging
    logger = config.setup_logging()

    # Assert
    mock_get_logger.assert_called_once()
    mock_logger_instance.setLevel.assert_called_once_with(logging.INFO)
    assert mock_logger_instance.handlers == []  # Check handlers are cleared
    mock_formatter_cls.assert_called_once_with("%(asctime)s - %(levelname)s - %(message)s")
    mock_stream_handler_cls.assert_called_once_with(sys.stdout)
    mock_stream_handler_instance.setFormatter.assert_called_once_with(mock_formatter_instance)
    mock_logger_instance.addHandler.assert_called_once_with(mock_stream_handler_instance)
    mock_logger_instance.info.assert_called_once_with(
        "Logging initialised in new production environment at 20 level"
    )
    assert logger == mock_logger_instance


def test_setup_logging_development(mocker, clean_env):
    """Tests setup_logging in development environment."""
    # Create a patched bootstrap_config to prevent its execution during import
    mock_bootstrap = MagicMock()
    patches = [('app.core.config.bootstrap_config', mock_bootstrap)]

    # Set ENVIRONMENT before importing and provide other necessary env vars
    env_vars = {'ENVIRONMENT': 'development', 'OPENAI_API_KEY': 'dummy_key'}
    config, _ = import_config(env_vars, patches=patches)

    mock_get_logger = mocker.patch('logging.getLogger')
    mock_logger_instance = MagicMock()
    mock_get_logger.return_value = mock_logger_instance
    mock_stream_handler_cls = mocker.patch('logging.StreamHandler')
    mock_stream_handler_instance = MagicMock()
    mock_stream_handler_cls.return_value = mock_stream_handler_instance
    mock_formatter_cls = mocker.patch('logging.Formatter')
    mock_formatter_instance = MagicMock()
    mock_formatter_cls.return_value = mock_formatter_instance

    logger = config.setup_logging()

    mock_get_logger.assert_called_once()
    mock_logger_instance.setLevel.assert_called_once_with(logging.DEBUG)
    assert mock_logger_instance.handlers == []  # Check handlers are cleared
    mock_formatter_cls.assert_called_once_with(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    mock_stream_handler_cls.assert_called_once_with(sys.stdout)
    mock_stream_handler_instance.setFormatter.assert_called_once_with(mock_formatter_instance)
    mock_logger_instance.addHandler.assert_called_once_with(mock_stream_handler_instance)
    mock_logger_instance.info.assert_called_once_with(
        "Logging initialised in new development environment at 10 level"
    )  # logging.DEBUG is 10
    assert logger == mock_logger_instance


def test_setup_logging_default_environment(mocker, clean_env):
    """Tests setup_logging when ENVIRONMENT is not set (defaults to development)."""
    # Create a patched bootstrap_config to prevent its execution during import
    mock_bootstrap = MagicMock()
    patches = [('app.core.config.bootstrap_config', mock_bootstrap)]

    # Ensure ENVIRONMENT is not set and provide other necessary env vars
    env_vars = {'OPENAI_API_KEY': 'dummy_key'}
    config, _ = import_config(env_vars, patches=patches)

    mock_get_logger = mocker.patch('logging.getLogger')
    mock_logger_instance = MagicMock()
    mock_get_logger.return_value = mock_logger_instance
    mock_stream_handler_cls = mocker.patch('logging.StreamHandler')
    mock_stream_handler_instance = MagicMock()
    mock_stream_handler_cls.return_value = mock_stream_handler_instance
    mock_formatter_cls = mocker.patch('logging.Formatter')
    mock_formatter_instance = MagicMock()
    mock_formatter_cls.return_value = mock_formatter_instance

    logger = config.setup_logging()

    mock_get_logger.assert_called_once()
    mock_logger_instance.setLevel.assert_called_once_with(logging.DEBUG)
    assert mock_logger_instance.handlers == []  # Check handlers are cleared
    mock_formatter_cls.assert_called_once_with(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    mock_stream_handler_cls.assert_called_once_with(sys.stdout)
    mock_stream_handler_instance.setFormatter.assert_called_once_with(mock_formatter_instance)
    mock_logger_instance.addHandler.assert_called_once_with(mock_stream_handler_instance)
    mock_logger_instance.info.assert_called_once_with(
        "Logging initialised in new development environment at 10 level"
    )
    assert logger == mock_logger_instance


def test_global_variables_and_client_init(mock_boto3_secretsmanager_global, mock_load_dotenv_global, mock_twilio_client_global, mocker):
    """Tests that global variables and twilio_client are initialized correctly on import."""
    # Create a patched bootstrap_config to prevent its execution during import
    mock_bootstrap = MagicMock()
    mock_load_secrets = MagicMock(return_value={"ENV_VARS": {}})

    patches = [
        ('app.core.config.bootstrap_config', mock_bootstrap),
        ('app.core.config.load_secrets_manager', mock_load_secrets)
    ]

    # Arrange: Set up environment variables to be used by import_config
    env_vars = {
        'TWILIO_ACCOUNT_SID': 'AC_mock_sid',
        'TWILIO_AUTH_TOKEN': 'mock_auth_token',
        'TWILIO_WHATSAPP_NUMBER': '+1234567890',
        'GOAUTH_REDIRECT_URL': 'http://test.com',
        'OPENAI_API_KEY': 'mock_openai_key',
        'AWS_REGION': 'us-east-1'  # Test overriding default REGION
    }

    # Act: Import the module - this triggers the global variable assignments and client init
    config, _ = import_config(env_vars, patches=patches)

    # Assert: Check if global variables are set correctly by reading the config module
    assert config.REGION == 'us-east-1'  # Check the variable within the imported module
    assert config.SECRET_NAME == 'google_drive_mcp_secrets'  # Should not be overridden by env var
    assert config.TWILIO_ACCOUNT_SID == 'AC_mock_sid'
    assert config.TWILIO_AUTH_TOKEN == 'mock_auth_token'
    assert config.TWILIO_WHATSAPP_NUMBER == '+1234567890'
    assert config.GOAUTH_REDIRECT_URL == 'http://test.com'

    # Don't check os.environ since it would have been cleared
    # Instead check that the "os.environ" was set during module import
    # We can verify this indirectly by making sure the right code was executed

    # Assert: Check if twilio_client was initialized correctly
    mock_twilio_client_global.assert_called_once_with('AC_mock_sid', 'mock_auth_token')
    assert config.twilio_client == mock_twilio_client_global.return_value

    # Assert: Check MCP_CONFIG structure (static dictionary)
    assert isinstance(config.MCP_CONFIG, dict)
    assert "gdrive" in config.MCP_CONFIG
    assert "gmail" in config.MCP_CONFIG
    assert config.MCP_CONFIG["gdrive"]["command"] == "python3"
    assert config.MCP_CONFIG["gdrive"]["args"] == ["app/mcp_servers/gdrive/server/drive_mcp_server.py"]
    assert config.MCP_CONFIG["gdrive"]["transport"] == "stdio"
    assert config.MCP_CONFIG["gmail"]["command"] == "npx"
    assert config.MCP_CONFIG["gmail"]["args"] == ["@gongrzhe/server-gmail-autoauth-mcp"]


def test_global_variables_default_goauth_redirect_url(mock_boto3_secretsmanager_global, mock_load_dotenv_global, mock_twilio_client_global, mocker):
    """Tests that GOAUTH_REDIRECT_URL defaults correctly when not set."""
    # Create a patched bootstrap_config to prevent its execution during import
    mock_bootstrap = MagicMock()
    mock_load_secrets = MagicMock(return_value={"ENV_VARS": {}})

    patches = [
        ('app.core.config.bootstrap_config', mock_bootstrap),
        ('app.core.config.load_secrets_manager', mock_load_secrets)
    ]

    # Arrange: Set up environment variables to be used by import_config, omit GOAUTH_REDIRECT_URL
    env_vars = {
        'TWILIO_ACCOUNT_SID1': 'AC_mock_sid',
        'TWILIO_AUTH_TOKEN1': 'mock_auth_token',
        'TWILIO_WHATSAPP_NUMBER1': '+1234567890',
        # Omit GOAUTH_REDIRECT_URL
        'OPENAI_API_KEY': 'mock_openai_key',
    }

    # Act: Import the module
    config, _ = import_config(env_vars, patches=patches)

    # Assert: Check if GOAUTH_REDIRECT_URL defaulted correctly
    assert config.GOAUTH_REDIRECT_URL == "http://localhost:8000"


# Additional test to ensure load_secrets_manager is called by bootstrap_config
def test_bootstrap_calls_load_secrets_manager(mock_boto3_secretsmanager_global, mock_load_dotenv_global, mocker):
    """Ensures bootstrap_config attempts to call load_secrets_manager."""
    # Patch os.getenv to return a dummy key for OPENAI_API_KEY
    mocker.patch('os.getenv', side_effect=lambda key, default=None:
                'dummy_key' if key == 'OPENAI_API_KEY' else default)

    # Patch os.environ.__setitem__ to handle None values safely
    orig_setitem = os.environ.__setitem__
    def safe_setitem(key, value):
        # Only set environment variables with non-None values
        if value is not None:
            orig_setitem(key, value)
    mocker.patch.object(os.environ, '__setitem__', side_effect=safe_setitem)

    # Now we can safely import the module
    if 'app.core.config' in sys.modules:
        del sys.modules['app.core.config']

    # Import with bootstrap_config temporarily patched
    with patch('app.core.config.bootstrap_config', autospec=True):
        from app.core import config as config_module

    # The key change: we need to remove any patches applied to load_secrets_manager
    # during module import before we set up our own patch
    if hasattr(config_module.load_secrets_manager, '__wrapped__'):
        # If the function is already patched, restore the original
        while hasattr(config_module.load_secrets_manager, '__wrapped__'):
            config_module.load_secrets_manager = config_module.load_secrets_manager.__wrapped__

    # Now patch load_secrets_manager to fail when called directly in our test
    # Use side_effect to raise the expected exception
    mock_load_secrets = mocker.patch.object(
        config_module,
        'load_secrets_manager',
        side_effect=Exception("Simulated failure")
    )

    # Add a spy to verify dotenv.load_dotenv is called as a fallback
    mock_load_dotenv_spy = mocker.spy(config_module, 'load_dotenv')

    # Call bootstrap_config directly - it should catch the exception and
    # use the fallback method (load_dotenv)
    config_module.bootstrap_config()

    # Verify load_secrets_manager was called
    mock_load_secrets.assert_called_once()

    # Verify that load_dotenv was called as a fallback
    mock_load_dotenv_spy.assert_called_once_with(override=False)
