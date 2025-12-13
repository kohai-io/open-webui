"""
Google Drive file synchronization utilities
"""
import logging
import time
import aiohttp
from typing import Dict, Optional
from open_webui.models.files import Files, FileModel

log = logging.getLogger(__name__)


async def fetch_drive_file_metadata(file_id: str, access_token: str) -> Optional[Dict]:
    """
    Fetch metadata for a Google Drive file.
    
    Args:
        file_id: Google Drive file ID
        access_token: OAuth access token
        
    Returns:
        Dict with file metadata or None if failed
    """
    try:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        params = {
            "fields": "id,name,mimeType,modifiedTime,version,webViewLink,size"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    log.error(f"Failed to fetch Drive metadata for {file_id}: {response.status} - {error_text}")
                    return None
    except Exception as e:
        log.error(f"Error fetching Drive metadata for {file_id}: {e}")
        return None


async def download_drive_file(file_id: str, mime_type: str, access_token: str) -> Optional[bytes]:
    """
    Download file content from Google Drive.
    
    Args:
        file_id: Google Drive file ID
        mime_type: File MIME type
        access_token: OAuth access token
        
    Returns:
        File content as bytes or None if failed
    """
    try:
        # Determine if this is a Google Workspace file that needs export
        if mime_type.startswith('application/vnd.google-apps'):
            # Google Workspace files need export
            if 'document' in mime_type:
                export_format = 'text/plain'
            elif 'spreadsheet' in mime_type:
                export_format = 'text/csv'
            elif 'presentation' in mime_type:
                export_format = 'text/plain'
            else:
                export_format = 'application/pdf'
            
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
            params = {"mimeType": export_format}
        else:
            # Regular files use direct download
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            params = {"alt": "media"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"}
            ) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    error_text = await response.text()
                    log.error(f"Failed to download Drive file {file_id}: {response.status} - {error_text}")
                    return None
    except Exception as e:
        log.error(f"Error downloading Drive file {file_id}: {e}")
        return None


async def sync_drive_file(file: FileModel, access_token: str) -> Dict[str, bool]:
    """
    Sync a Google Drive file - check if modified and update if needed.
    
    Args:
        file: FileModel record with Drive metadata
        access_token: OAuth access token
        
    Returns:
        Dict with sync result: {"updated": True/False, "error": Optional[str]}
    """
    try:
        # Get stored Drive metadata (nested in meta.data.google_drive)
        file_data = file.meta.get("data", {}) if file.meta else {}
        stored_metadata = file_data.get("google_drive")
        
        if not stored_metadata:
            log.warning(f"File {file.id} has no Drive metadata, cannot sync")
            return {"updated": False, "error": "No Drive metadata"}
        
        file_id = stored_metadata.get("file_id")
        stored_modified_time = stored_metadata.get("modified_time")
        
        if not file_id:
            log.warning(f"File {file.id} missing Drive file_id")
            return {"updated": False, "error": "Missing file_id"}
        
        # Fetch current Drive metadata
        current_metadata = await fetch_drive_file_metadata(file_id, access_token)
        if not current_metadata:
            return {"updated": False, "error": "Failed to fetch metadata"}
        
        current_modified_time = current_metadata.get("modifiedTime")
        
        # Check if file has been modified
        if stored_modified_time == current_modified_time:
            log.info(f"File {file.id} ({file.filename}) is up to date")
            return {"updated": False}
        
        log.info(f"File {file.id} ({file.filename}) has been modified, re-downloading...")
        
        # Download updated file content
        mime_type = current_metadata.get("mimeType", "")
        content = await download_drive_file(file_id, mime_type, access_token)
        
        if not content:
            return {"updated": False, "error": "Failed to download file"}
        
        # Update file in storage
        from open_webui.storage.provider import Storage
        
        # Save updated content to storage
        Storage.upload_file(
            file_path=file.path,
            file=content,
            overwrite=True
        )
        
        # Update file metadata (preserve nested structure: meta.data.google_drive)
        existing_data = file.meta.get("data", {}) if file.meta else {}
        existing_drive = existing_data.get("google_drive", {})
        
        updated_meta = {
            "data": {
                **existing_data,
                "source": "google_drive",  # Preserve source for UI detection
                "google_drive": {
                    **existing_drive,
                    "file_id": file_id,
                    "modified_time": current_modified_time,
                    "version": current_metadata.get("version"),
                    "web_view_link": current_metadata.get("webViewLink"),
                    "mime_type": mime_type,
                    "size": current_metadata.get("size"),
                    "last_synced_at": int(time.time())
                }
            }
        }
        
        # Update file record in database
        Files.update_file_metadata_by_id(file.id, updated_meta)
        
        log.info(f"Successfully synced file {file.id} ({file.filename})")
        return {"updated": True}
        
    except Exception as e:
        log.error(f"Error syncing file {file.id}: {e}")
        return {"updated": False, "error": str(e)}
