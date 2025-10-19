import logging
import os
import uuid
import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional
from urllib.parse import quote
import asyncio

from fastapi import (
    BackgroundTasks,
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
    Query,
)

from fastapi.responses import FileResponse, StreamingResponse
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

from open_webui.models.users import Users
from open_webui.models.files import (
    FileForm,
    FileModel,
    FileModelResponse,
    Files,
)
from open_webui.models.knowledge import Knowledges
from open_webui.models.chats import Chats
from open_webui.models.folders import Folders

from open_webui.routers.knowledge import get_knowledge, get_knowledge_list
from open_webui.routers.retrieval import ProcessFileForm, process_file
from open_webui.routers.audio import transcribe
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# Check if the current user has access to a file through any knowledge bases the user may be in.
############################


def has_access_to_file(
    file_id: Optional[str], access_type: str, user=Depends(get_verified_user)
) -> bool:
    file = Files.get_file_by_id(file_id)
    log.debug(f"Checking if user has {access_type} access to file")

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    has_access = False
    knowledge_base_id = file.meta.get("collection_name") if file.meta else None

    if knowledge_base_id:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
            user.id, access_type
        )
        for knowledge_base in knowledge_bases:
            if knowledge_base.id == knowledge_base_id:
                has_access = True
                break

    return has_access


############################
# Upload File
############################


def process_uploaded_file(request, file, file_path, file_item, file_metadata, user):
    try:
        processed = False
        if file.content_type:
            stt_supported_content_types = getattr(
                request.app.state.config, "STT_SUPPORTED_CONTENT_TYPES", []
            )

            if any(
                fnmatch(file.content_type, content_type)
                for content_type in (
                    stt_supported_content_types
                    if stt_supported_content_types
                    and any(t.strip() for t in stt_supported_content_types)
                    else ["audio/*", "video/webm"]
                )
            ):
                file_path = Storage.get_file(file_path)
                result = transcribe(request, file_path, file_metadata)

                process_file(
                    request,
                    ProcessFileForm(
                        file_id=file_item.id, content=result.get("text", "")
                    ),
                    user=user,
                )
                processed = True
            elif (not file.content_type.startswith(("image/", "video/"))) or (
                request.app.state.config.CONTENT_EXTRACTION_ENGINE == "external"
            ):
                process_file(request, ProcessFileForm(file_id=file_item.id), user=user)
                processed = True
        else:
            log.info(
                f"File type {file.content_type} is not provided, but trying to process anyway"
            )
            process_file(request, ProcessFileForm(file_id=file_item.id), user=user)
            processed = True

        # If no processing was performed (e.g., certain image/video types), mark as completed
        if not processed:
            Files.update_file_data_by_id(
                file_item.id,
                {
                    "status": "completed",
                },
            )
    except Exception as e:
        log.error(f"Error processing file: {file_item.id}")
        Files.update_file_data_by_id(
            file_item.id,
            {
                "status": "failed",
                "error": str(e.detail) if hasattr(e, "detail") else str(e),
            },
        )


@router.post("/", response_model=FileModelResponse)
def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    process_in_background: bool = Query(True),
    user=Depends(get_verified_user),
):
    return upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=process,
        process_in_background=process_in_background,
        user=user,
        background_tasks=background_tasks,
    )


def upload_file_handler(
    request: Request,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    process_in_background: bool = Query(True),
    user=Depends(get_verified_user),
    background_tasks: Optional[BackgroundTasks] = None,
):
    log.info(f"file.content_type: {file.content_type}")

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Invalid metadata format"),
            )
    file_metadata = metadata if metadata else {}

    try:
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        file_extension = os.path.splitext(filename)[1]
        # Remove the leading dot from the file extension
        file_extension = file_extension[1:] if file_extension else ""

        if process and request.app.state.config.ALLOWED_FILE_EXTENSIONS:
            request.app.state.config.ALLOWED_FILE_EXTENSIONS = [
                ext for ext in request.app.state.config.ALLOWED_FILE_EXTENSIONS if ext
            ]

            if file_extension not in request.app.state.config.ALLOWED_FILE_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(
                        f"File type {file_extension} is not allowed"
                    ),
                )

        # replace filename with uuid
        id = str(uuid.uuid4())
        name = filename
        filename = f"{id}_{filename}"
        contents, file_path = Storage.upload_file(
            file.file,
            filename,
            {
                "OpenWebUI-User-Email": user.email,
                "OpenWebUI-User-Id": user.id,
                "OpenWebUI-User-Name": user.name,
                "OpenWebUI-File-Id": id,
            },
        )

        file_item = Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    "id": id,
                    "filename": name,
                    "path": file_path,
                    "data": {
                        **({"status": "pending"} if process else {}),
                    },
                    "meta": {
                        "name": name,
                        "content_type": file.content_type,
                        "size": len(contents),
                        "data": file_metadata,
                    },
                }
            ),
        )

        if process:
            if background_tasks and process_in_background:
                background_tasks.add_task(
                    process_uploaded_file,
                    request,
                    file,
                    file_path,
                    file_item,
                    file_metadata,
                    user,
                )
                return {"status": True, **file_item.model_dump()}
            else:
                process_uploaded_file(
                    request,
                    file,
                    file_path,
                    file_item,
                    file_metadata,
                    user,
                )
                return {"status": True, **file_item.model_dump()}
        else:
            if file_item:
                return file_item
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
                )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
        )


############################
# Get Media Overview
############################


class MediaOverviewResponse(BaseModel):
    files: list[dict]
    chats: list[dict]
    folders: list[dict]
    total: int
    skip: int
    limit: int


@router.get("/media-overview")
async def get_media_overview(
    user=Depends(get_verified_user),
    skip: int = Query(0, ge=0, description="Number of files to skip"),
    limit: int = Query(0, ge=0, le=500, description="Max files to return (0 = all)"),
):
    """
    Get media files with pre-joined chat and folder information.
    Only returns folders/chats that contain media files.
    Optimized for the media workspace page.
    """
    import time
    start_time = time.time()
    
    # Get all user's files
    t1 = time.time()
    files = Files.get_files_by_user_id(user.id)
    log.info(f"[PERF] Get all files: {(time.time() - t1)*1000:.0f}ms ({len(files)} files)")
    
    # Filter to media types only (images, videos, audio)
    t2 = time.time()
    media_types = ('image/', 'video/', 'audio/')
    media_files = []
    file_to_chat_map = {}
    files_without_chat = set()  # Track files needing chat resolution
    
    for f in files:
        # Check if it's a media file based on content_type in meta
        content_type = f.meta.get('content_type', '') if f.meta else ''
        if content_type and content_type.startswith(media_types):
            media_files.append(f)
            # Try to get chat_id from metadata first
            chat_id = None
            if f.meta:
                chat_id = f.meta.get('chat_id') or f.meta.get('source_chat_id')
            
            # Handle orphan files (marked as 'orphan' to skip expensive lookup)
            if chat_id == 'orphan':
                file_to_chat_map[f.id] = None
            else:
                file_to_chat_map[f.id] = chat_id
                # Only add to files_without_chat if not marked as orphan
                if chat_id is None:
                    files_without_chat.add(f.id)
    
    log.info(f"[PERF] Filter media files: {(time.time() - t2)*1000:.0f}ms ({len(media_files)} media, {len(files_without_chat)} need chat lookup)")
    
    # For files without chat_id in metadata, search chat history
    # OPTIMIZATION: Use optimized method that only loads minimal chat data
    if files_without_chat:
        t3 = time.time()
        # Get chat associations for files without metadata
        resolved_mappings = Chats.get_chat_ids_containing_file_ids(user.id, files_without_chat)
        log.info(f"[PERF] Chat lookup for orphans: {(time.time() - t3)*1000:.0f}ms ({len(resolved_mappings or [])} resolved)")
        
        # Build file dict for efficient lookup
        file_dict = {f.id: f for f in media_files if f.id in files_without_chat}
        
        # Update file_to_chat_map and file metadata for resolved files
        if resolved_mappings:
            for file_id, chat_id in resolved_mappings.items():
                file_to_chat_map[file_id] = chat_id
                
                # Update file metadata so it's available on subsequent loads
                f = file_dict.get(file_id)
                if f:
                    if not f.meta:
                        f.meta = {}
                    f.meta['chat_id'] = chat_id
                    
                    # Persist to database so we don't need to search again
                    try:
                        Files.update_file_metadata_by_id(file_id, f.meta)
                    except Exception as e:
                        log.warning(f"Failed to persist chat_id for file {file_id}: {e}")
        
        # Mark unresolved files as orphans so we don't search again
        orphan_files = files_without_chat - set(resolved_mappings.keys() if resolved_mappings else [])
        if orphan_files:
            log.info(f"[PERF] Marking {len(orphan_files)} files as orphans (no chat found)")
            for file_id in orphan_files:
                f = file_dict.get(file_id)
                if f:
                    if not f.meta:
                        f.meta = {}
                    # Mark as orphan with special value so we don't search again
                    f.meta['chat_id'] = 'orphan'
                    try:
                        Files.update_file_metadata_by_id(file_id, f.meta)
                    except Exception as e:
                        log.warning(f"Failed to mark file {file_id} as orphan: {e}")
    
    # Collect unique chat IDs (exclude None and 'orphan' marker)
    t4 = time.time()
    chat_ids = set(cid for cid in file_to_chat_map.values() if cid is not None and cid != 'orphan')
    
    # Get only chat metadata (id, title, folder_id) - optimized to avoid loading full chat history
    chats_dict = []
    folder_ids = set()
    if chat_ids:
        chats_dict = Chats.get_chat_metadata_by_ids(list(chat_ids))
        # Extract folder IDs from chats
        for chat in chats_dict:
            if chat.get("folder_id"):
                folder_ids.add(chat["folder_id"])
    log.info(f"[PERF] Get chats: {(time.time() - t4)*1000:.0f}ms ({len(chats_dict)} chats)")
    
    # Get only folders that contain chats with media
    t5 = time.time()
    folders = []
    if folder_ids:
        folders = Folders.get_folders_by_ids(list(folder_ids))
    log.info(f"[PERF] Get folders: {(time.time() - t5)*1000:.0f}ms ({len(folders)} folders)")
    
    # Sort files by updated_at (newest first) before pagination
    t6 = time.time()
    media_files.sort(key=lambda f: f.updated_at if hasattr(f, 'updated_at') and f.updated_at else 0, reverse=True)
    log.info(f"[PERF] Sort files: {(time.time() - t6)*1000:.0f}ms")
    
    # Apply pagination if requested
    total_files = len(media_files)
    if limit > 0:
        media_files = media_files[skip : skip + limit]
    
    # Convert files and folders to dicts for response (chats already dicts from get_chat_metadata_by_ids)
    t7 = time.time()
    files_dict = [f.model_dump() for f in media_files]
    folders_dict = [folder.model_dump() for folder in folders]
    log.info(f"[PERF] Serialize to dicts: {(time.time() - t7)*1000:.0f}ms")
    
    total_time = (time.time() - start_time) * 1000
    log.info(f"[PERF] media-overview TOTAL: {total_time:.0f}ms (skip={skip}, limit={limit}, returned {len(files_dict)} files)")
    
    return {
        "files": files_dict,
        "chats": chats_dict,
        "folders": folders_dict,
        "total": total_files,
        "skip": skip,
        "limit": limit if limit > 0 else total_files,
    }


############################
# List Files
############################


@router.get("/", response_model=list[FileModelResponse])
async def list_files(user=Depends(get_verified_user), content: bool = Query(True)):
    if user.role == "admin":
        files = Files.get_files()
    else:
        files = Files.get_files_by_user_id(user.id)

    if not content:
        for file in files:
            if "content" in file.data:
                del file.data["content"]

    return files


############################
# Search Files
############################


@router.get("/search", response_model=list[FileModelResponse])
async def search_files(
    filename: str = Query(
        ...,
        description="Filename pattern to search for. Supports wildcards such as '*.txt'",
    ),
    content: bool = Query(True),
    user=Depends(get_verified_user),
):
    """
    Search for files by filename with support for wildcard patterns.
    """
    # Get files according to user role
    if user.role == "admin":
        files = Files.get_files()
    else:
        files = Files.get_files_by_user_id(user.id)

    # Get matching files
    matching_files = [
        file for file in files if fnmatch(file.filename.lower(), filename.lower())
    ]

    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files found matching the pattern.",
        )

    if not content:
        for file in matching_files:
            if "content" in file.data:
                del file.data["content"]

    return matching_files


############################
# Delete All Files
############################


@router.delete("/all")
async def delete_all_files(user=Depends(get_admin_user)):
    result = Files.delete_all_files()
    if result:
        try:
            Storage.delete_all_files()
            VECTOR_DB_CLIENT.reset()
        except Exception as e:
            log.exception(e)
            log.error("Error deleting files")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
            )
        return {"message": "All files deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
        )


############################
# Get File By Id
############################


@router.get("/{id}", response_model=Optional[FileModel])
async def get_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        return file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/process/status")
async def get_file_process_status(
    id: str, stream: bool = Query(False), user=Depends(get_verified_user)
):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        if stream:
            MAX_FILE_PROCESSING_DURATION = 3600 * 2

            async def event_stream(file_item):
                if file_item:
                    for _ in range(MAX_FILE_PROCESSING_DURATION):
                        file_item = Files.get_file_by_id(file_item.id)
                        if file_item:
                            data = file_item.model_dump().get("data", {})
                            status = data.get("status")

                            if status:
                                event = {"status": status}
                                if status == "failed":
                                    event["error"] = data.get("error")

                                yield f"data: {json.dumps(event)}\n\n"
                                if status in ("completed", "failed"):
                                    break
                            else:
                                # Legacy
                                break

                        await asyncio.sleep(0.5)
                else:
                    yield f"data: {json.dumps({'status': 'not_found'})}\n\n"

            return StreamingResponse(
                event_stream(file),
                media_type="text/event-stream",
            )
        else:
            return {"status": file.data.get("status", "pending")}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Data Content By Id
############################


@router.get("/{id}/data/content")
async def get_file_data_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        return {"content": file.data.get("content", "")}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Update File Data Content By Id
############################


class ContentForm(BaseModel):
    content: str


@router.post("/{id}/data/content/update")
async def update_file_data_content_by_id(
    request: Request, id: str, form_data: ContentForm, user=Depends(get_verified_user)
):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "write", user)
    ):
        try:
            process_file(
                request,
                ProcessFileForm(file_id=id, content=form_data.content),
                user=user,
            )
            file = Files.get_file_by_id(id=id)
        except Exception as e:
            log.exception(e)
            log.error(f"Error processing file: {file.id}")

        return {"content": file.data.get("content", "")}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Content By Id
############################


@router.get("/{id}/content")
async def get_file_content_by_id(
    id: str, user=Depends(get_verified_user), attachment: bool = Query(False)
):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        try:
            file_path = Storage.get_file(file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                # Handle Unicode filenames
                filename = file.meta.get("name", file.filename)
                encoded_filename = quote(filename)  # RFC5987 encoding

                content_type = file.meta.get("content_type")
                filename = file.meta.get("name", file.filename)
                encoded_filename = quote(filename)
                headers = {}

                if attachment:
                    headers["Content-Disposition"] = (
                        f"attachment; filename*=UTF-8''{encoded_filename}"
                    )
                else:
                    if content_type == "application/pdf" or filename.lower().endswith(
                        ".pdf"
                    ):
                        headers["Content-Disposition"] = (
                            f"inline; filename*=UTF-8''{encoded_filename}"
                        )
                        content_type = "application/pdf"
                    elif content_type != "text/plain":
                        headers["Content-Disposition"] = (
                            f"attachment; filename*=UTF-8''{encoded_filename}"
                        )

                return FileResponse(file_path, headers=headers, media_type=content_type)

            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except Exception as e:
            log.exception(e)
            log.error("Error getting file content")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/content/html")
async def get_html_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    file_user = Users.get_user_by_id(file.user_id)
    if not file_user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        try:
            file_path = Storage.get_file(file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                log.info(f"file_path: {file_path}")
                return FileResponse(file_path)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except Exception as e:
            log.exception(e)
            log.error("Error getting file content")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/content/{file_name}")
async def get_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        file_path = file.path

        # Handle Unicode filenames
        filename = file.meta.get("name", file.filename)
        encoded_filename = quote(filename)  # RFC5987 encoding
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }

        if file_path:
            file_path = Storage.get_file(file_path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                return FileResponse(file_path, headers=headers)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        else:
            # File path doesn’t exist, return the content as .txt if possible
            file_content = file.content.get("content", "")
            file_name = file.filename

            # Create a generator that encodes the file content
            def generator():
                yield file_content.encode("utf-8")

            return StreamingResponse(
                generator(),
                media_type="text/plain",
                headers=headers,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Delete File By Id
############################


@router.delete("/{id}")
async def delete_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "write", user)
    ):

        result = Files.delete_file_by_id(id)
        if result:
            try:
                Storage.delete_file(file.path)
                VECTOR_DB_CLIENT.delete(collection_name=f"file-{id}")
            except Exception as e:
                log.exception(e)
                log.error("Error deleting files")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
                )
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting file"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
