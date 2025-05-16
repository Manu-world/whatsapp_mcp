"""
Google Drive AI Agent: File Browsing & Metadata
This agent provides tools to interact with Google Drive for browsing files and retrieving metadata.
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import datetime

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from googleapiclient.http import MediaFileUpload
from app.core.auth import get_drive_service


# Define schemas for each tool
class ListFilesInput(BaseModel):
    page_size: int = Field(default=10, description="Maximum number of files to return")
    
class ListFolderFilesInput(BaseModel):
    folder_id: str = Field(..., description="The ID of the folder to list files from")
    page_size: int = Field(default=10, description="Maximum number of files to return")

class SearchFilesInput(BaseModel):
    query: str = Field(..., description="Search query. Can include file name, file type('document', 'doc', 'docs' for word document files, 'spreadsheet', 'sheet', 'sheets' for excel or spreadsheet files, 'presentation', 'slides' for powerpoint files, 'pdf' for pdf files, 'folder', 'directory' for folders or directories), or content keywords")
    page_size: int = Field(default=10, description="Maximum number of files to return")

class GetFileMetadataInput(BaseModel):
    file_id: str = Field(..., description="The ID of the file to get metadata for")

# Define the tools
class ListAllFilesTool(BaseTool):
    name: str = "list_all_files"
    description: str = "Lists all files in Google Drive. Use when you need to get an overview of all files."
    args_schema: type[ListFilesInput] = ListFilesInput
    
    def _run(self, page_size: int = 10) -> str:
        """Lists all files in Google Drive."""
        try:
            service = get_drive_service()
            results = service.files().list(
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, owners, parents)"
            ).execute()
            items = results.get('files', [])
            
            if not items:
                return "No files found in Google Drive."
            
            files_info = []
            for item in items:
                file_type = item.get('mimeType', 'Unknown type')
                modified_time = item.get('modifiedTime', 'Unknown')
                if modified_time != 'Unknown':
                    # Convert to a more readable format
                    modified_time = datetime.datetime.fromisoformat(modified_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                
                owner = "Unknown"
                if 'owners' in item and item['owners']:
                    owner = item['owners'][0].get('displayName', 'Unknown')
                
                size = item.get('size', 'Unknown')
                if size != 'Unknown':
                    # Convert size to a readable format
                    size = f"{int(size) / 1024:.2f} KB" if int(size) < 1024 * 1024 else f"{int(size) / (1024 * 1024):.2f} MB"
                
                files_info.append({
                    'id': item['id'],
                    'name': item['name'],
                    'type': file_type,
                    'modified': modified_time,
                    'owner': owner,
                    'size': size
                })
            
            # Format the output
            output = "Files in Google Drive:\n\n"
            for idx, file in enumerate(files_info, 1):
                output += f"{idx}. {file['name']} ({file['type']})\n"
                output += f"   ID: {file['id']}\n"
                output += f"   Modified: {file['modified']}\n"
                output += f"   Owner: {file['owner']}\n"
                output += f"   Size: {file['size']}\n\n"
            
            return output
        
        except Exception as e:
            return f"Error listing files: {str(e)}"

class ListFolderFilesTool(BaseTool):
    name: str = "list_folder_files"
    description: str = "Lists files in a specific folder in Google Drive. Use when you need to explore the contents of a particular folder."
    args_schema: type[ListFolderFilesInput] = ListFolderFilesInput
    
    def _run(self, folder_id: str, page_size: int = 10) -> str:
        """Lists files in a specific folder in Google Drive."""
        try:
            service = get_drive_service()
            query = f"'{folder_id}' in parents"
            results = service.files().list(
                q=query,
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, owners)"
            ).execute()
            items = results.get('files', [])
            
            if not items:
                # First verify that the folder exists
                try:
                    folder = service.files().get(fileId=folder_id).execute()
                    return f"No files found in folder '{folder['name']}'."
                except:
                    return f"Folder with ID '{folder_id}' not found or inaccessible."
            
            files_info = []
            for item in items:
                file_type = item.get('mimeType', 'Unknown type')
                modified_time = item.get('modifiedTime', 'Unknown')
                if modified_time != 'Unknown':
                    modified_time = datetime.datetime.fromisoformat(modified_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                
                owner = "Unknown"
                if 'owners' in item and item['owners']:
                    owner = item['owners'][0].get('displayName', 'Unknown')
                
                size = item.get('size', 'Unknown')
                if size != 'Unknown':
                    size = f"{int(size) / 1024:.2f} KB" if int(size) < 1024 * 1024 else f"{int(size) / (1024 * 1024):.2f} MB"
                
                files_info.append({
                    'id': item['id'],
                    'name': item['name'],
                    'type': file_type,
                    'modified': modified_time,
                    'owner': owner,
                    'size': size
                })
            
            # Get folder name for better output
            try:
                folder = service.files().get(fileId=folder_id, fields="name").execute()
                folder_name = folder.get('name', 'Unknown folder')
            except Exception as e:
                folder_name = "Folder"
            
            # Format the output
            output = f"Files in '{folder_name}' (ID: {folder_id}):\n\n"
            for idx, file in enumerate(files_info, 1):
                output += f"{idx}. {file['name']} ({file['type']})\n"
                output += f"   ID: {file['id']}\n"
                output += f"   Modified: {file['modified']}\n"
                output += f"   Owner: {file['owner']}\n"
                output += f"   Size: {file['size']}\n\n"
            
            return output
        
        except Exception as e:
            return f"Error listing folder files: {str(e)}"

class SearchFilesTool(BaseTool):
    name: str = "search_files"
    description: str = "Searches for specific files in Google Drive Searches for files by name, file type(pdf, document, docs, sheet, folder etc..), or content. Use when looking for specific files."
    args_schema: type[SearchFilesInput] = SearchFilesInput
    
    def _run(self, query: str, page_size: int = 10) -> str:
        """Searches for files in Google Drive by name, file type(or file extension), or content keywords."""
        try:
            service = get_drive_service()
            
            # Handle common file type searches more intuitively
            if query.lower() in ['document', 'doc', 'docs', 'type:document', 'type:doc', 'type:docs']:
                search_query = "mimeType = 'application/vnd.google-apps.document'"
            elif query.lower() in ['spreadsheet', 'sheet', 'sheets', 'type:spreadsheet', 'type:sheet', 'type:sheets']:
                search_query = "mimeType = 'application/vnd.google-apps.spreadsheet'"
            elif query.lower() in ['presentation', 'slides', 'type:presentation', 'type:slides']:
                search_query = "mimeType = 'application/vnd.google-apps.presentation'"
            elif query.lower() in ['pdf', 'type:pdf']:
                search_query = "mimeType = 'application/pdf'"
            elif query.lower() in ['folder', 'directory', 'type:folder', 'type:directory']:
                search_query = "mimeType = 'application/vnd.google-apps.folder'"
            else:
                words = query.split()
                name_terms = [f"name contains '{word}'" for word in words]
                content_terms = [f"fullText contains '{word}'" for word in words]
                
                name_query = " or ".join(name_terms)
                content_query = " or ".join(content_terms)
                search_query = f"({name_query}) and ({content_query})"
            
            results = service.files().list(
                q=search_query,
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, owners, parents)"
            ).execute()
            
            items = results.get('files', [])
            
            if not items:
                return f"No files found matching '{query}'."
            
            files_info = []
            for item in items:
                file_type = item.get('mimeType', 'Unknown type')
                # Convert Google Drive mime types to more readable formats
                if file_type == 'application/vnd.google-apps.document':
                    file_type = 'Google Doc'
                elif file_type == 'application/vnd.google-apps.spreadsheet':
                    file_type = 'Google Sheet'
                elif file_type == 'application/vnd.google-apps.presentation':
                    file_type = 'Google Slides'
                elif file_type == 'application/vnd.google-apps.folder':
                    file_type = 'Folder'
                    
                modified_time = item.get('modifiedTime', 'Unknown')
                if modified_time != 'Unknown':
                    modified_time = datetime.datetime.fromisoformat(modified_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                
                owner = "Unknown"
                if 'owners' in item and item['owners']:
                    owner = item['owners'][0].get('displayName', 'Unknown')
                
                size = item.get('size', 'Unknown')
                if size != 'Unknown':
                    size = f"{int(size) / 1024:.2f} KB" if int(size) < 1024 * 1024 else f"{int(size) / (1024 * 1024):.2f} MB"
                else:
                    if file_type == 'Folder':
                        size = 'N/A'
                
                files_info.append({
                    'id': item['id'],
                    'name': item['name'],
                    'type': file_type,
                    'modified': modified_time,
                    'owner': owner,
                    'size': size
                })
            
            # Format the output
            output = f"Search results for '{query}':\n\n"
            for idx, file in enumerate(files_info, 1):
                output += f"{idx}. {file['name']} ({file['type']})\n"
                output += f"   ID: {file['id']}\n"
                output += f"   Modified: {file['modified']}\n"
                output += f"   Owner: {file['owner']}\n"
                output += f"   Size: {file['size']}\n\n"
            
            return output
        
        except Exception as e:
            return f"Error searching files: {str(e)}"

class GetFileMetadataTool(BaseTool):
    name: str = "get_file_metadata"
    description: str = "Gets detailed metadata for a specific file in Google Drive. Use when you need comprehensive information about a particular file."
    args_schema: type[GetFileMetadataInput] = GetFileMetadataInput
    
    def _run(self, file_id: str) -> str:
        """Gets detailed metadata for a file."""
        try:
            service = get_drive_service()
            # metadata
            file = service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, description, createdTime, modifiedTime, modifiedByMeTime, viewedByMeTime, "
                       "size, version, webViewLink, iconLink, thumbnailLink, owners, sharingUser, shared, " 
                       "lastModifyingUser, capabilities, permissions, starred, trashed"
            ).execute()
            
            if not file:
                return f"No file found with ID '{file_id}'."
            
            # Process the file data for human-friendly output
            mime_type = file.get('mimeType', 'Unknown type')
            # Convert Google Drive mime types to more readable formats
            file_type = "Unknown type"
            if mime_type == 'application/vnd.google-apps.document':
                file_type = 'Google Doc'
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                file_type = 'Google Sheet'
            elif mime_type == 'application/vnd.google-apps.presentation':
                file_type = 'Google Slides'
            elif mime_type == 'application/vnd.google-apps.folder':
                file_type = 'Folder'
            elif mime_type == 'application/pdf':
                file_type = 'PDF'
            elif 'image/' in mime_type:
                file_type = 'Image'
            elif 'video/' in mime_type:
                file_type = 'Video'
            elif 'audio/' in mime_type:
                file_type = 'Audio'
            elif 'text/' in mime_type:
                file_type = 'Text'
            else:
                file_type = mime_type
            
            # Format timestamps
            created_time = "Unknown"
            if 'createdTime' in file:
                created_time = datetime.datetime.fromisoformat(file['createdTime'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            
            modified_time = "Unknown"
            if 'modifiedTime' in file:
                modified_time = datetime.datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            
            # Format size
            size = file.get('size', 'Unknown')
            if size != 'Unknown':
                size_int = int(size)
                if size_int < 1024:
                    size = f"{size_int} B"
                elif size_int < 1024 * 1024:
                    size = f"{size_int / 1024:.2f} KB"
                else:
                    size = f"{size_int / (1024 * 1024):.2f} MB"
            
            # Get owner information
            owner = "Unknown"
            if 'owners' in file and file['owners']:
                owner = file['owners'][0].get('displayName', 'Unknown')
                owner_email = file['owners'][0].get('emailAddress', 'Unknown')
                owner = f"{owner} ({owner_email})"
            
            # Last modified by
            last_modifier = "Unknown"
            if 'lastModifyingUser' in file:
                last_modifier = file['lastModifyingUser'].get('displayName', 'Unknown')
                last_modifier_email = file['lastModifyingUser'].get('emailAddress', 'Unknown')
                last_modifier = f"{last_modifier} ({last_modifier_email})"
            
            # Format the output
            output = f"Metadata for '{file['name']}':\n\n"
            output += f"Basic Information:\n"
            output += f"- File ID: {file['id']}\n"
            output += f"- Name: {file['name']}\n"
            output += f"- Type: {file_type} ({mime_type})\n"
            output += f"- Size: {size}\n"
            output += f"- Version: {file.get('version', 'Unknown')}\n\n"
            
            output += f"Timestamps:\n"
            output += f"- Created: {created_time}\n"
            output += f"- Modified: {modified_time}\n"
            if 'viewedByMeTime' in file:
                viewed_time = datetime.datetime.fromisoformat(file['viewedByMeTime'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                output += f"- Last viewed: {viewed_time}\n\n"
            else:
                output += f"- Last viewed: Never or Unknown\n\n"
            
            output += f"Ownership & Sharing:\n"
            output += f"- Owner: {owner}\n"
            output += f"- Last modified by: {last_modifier}\n"
            output += f"- Shared: {'Yes' if file.get('shared', False) else 'No'}\n"
            
            if 'description' in file and file['description']:
                output += f"\nDescription:\n{file['description']}\n"
            
            if 'webViewLink' in file:
                output += f"\nWeb link: {file['webViewLink']}\n"
            
            # Additional flags
            flags = []
            if file.get('starred', False):
                flags.append("Starred")
            if file.get('trashed', False):
                flags.append("In trash")
            
            if flags:
                output += f"\nFlags: {', '.join(flags)}\n"
            
            return output
        
        except Exception as e:
            return f"Error retrieving file metadata: {str(e)}"

class UploadFileInput(BaseModel):
    file_path: str = Field(..., description="Path to the local file to upload")
    folder_id: Optional[str] = Field(None, description="Optional Google Drive folder ID to upload the file into")

class UploadFileToDriveTool(BaseTool):
    name: str = "upload_file_to_drive"
    description: str = "Uploads a local file to Google Drive. Optionally specify a folder to upload into."
    args_schema: type[UploadFileInput] = UploadFileInput

    def _run(self, file_path: str, folder_id: Optional[str] = None) -> str:
        try:
            service = get_drive_service()
            file_metadata = {'name': os.path.basename(file_path)}
            if folder_id:
                file_metadata['parents'] = [folder_id]

            media = MediaFileUpload(file_path, resumable=True)
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()

            return f"✅ File uploaded successfully!\nName: {file['name']}\nID: {file['id']}\nLink: {file['webViewLink']}"
        
        except Exception as e:
            return f"❌ Failed to upload file: {str(e)}"
