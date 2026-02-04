"""
Scheduler service for executing scheduled prompts.

Uses asyncio for lightweight scheduling without external dependencies.
Checks the database every minute for due jobs and executes them.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from croniter import croniter

from open_webui.models.scheduled_prompts import ScheduledPrompts, ScheduledPromptModel
from open_webui.models.chats import Chats, ChatForm
from open_webui.models.users import Users
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("SCHEDULER", logging.INFO))

# Global scheduler task reference
_scheduler_task: Optional[asyncio.Task] = None
_scheduler_running = False

# Check interval in seconds
SCHEDULER_CHECK_INTERVAL = 60


def validate_cron_expression(cron_expression: str) -> bool:
    """
    Validate a cron expression.
    Returns True if valid, False otherwise.
    """
    try:
        # croniter expects 5 fields: minute hour day month weekday
        croniter(cron_expression)
        return True
    except (ValueError, KeyError):
        return False


def calculate_next_run(cron_expression: str, timezone: str = "UTC") -> int:
    """
    Calculate the next run time for a cron expression.
    Returns Unix timestamp.
    """
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("UTC")
    
    now = datetime.now(tz)
    cron = croniter(cron_expression, now)
    next_run = cron.get_next(datetime)
    
    return int(next_run.timestamp())


def get_cron_description(cron_expression: str) -> str:
    """
    Get a human-readable description of a cron expression.
    """
    try:
        parts = cron_expression.split()
        if len(parts) != 5:
            return cron_expression
        
        minute, hour, day, month, weekday = parts
        
        # Simple descriptions for common patterns
        if cron_expression == "* * * * *":
            return "Every minute"
        elif minute != "*" and hour != "*" and day == "*" and month == "*" and weekday == "*":
            return f"Daily at {hour}:{minute.zfill(2)}"
        elif minute != "*" and hour != "*" and weekday != "*" and day == "*" and month == "*":
            days = {
                "0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday",
                "4": "Thursday", "5": "Friday", "6": "Saturday", "7": "Sunday",
                "1-5": "weekdays", "0,6": "weekends"
            }
            day_str = days.get(weekday, weekday)
            return f"Every {day_str} at {hour}:{minute.zfill(2)}"
        
        return cron_expression
    except Exception:
        return cron_expression


async def execute_scheduled_prompt(app, prompt: ScheduledPromptModel) -> dict:
    """
    Execute a single scheduled prompt.
    
    Args:
        app: FastAPI application instance (for accessing models and config)
        prompt: The scheduled prompt to execute
    
    Returns:
        dict with execution result including chat_id
    """
    import json
    import aiohttp
    from open_webui.utils.auth import create_token
    from datetime import timedelta
    
    log.info(f"[Scheduler] Executing scheduled prompt: {prompt.id} - {prompt.name}")
    
    try:
        # Get the user who owns this prompt
        user = Users.get_user_by_id(prompt.user_id)
        if not user:
            raise Exception(f"User {prompt.user_id} not found")
        
        # Build the messages
        messages = []
        if prompt.system_prompt:
            messages.append({
                "role": "system",
                "content": prompt.system_prompt,
            })
        messages.append({
            "role": "user",
            "content": prompt.prompt,
        })
        
        # Build the payload for chat completion
        payload = {
            "model": prompt.model_id,
            "messages": messages,
            "stream": False,
        }
        
        # Get models from app state and validate/fallback model
        models = app.state.MODELS
        model_id = prompt.model_id
        
        if model_id not in models:
            # Try to use user's default model or first available model
            log.warning(f"[Scheduler] Model {model_id} not found, looking for fallback")
            
            # Check user settings for default model
            user_default_model = None
            if user.settings:
                # user.settings is a UserSettings Pydantic model, access via model_dump() or getattr
                settings_dict = user.settings.model_dump() if hasattr(user.settings, 'model_dump') else {}
                models_list = settings_dict.get("models", [])
                if models_list:
                    user_default_model = models_list[0]
            
            if user_default_model and user_default_model in models:
                model_id = user_default_model
                log.info(f"[Scheduler] Using user's default model: {model_id}")
            elif models:
                # Use first available model as last resort
                model_id = list(models.keys())[0]
                log.info(f"[Scheduler] Using first available model: {model_id}")
            else:
                raise Exception(f"Model {prompt.model_id} not found and no fallback available")
        
        # Update payload with resolved model
        payload["model"] = model_id
        
        # Determine tool_ids: use explicit prompt.tool_ids, or inherit from model config
        tool_ids = prompt.tool_ids
        if not tool_ids:
            # Check if the model has default tools configured
            model_info = models.get(model_id, {})
            model_tool_ids = model_info.get("info", {}).get("meta", {}).get("toolIds", [])
            if model_tool_ids:
                tool_ids = model_tool_ids
                log.info(f"[Scheduler] Using model's configured tools: {tool_ids}")
        
        if tool_ids:
            payload["tool_ids"] = tool_ids
            log.info(f"[Scheduler] Prompt will use tools: {tool_ids}")
            
            # Build tool instruction - exclude prompt_scheduler from "use these tools" instruction
            # since this IS a scheduled prompt execution, not a request to create one
            action_tools = [t for t in tool_ids if 'prompt_scheduler' not in t.lower()]
            
            if action_tools:
                tool_instruction = f"\n\nIMPORTANT: This is an automated scheduled reminder. You have access to these tools: {', '.join(action_tools)}. Use them to help the user with their request. For example, if this is about a todo list, use the notes_manager tool to fetch the actual current data."
            else:
                tool_instruction = "\n\nIMPORTANT: This is an automated scheduled reminder. Respond helpfully to the user's request."
            
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] += tool_instruction
            else:
                messages.insert(0, {
                    "role": "system",
                    "content": f"You are a helpful assistant.{tool_instruction}"
                })
        
        # Create a short-lived token for this user
        token = create_token(
            data={"id": prompt.user_id},
            expires_delta=timedelta(seconds=300),
        )
        
        # Call the internal API - always use localhost since scheduler runs on same server
        import os
        port = os.environ.get("PORT", "8080")
        api_url = f"http://127.0.0.1:{port}/api/chat/completions"
        
        log.info(f"[Scheduler] Calling API: {api_url}")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                response_data = await response.json()
        
        # Extract the assistant response
        assistant_content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        timestamp = int(time.time())
        
        # Build chat messages (only user + assistant, system prompt is hidden context)
        chat_messages = [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": prompt.prompt,
                "timestamp": timestamp,
                "models": [prompt.model_id],
            },
            {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": assistant_content,
                "timestamp": timestamp,
                "models": [prompt.model_id],
            },
        ]
        
        chat_id = prompt.chat_id
        
        # Create or update chat
        if prompt.create_new_chat or not chat_id:
            # Create new chat
            title = prompt.name or prompt.prompt[:50] + ("..." if len(prompt.prompt) > 50 else "")
            chat_data = {
                "title": f"[Scheduled] {title}",
                "messages": chat_messages,
                "models": [model_id],
            }
            # Include tool_ids in chat data so UI can restore them
            if tool_ids:
                chat_data["tool_ids"] = tool_ids
                log.info(f"[Scheduler] Saving chat with tool_ids: {tool_ids}")
            
            chat = Chats.insert_new_chat(
                prompt.user_id,
                ChatForm(chat=chat_data),
            )
            chat_id = chat.id if chat else None
        else:
            # Append to existing chat
            existing_chat = Chats.get_chat_by_id(chat_id)
            if existing_chat:
                existing_messages = existing_chat.chat.get("messages", [])
                existing_messages.extend(chat_messages[-2:])  # Add user + assistant messages
                existing_chat.chat["messages"] = existing_messages
                Chats.update_chat_by_id(chat_id, existing_chat.chat)
            else:
                # Chat was deleted, create new one
                title = prompt.name or prompt.prompt[:50]
                chat_data = {
                    "title": f"[Scheduled] {title}",
                    "messages": chat_messages,
                    "models": [model_id],
                }
                # Include tool_ids in chat data so UI can restore them
                if tool_ids:
                    chat_data["tool_ids"] = tool_ids
                    log.info(f"[Scheduler] Saving fallback chat with tool_ids: {tool_ids}")
                
                chat = Chats.insert_new_chat(
                    prompt.user_id,
                    ChatForm(chat=chat_data),
                )
                chat_id = chat.id if chat else None
        
        # Handle run_once: disable after successful execution, otherwise calculate next run
        if prompt.run_once:
            # Disable the prompt after one-off execution
            next_run_at = None
            ScheduledPrompts.update_execution_status(
                prompt.id,
                status="success",
                error=None,
                chat_id=chat_id,
                next_run_at=None,
            )
            # Disable the prompt
            from open_webui.models.scheduled_prompts import ScheduledPromptUpdateForm
            ScheduledPrompts.update_scheduled_prompt_by_id(
                prompt.id,
                ScheduledPromptUpdateForm(enabled=False),
            )
            log.info(f"[Scheduler] One-off prompt {prompt.id} completed and disabled")
        else:
            # Calculate next run time for recurring prompts
            next_run_at = calculate_next_run(prompt.cron_expression, prompt.timezone)
            ScheduledPrompts.update_execution_status(
                prompt.id,
                status="success",
                error=None,
                chat_id=chat_id,
                next_run_at=next_run_at,
            )
        
        log.info(f"[Scheduler] Successfully executed prompt {prompt.id}, chat_id: {chat_id}")
        
        # Send notification to user via websocket
        notification_message = f"'{prompt.name}' ran successfully"
        if prompt.run_once:
            notification_message += " (one-off, now disabled)"
        
        await send_user_notification(
            prompt.user_id,
            {
                "type": "scheduled_prompt",
                "status": "success",
                "title": f"Scheduled prompt completed",
                "message": notification_message,
                "chat_id": chat_id,
                "prompt_id": prompt.id,
            }
        )
        
        return {
            "success": True,
            "chat_id": chat_id,
            "response": assistant_content[:200] + "..." if len(assistant_content) > 200 else assistant_content,
        }
        
    except Exception as e:
        log.error(f"[Scheduler] Error executing prompt {prompt.id}: {e}")
        
        # Calculate next run time even on failure
        next_run_at = calculate_next_run(prompt.cron_expression, prompt.timezone)
        
        # Update execution status with error
        ScheduledPrompts.update_execution_status(
            prompt.id,
            status="error",
            error=str(e),
            next_run_at=next_run_at,
        )
        
        # Send error notification to user
        await send_user_notification(
            prompt.user_id,
            {
                "type": "scheduled_prompt",
                "status": "error",
                "title": f"Scheduled prompt failed",
                "message": f"'{prompt.name}' failed: {str(e)[:100]}",
                "prompt_id": prompt.id,
            }
        )
        
        raise


async def scheduler_loop(app):
    """
    Main scheduler loop. Runs continuously, checking for due prompts every minute.
    """
    global _scheduler_running
    _scheduler_running = True
    
    log.info("[Scheduler] Starting scheduler loop")
    
    while _scheduler_running:
        try:
            current_time = int(time.time())
            
            # Get all due prompts
            due_prompts = ScheduledPrompts.get_due_scheduled_prompts(current_time)
            
            if due_prompts:
                log.info(f"[Scheduler] Found {len(due_prompts)} due prompt(s)")
            
            for prompt in due_prompts:
                try:
                    await execute_scheduled_prompt(app, prompt)
                except Exception as e:
                    log.error(f"[Scheduler] Failed to execute prompt {prompt.id}: {e}")
                    # Continue with other prompts even if one fails
            
        except Exception as e:
            log.error(f"[Scheduler] Error in scheduler loop: {e}")
        
        # Wait for next check interval
        await asyncio.sleep(SCHEDULER_CHECK_INTERVAL)
    
    log.info("[Scheduler] Scheduler loop stopped")


def start_scheduler(app):
    """
    Start the scheduler background task.
    Called from FastAPI lifespan startup.
    """
    global _scheduler_task
    
    if _scheduler_task is not None:
        log.warning("[Scheduler] Scheduler already running")
        return
    
    log.info("[Scheduler] Starting scheduler service")
    _scheduler_task = asyncio.create_task(scheduler_loop(app))


def stop_scheduler():
    """
    Stop the scheduler background task.
    Called from FastAPI lifespan shutdown.
    """
    global _scheduler_task, _scheduler_running
    
    log.info("[Scheduler] Stopping scheduler service")
    _scheduler_running = False
    
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None


def is_scheduler_running() -> bool:
    """Check if the scheduler is currently running."""
    return _scheduler_running and _scheduler_task is not None


async def send_user_notification(user_id: str, data: dict):
    """
    Send a notification to a user via websocket.
    
    Args:
        user_id: The user ID to notify
        data: Notification data dict with type, status, title, message, etc.
    """
    try:
        from open_webui.socket.main import sio, USER_POOL
        
        # Get user's active session IDs
        session_ids = USER_POOL.get(user_id, [])
        
        if not session_ids:
            log.debug(f"[Scheduler] User {user_id} not online, skipping notification")
            return
        
        # Emit notification to only the first/primary session to avoid duplicates
        # (user may have multiple tabs open)
        await sio.emit(
            "notification",
            data,
            to=session_ids[0],
        )
        
        log.debug(f"[Scheduler] Sent notification to user {user_id}: {data.get('title')}")
        
    except Exception as e:
        log.warning(f"[Scheduler] Failed to send notification: {e}")
