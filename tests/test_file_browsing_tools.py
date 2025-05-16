import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.mcp_servers.gdrive.tools.file_browsing_tools import (
    ListAllFilesTool,
    ListFolderFilesTool,
    SearchFilesTool,
    GetFileMetadataTool,
    ListFilesInput,
    ListFolderFilesInput,
    SearchFilesInput,
    GetFileMetadataInput
)

@pytest.fixture
def mock_drive_service():
    with patch('app.mcp_servers.gdrive.tools.file_browsing_tools.get_drive_service') as mock_service:
        mock_drive = MagicMock()
        mock_service.return_value = mock_drive
        yield mock_drive

class TestListAllFilesTool:
    @pytest.fixture
    def tool(self):
        return ListAllFilesTool()

    def test_list_all_files_success(self, tool, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {
            'files': [{
                'id': 'file1', 'name': 'Test Document', 'mimeType': 'application/vnd.google-apps.document',
                'modifiedTime': '2023-01-01T12:00:00Z', 'owners': [{'displayName': 'Test User'}], 'size': '1024'
            }]
        }
        result = tool._run(page_size=10)
        assert "Files in Google Drive:" in result
        assert "Test Document" in result
        assert "1.00 KB" in result

    def test_list_all_files_missing_fields(self, tool, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {
            'files': [{
                'id': 'file1', 'name': 'Nameless', 'mimeType': 'application/pdf',
                'modifiedTime': '2023-01-01T12:00:00Z'
            }]
        }
        result = tool._run(page_size=10)
        assert "Nameless (application/pdf)" in result
        assert "Owner: Unknown" in result

    def test_list_all_files_empty(self, tool, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {'files': []}
        result = tool._run(page_size=10)
        assert result == "No files found in Google Drive."

    def test_list_all_files_error(self, tool, mock_drive_service):
        mock_drive_service.files().list().execute.side_effect = Exception("API Error")
        result = tool._run(page_size=10)
        assert "Error listing files: API Error" in result

    def test_args_schema(self, tool):
        assert tool.args_schema == ListFilesInput

class TestListFolderFilesTool:
    @pytest.fixture
    def tool(self):
        return ListFolderFilesTool()

    def test_list_folder_files_success(self, tool, mock_drive_service):
        mock_drive_service.files().get().execute.return_value = {'name': 'Test Folder'}
        mock_drive_service.files().list().execute.return_value = {
            'files': [{
                'id': 'file1', 'name': 'Folder Doc', 'mimeType': 'application/vnd.google-apps.document',
                'modifiedTime': '2023-01-01T12:00:00Z', 'owners': [{'displayName': 'Test User'}], 'size': '1024'
            }]
        }
        result = tool._run(folder_id='folder1', page_size=10)
        assert "Files in 'Test Folder'" in result

    def test_list_folder_files_empty(self, tool, mock_drive_service):
        mock_drive_service.files().get().execute.return_value = {'name': 'Test Folder'}
        mock_drive_service.files().list().execute.return_value = {'files': []}
        result = tool._run(folder_id='folder1', page_size=10)
        assert result == "No files found in folder 'Test Folder'."

    def test_list_folder_name_fetch_failure(self, tool, mock_drive_service):
        mock_drive_service.files().get().execute.side_effect = Exception("Folder not found")
        mock_drive_service.files().list().execute.return_value = {'files': []}
        result = tool._run(folder_id='bad_id', page_size=10)
        assert "Folder with ID 'bad_id' not found or inaccessible." in result
        assert "Folder with ID 'bad_id' not found or inaccessible" in result

    def test_list_folder_files_error(self, tool, mock_drive_service):
        mock_drive_service.files().list().execute.side_effect = Exception("API Error")
        result = tool._run(folder_id='folder1', page_size=10)
        assert "Error listing folder files: API Error" in result

    def test_args_schema(self, tool):
        assert tool.args_schema == ListFolderFilesInput

class TestSearchFilesTool:
    @pytest.fixture
    def tool(self):
        return SearchFilesTool()

    @pytest.mark.parametrize("query,expected_mime", [
        ("document", "application/vnd.google-apps.document"),
        ("sheet", "application/vnd.google-apps.spreadsheet"),
        ("slides", "application/vnd.google-apps.presentation"),
        ("pdf", "application/pdf"),
        ("folder", "application/vnd.google-apps.folder"),
    ])
    def test_search_by_file_type(self, tool, mock_drive_service, query, expected_mime):
        mock_drive_service.files().list().execute.return_value = {
            'files': [{
                'id': 'file1', 'name': f'Test {query}', 'mimeType': expected_mime,
                'modifiedTime': '2023-01-01T12:00:00Z', 'owners': [{'displayName': 'Test User'}], 'size': '1024'
            }]
        }
        result = tool._run(query=query)
        assert f"Search results for '{query}':" in result

    def test_search_no_results(self, tool, mock_drive_service):
        mock_drive_service.files().list().execute.return_value = {'files': []}
        result = tool._run(query="nonexistent")
        assert "No files found matching 'nonexistent'." in result

    def test_search_error(self, tool, mock_drive_service):
        mock_drive_service.files().list().execute.side_effect = Exception("API Error")
        result = tool._run(query="test")
        assert "Error searching files: API Error" in result

    def test_args_schema(self, tool):
        assert tool.args_schema == SearchFilesInput

class TestGetFileMetadataTool:
    @pytest.fixture
    def tool(self):
        return GetFileMetadataTool()

    def test_get_metadata_success(self, tool, mock_drive_service):
        mock_drive_service.files().get().execute.return_value = {
            'id': 'file1', 'name': 'Test Document', 'mimeType': 'application/vnd.google-apps.document',
            'description': 'Test description', 'createdTime': '2023-01-01T12:00:00Z',
            'modifiedTime': '2023-01-02T12:00:00Z', 'viewedByMeTime': '2023-01-03T12:00:00Z',
            'size': '1024', 'version': '42', 'webViewLink': 'https://drive.google.com/file',
            'owners': [{'displayName': 'Test Owner', 'emailAddress': 'owner@test.com'}],
            'lastModifyingUser': {'displayName': 'Test Modifier', 'emailAddress': 'modifier@test.com'},
            'shared': True, 'starred': True, 'trashed': False
        }
        result = tool._run(file_id='file1')
        assert "Metadata for 'Test Document':" in result

    def test_get_metadata_folder(self, tool, mock_drive_service):
        mock_drive_service.files().get().execute.return_value = {
            'id': 'folder1', 'name': 'Test Folder', 'mimeType': 'application/vnd.google-apps.folder',
            'createdTime': '2023-01-01T12:00:00Z', 'modifiedTime': '2023-01-02T12:00:00Z',
            'owners': [{'displayName': 'Test Owner'}], 'size': '0'
        }
        result = tool._run(file_id='folder1')
        assert "Metadata for 'Test Folder':" in result
        assert "Type: Folder" in result
        assert "Size: 0 B" in result

    def test_get_metadata_missing_optional_fields(self, tool, mock_drive_service):
        mock_drive_service.files().get().execute.return_value = {
            'id': 'file1', 'name': 'Test File', 'mimeType': 'application/pdf',
            'createdTime': '2023-01-01T12:00:00Z', 'modifiedTime': '2023-01-01T12:00:00Z',
            'size': '2048'
        }
        result = tool._run(file_id='file1')
        assert "Metadata for 'Test File':" in result
        assert "Size: 2.00 KB" in result
        assert "Owner: Unknown" in result

    @pytest.mark.parametrize("size,expected", [
        ("1023", "1023 B"),
        ("1024", "1.00 KB"),
        (str(1024 * 1024), "1.00 MB"),
        (str(1024 * 1024 * 3), "3.00 MB"),
        (str(1024 * 1024 * 1024), "1024.00 MB"),
    ])
    def test_size_formatting(self, tool, mock_drive_service, size, expected):
        mock_drive_service.files().get().execute.return_value = {
            'id': 'file1', 'name': 'Big File', 'mimeType': 'application/pdf',
            'createdTime': '2023-01-01T12:00:00Z', 'modifiedTime': '2023-01-01T12:00:00Z',
            'size': size, 'owners': [{'displayName': 'Owner'}]
        }
        result = tool._run(file_id='file1')
        assert f"Size: {expected}" in result

    def test_get_metadata_not_found(self, tool, mock_drive_service):
        mock_drive_service.files().get().execute.side_effect = Exception("Not found")
        result = tool._run(file_id='nonexistent')
        assert "Error retrieving file metadata: Not found" in result

    def test_args_schema(self, tool):
        assert tool.args_schema == GetFileMetadataInput
