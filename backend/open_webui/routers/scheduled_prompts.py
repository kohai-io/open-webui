from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from open_webui.models.scheduled_prompts import (
    ScheduledPromptForm,
    ScheduledPromptUpdateForm,
    ScheduledPromptResponse,
    ScheduledPromptModel,
    ScheduledPrompts,
)
from open_webui.models.models import Models
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.scheduler import calculate_next_run, validate_cron_expression

import logging

log = logging.getLogger(__name__)

router = APIRouter()

# Rate limit: max scheduled prompts per user
MAX_SCHEDULED_PROMPTS_PER_USER = 50


############################
# GetScheduledPrompts
############################


@router.get("/", response_model=list[ScheduledPromptResponse])
async def get_scheduled_prompts(user=Depends(get_verified_user)):
    """
    Get all scheduled prompts for the current user.
    Admins can see all scheduled prompts.
    """
    if user.role == "admin":
        prompts = ScheduledPrompts.get_scheduled_prompts()
    else:
        prompts = ScheduledPrompts.get_scheduled_prompts_by_user_id(user.id)
    
    return [
        ScheduledPromptResponse(
            id=prompt.id,
            user_id=prompt.user_id,
            name=prompt.name,
            cron_expression=prompt.cron_expression,
            timezone=prompt.timezone,
            enabled=prompt.enabled,
            model_id=prompt.model_id,
            system_prompt=prompt.system_prompt,
            prompt=prompt.prompt,
            chat_id=prompt.chat_id,
            create_new_chat=prompt.create_new_chat,
            run_once=prompt.run_once,
            tool_ids=prompt.tool_ids,
            function_calling_mode=prompt.function_calling_mode,
            last_run_at=prompt.last_run_at,
            next_run_at=prompt.next_run_at,
            last_status=prompt.last_status,
            last_error=prompt.last_error,
            run_count=prompt.run_count,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at,
        )
        for prompt in prompts
    ]


############################
# CreateScheduledPrompt
############################


@router.post("/create", response_model=Optional[ScheduledPromptResponse])
async def create_scheduled_prompt(
    request: Request, form_data: ScheduledPromptForm, user=Depends(get_verified_user)
):
    """
    Create a new scheduled prompt
    """
    # Rate limiting: check user's prompt count
    current_count = ScheduledPrompts.count_scheduled_prompts_by_user_id(user.id)
    if current_count >= MAX_SCHEDULED_PROMPTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum number of scheduled prompts ({MAX_SCHEDULED_PROMPTS_PER_USER}) reached",
        )

    # Validate cron expression
    if not validate_cron_expression(form_data.cron_expression):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cron expression. Use standard 5-field cron format (minute hour day month weekday)",
        )

    # Validate model exists
    model = Models.get_model_by_id(form_data.model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{form_data.model_id}' not found",
        )

    try:
        # Calculate next run time
        next_run_at = calculate_next_run(form_data.cron_expression, form_data.timezone)
        
        prompt = ScheduledPrompts.insert_new_scheduled_prompt(
            user.id, form_data, next_run_at=next_run_at
        )

        if prompt:
            return ScheduledPromptResponse(
                id=prompt.id,
                user_id=prompt.user_id,
                name=prompt.name,
                cron_expression=prompt.cron_expression,
                timezone=prompt.timezone,
                enabled=prompt.enabled,
                model_id=prompt.model_id,
                system_prompt=prompt.system_prompt,
                prompt=prompt.prompt,
                chat_id=prompt.chat_id,
                create_new_chat=prompt.create_new_chat,
                run_once=prompt.run_once,
                tool_ids=prompt.tool_ids,
                function_calling_mode=prompt.function_calling_mode,
                last_run_at=prompt.last_run_at,
                next_run_at=prompt.next_run_at,
                last_status=prompt.last_status,
                last_error=prompt.last_error,
                run_count=prompt.run_count,
                created_at=prompt.created_at,
                updated_at=prompt.updated_at,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
    except Exception as e:
        log.error(f"Error creating scheduled prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


############################
# GetScheduledPromptById
############################


@router.get("/{id}", response_model=Optional[ScheduledPromptResponse])
async def get_scheduled_prompt_by_id(id: str, user=Depends(get_verified_user)):
    """
    Get a specific scheduled prompt by ID
    """
    prompt = ScheduledPrompts.get_scheduled_prompt_by_id(id)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check ownership (admins can view any)
    if prompt.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return ScheduledPromptResponse(
        id=prompt.id,
        user_id=prompt.user_id,
        name=prompt.name,
        cron_expression=prompt.cron_expression,
        timezone=prompt.timezone,
        enabled=prompt.enabled,
        model_id=prompt.model_id,
        system_prompt=prompt.system_prompt,
        prompt=prompt.prompt,
        chat_id=prompt.chat_id,
        create_new_chat=prompt.create_new_chat,
        run_once=prompt.run_once,
        tool_ids=prompt.tool_ids,
        function_calling_mode=prompt.function_calling_mode,
        last_run_at=prompt.last_run_at,
        next_run_at=prompt.next_run_at,
        last_status=prompt.last_status,
        last_error=prompt.last_error,
        run_count=prompt.run_count,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


############################
# UpdateScheduledPromptById
############################


@router.post("/{id}", response_model=Optional[ScheduledPromptResponse])
async def update_scheduled_prompt_by_id(
    id: str,
    form_data: ScheduledPromptUpdateForm,
    user=Depends(get_verified_user),
):
    """
    Update a scheduled prompt by ID
    """
    prompt = ScheduledPrompts.get_scheduled_prompt_by_id(id)
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check ownership (admins can update any)
    if prompt.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Validate cron expression if being updated
    if form_data.cron_expression is not None:
        if not validate_cron_expression(form_data.cron_expression):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cron expression",
            )

    # Validate model if being updated
    if form_data.model_id is not None:
        model = Models.get_model_by_id(form_data.model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{form_data.model_id}' not found",
            )

    # Recalculate next run time if cron or timezone changed
    next_run_at = None
    cron = form_data.cron_expression if form_data.cron_expression else prompt.cron_expression
    tz = form_data.timezone if form_data.timezone else prompt.timezone
    
    if form_data.cron_expression is not None or form_data.timezone is not None:
        next_run_at = calculate_next_run(cron, tz)

    updated_prompt = ScheduledPrompts.update_scheduled_prompt_by_id(id, form_data, next_run_at)
    
    if updated_prompt:
        return ScheduledPromptResponse(
            id=updated_prompt.id,
            user_id=updated_prompt.user_id,
            name=updated_prompt.name,
            cron_expression=updated_prompt.cron_expression,
            timezone=updated_prompt.timezone,
            enabled=updated_prompt.enabled,
            model_id=updated_prompt.model_id,
            system_prompt=updated_prompt.system_prompt,
            prompt=updated_prompt.prompt,
            chat_id=updated_prompt.chat_id,
            create_new_chat=updated_prompt.create_new_chat,
            run_once=updated_prompt.run_once,
            tool_ids=updated_prompt.tool_ids,
            function_calling_mode=updated_prompt.function_calling_mode,
            last_run_at=updated_prompt.last_run_at,
            next_run_at=updated_prompt.next_run_at,
            last_status=updated_prompt.last_status,
            last_error=updated_prompt.last_error,
            run_count=updated_prompt.run_count,
            created_at=updated_prompt.created_at,
            updated_at=updated_prompt.updated_at,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# ToggleScheduledPrompt
############################


@router.post("/{id}/toggle", response_model=Optional[ScheduledPromptResponse])
async def toggle_scheduled_prompt(id: str, user=Depends(get_verified_user)):
    """
    Toggle enabled/disabled state of a scheduled prompt
    """
    prompt = ScheduledPrompts.get_scheduled_prompt_by_id(id)
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check ownership
    if prompt.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Toggle and recalculate next run if enabling
    new_enabled = not prompt.enabled
    next_run_at = None
    
    if new_enabled:
        next_run_at = calculate_next_run(prompt.cron_expression, prompt.timezone)

    form_data = ScheduledPromptUpdateForm(enabled=new_enabled)
    updated_prompt = ScheduledPrompts.update_scheduled_prompt_by_id(id, form_data, next_run_at)
    
    if updated_prompt:
        return ScheduledPromptResponse(
            id=updated_prompt.id,
            user_id=updated_prompt.user_id,
            name=updated_prompt.name,
            cron_expression=updated_prompt.cron_expression,
            timezone=updated_prompt.timezone,
            enabled=updated_prompt.enabled,
            model_id=updated_prompt.model_id,
            system_prompt=updated_prompt.system_prompt,
            prompt=updated_prompt.prompt,
            chat_id=updated_prompt.chat_id,
            create_new_chat=updated_prompt.create_new_chat,
            run_once=updated_prompt.run_once,
            tool_ids=updated_prompt.tool_ids,
            function_calling_mode=updated_prompt.function_calling_mode,
            last_run_at=updated_prompt.last_run_at,
            next_run_at=updated_prompt.next_run_at,
            last_status=updated_prompt.last_status,
            last_error=updated_prompt.last_error,
            run_count=updated_prompt.run_count,
            created_at=updated_prompt.created_at,
            updated_at=updated_prompt.updated_at,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# RunScheduledPromptNow
############################


@router.post("/{id}/run", response_model=dict)
async def run_scheduled_prompt_now(
    request: Request, id: str, user=Depends(get_verified_user)
):
    """
    Manually trigger a scheduled prompt to run immediately
    """
    prompt = ScheduledPrompts.get_scheduled_prompt_by_id(id)
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check ownership
    if prompt.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Import here to avoid circular imports
    from open_webui.utils.scheduler import execute_scheduled_prompt
    
    try:
        result = await execute_scheduled_prompt(request.app, prompt)
        return {
            "success": True,
            "message": "Scheduled prompt executed successfully",
            "chat_id": result.get("chat_id"),
        }
    except Exception as e:
        log.error(f"Error executing scheduled prompt {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {str(e)}",
        )


############################
# DeleteScheduledPromptById
############################


@router.delete("/{id}", response_model=bool)
async def delete_scheduled_prompt_by_id(id: str, user=Depends(get_verified_user)):
    """
    Delete a scheduled prompt by ID
    """
    prompt = ScheduledPrompts.get_scheduled_prompt_by_id(id)
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check ownership (admins can delete any)
    if prompt.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = ScheduledPrompts.delete_scheduled_prompt_by_id(id)
    return result


############################
# Admin: GetAllScheduledPrompts
############################


@router.get("/admin/all", response_model=list[ScheduledPromptResponse])
async def get_all_scheduled_prompts(user=Depends(get_admin_user)):
    """
    Admin endpoint: Get all scheduled prompts from all users
    """
    prompts = ScheduledPrompts.get_scheduled_prompts()
    
    return [
        ScheduledPromptResponse(
            id=prompt.id,
            user_id=prompt.user_id,
            name=prompt.name,
            cron_expression=prompt.cron_expression,
            timezone=prompt.timezone,
            enabled=prompt.enabled,
            model_id=prompt.model_id,
            system_prompt=prompt.system_prompt,
            prompt=prompt.prompt,
            chat_id=prompt.chat_id,
            create_new_chat=prompt.create_new_chat,
            run_once=prompt.run_once,
            tool_ids=prompt.tool_ids,
            function_calling_mode=prompt.function_calling_mode,
            last_run_at=prompt.last_run_at,
            next_run_at=prompt.next_run_at,
            last_status=prompt.last_status,
            last_error=prompt.last_error,
            run_count=prompt.run_count,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at,
        )
        for prompt in prompts
    ]
