from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from pydantic import BaseModel
import logging

from open_webui.models.users import Users
from open_webui.utils.auth import get_verified_user
from open_webui.models.oauth_sessions import OAuthSessions

log = logging.getLogger(__name__)

router = APIRouter()


class GoogleDriveTokenResponse(BaseModel):
    access_token: str
    expires_in: Optional[int] = None


@router.get("/authorize")
async def authorize_google_drive(
    request: Request,
    user=Depends(get_verified_user)
):
    """
    Initiate OAuth flow for Google Drive API access.
    Redirects user to Google's authorization page.
    """
    client_id = "google_drive"
    
    try:
        # Use the OAuth client manager to initiate authorization
        return await request.app.state.oauth_client_manager.handle_authorize(
            request, 
            client_id=client_id
        )
    except Exception as e:
        log.error(f"Failed to initiate Google Drive OAuth: {e}")
        raise HTTPException(500, f"Failed to initiate authorization: {str(e)}")


@router.get("/callback")
async def google_drive_oauth_callback(
    request: Request,
    response: Response,
    user=Depends(get_verified_user)
):
    """
    Handle OAuth callback from Google.
    Stores tokens server-side and redirects back to app.
    """
    client_id = "google_drive"
    
    try:
        # Handle the OAuth callback
        result = await request.app.state.oauth_client_manager.handle_callback(
            request,
            client_id=client_id,
            user_id=user.id,
            response=response
        )
        
        # Redirect back to the knowledge base with success message
        return Response(
            content="""
            <html>
                <body>
                    <script>
                        window.opener.postMessage({type: 'google_drive_auth_success'}, '*');
                        window.close();
                    </script>
                    <p>Authorization successful! You can close this window.</p>
                </body>
            </html>
            """,
            media_type="text/html"
        )
    except Exception as e:
        log.error(f"Google Drive OAuth callback failed: {e}")
        return Response(
            content=f"""
            <html>
                <body>
                    <script>
                        window.opener.postMessage({{type: 'google_drive_auth_error', error: '{str(e)}'}}, '*');
                        window.close();
                    </script>
                    <p>Authorization failed: {str(e)}</p>
                </body>
            </html>
            """,
            media_type="text/html"
        )


@router.get("/token")
async def get_google_drive_token(
    request: Request,
    user=Depends(get_verified_user)
) -> GoogleDriveTokenResponse:
    """
    Get a valid Google Drive access token for the current user.
    Automatically refreshes if expired.
    """
    client_id = "google_drive"
    
    try:
        # Get token from OAuth client manager (auto-refreshes if needed)
        token_data = await request.app.state.oauth_client_manager.get_oauth_token(
            user.id, 
            client_id,
            force_refresh=False
        )
        
        if not token_data:
            raise HTTPException(
                401, 
                detail="Not authorized with Google Drive. Please authorize first."
            )
        
        return GoogleDriveTokenResponse(
            access_token=token_data["access_token"],
            expires_in=token_data.get("expires_in")
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to get Google Drive token: {e}")
        raise HTTPException(500, f"Failed to get access token: {str(e)}")


@router.delete("/revoke")
async def revoke_google_drive_access(
    request: Request,
    user=Depends(get_verified_user)
):
    """
    Revoke Google Drive access by deleting stored tokens.
    """
    client_id = "google_drive"
    
    try:
        # Delete the OAuth session
        session = OAuthSessions.get_session_by_provider_and_user_id(client_id, user.id)
        if session:
            OAuthSessions.delete_session_by_id(session.id)
            log.info(f"Revoked Google Drive access for user {user.id}")
            return {"message": "Google Drive access revoked successfully"}
        else:
            return {"message": "No active Google Drive session found"}
    except Exception as e:
        log.error(f"Failed to revoke Google Drive access: {e}")
        raise HTTPException(500, f"Failed to revoke access: {str(e)}")


@router.get("/status")
async def google_drive_auth_status(
    request: Request,
    user=Depends(get_verified_user)
):
    """
    Check if user has authorized Google Drive access.
    """
    client_id = "google_drive"
    
    try:
        session = OAuthSessions.get_session_by_provider_and_user_id(client_id, user.id)
        return {
            "authorized": session is not None,
            "expires_at": session.expires_at if session else None
        }
    except Exception as e:
        log.error(f"Failed to check Google Drive auth status: {e}")
        return {"authorized": False, "expires_at": None}


@router.post("/sync-all")
async def sync_all_google_drive_files(
    request: Request,
    user=Depends(get_verified_user)
):
    """
    Sync all Google Drive files for the current user.
    Checks all files with driveMetadata and updates them if modified.
    """
    try:
        from open_webui.models.files import Files
        from open_webui.utils.google_drive_sync import sync_drive_file
        
        # Get access token
        client_id = "google_drive"
        token_data = await request.app.state.oauth_client_manager.get_oauth_token(
            user.id, 
            client_id,
            force_refresh=False
        )
        
        if not token_data:
            raise HTTPException(
                401, 
                detail="Not authorized with Google Drive. Please authorize first."
            )
        
        access_token = token_data["access_token"]
        
        # Find all files owned by user with Drive metadata
        # Note: Files are stored with nested structure: meta.data.source and meta.data.google_drive
        all_files = Files.get_files()
        user_drive_files = [
            f for f in all_files 
            if f.user_id == user.id and 
               f.meta and 
               f.meta.get("data", {}).get("source") == "google_drive"
        ]
        
        log.info(f"[SYNC] Found {len(user_drive_files)} Google Drive files for user {user.id}")
        
        if not user_drive_files:
            return {
                "message": "No Google Drive files found",
                "synced": 0,
                "updated": 0,
                "failed": 0
            }
        
        synced = 0
        updated = 0
        failed = 0
        
        for file in user_drive_files:
            try:
                result = await sync_drive_file(file, access_token, request=request, user=user)
                if result.get("updated"):
                    updated += 1
                synced += 1
            except Exception as e:
                log.error(f"Failed to sync file {file.id}: {e}")
                failed += 1
        
        return {
            "message": f"Sync complete: {updated} updated, {synced - updated} unchanged, {failed} failed",
            "synced": synced,
            "updated": updated,
            "failed": failed
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to sync Google Drive files: {e}")
        raise HTTPException(500, f"Failed to sync files: {str(e)}")
