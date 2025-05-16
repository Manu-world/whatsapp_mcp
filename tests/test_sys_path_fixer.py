import pytest
import os
import sys
import glob
from unittest.mock import patch, mock_open
from app.utils.sys_path_fixer import fix_sys_path, check_and_clean_files
from app.core.auth import is_user_active  # Import the is_user_active function

def test_fix_sys_path():
    """
    Test that fix_sys_path adds the correct path to sys.path.
    """
    original_sys_path = sys.path[:]  # Create a copy of the original sys.path
    fix_sys_path()
    # Calculate the expected path relative to the sys_path_fixer.py file
    sys_path_fixer_dir = os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "utils", "sys_path_fixer.py")))
    expected_path = os.path.abspath(os.path.join(sys_path_fixer_dir, *[".."] * 4))
    assert expected_path in sys.path
    sys.path = original_sys_path  # Restore the original sys.path


@patch("app.utils.sys_path_fixer.os.path.exists")
@patch("app.utils.sys_path_fixer.is_user_active")
def test_check_and_clean_files_user_active(mock_is_user_active, mock_exists):
    """
    Test that check_and_clean_files returns True when the user is active and credentials file exists.
    """
    mock_exists.return_value = True
    mock_is_user_active.return_value = True
    result = check_and_clean_files("test_user")
    assert result is True


@patch("app.utils.sys_path_fixer.os.path.exists")
@patch("app.utils.sys_path_fixer.is_user_active")
@patch("app.utils.sys_path_fixer.glob.glob")
@patch("app.utils.sys_path_fixer.os.remove")
def test_check_and_clean_files_user_inactive(mock_remove, mock_glob, mock_is_user_active, mock_exists):
    """
    Test that check_and_clean_files cleans up files and returns False when the user is inactive.
    """
    mock_exists.return_value = True
    mock_is_user_active.return_value = False
    mock_glob.return_value = ["test.multi.json"]

    result = check_and_clean_files("test_user")

    assert result is False
    mock_remove.assert_called()  # Check if remove was called.
    mock_is_user_active.assert_called_with("test_user")


@patch("app.utils.sys_path_fixer.os.path.exists")
@patch("app.utils.sys_path_fixer.is_user_active")
@patch("app.utils.sys_path_fixer.glob.glob")
@patch("app.utils.sys_path_fixer.os.remove")
def test_check_and_clean_files_os_error(mock_remove, mock_glob, mock_is_user_active, mock_exists):
    """
    Test that check_and_clean_files handles OSError during file deletion.
    """
    mock_exists.return_value = True
    mock_is_user_active.return_value = False
    mock_glob.return_value = ["test.multi.json"]
    mock_remove.side_effect = OSError("Failed to delete file")

    result = check_and_clean_files("test_user")

    assert result is False
    mock_remove.assert_called()
