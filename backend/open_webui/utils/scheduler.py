"""
Scheduler service for executing scheduled prompts.

Uses asyncio for lightweight scheduling without external dependencies.
Checks the database every minute for due jobs and executes them.
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import aiohttp
from croniter import croniter

from open_webui.models.scheduled_prompts import (
    ScheduledPrompts,
    ScheduledPromptModel,
    ScheduledPromptUpdateForm,
)
from open_webui.models.chats import Chats, ChatForm
from open_webui.models.users import Users
from open_webui.utils.auth import create_token
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("SCHEDULER", logging.INFO))

# Global scheduler task reference
_scheduler_task: Optional[asyncio.Task] = None
_scheduler_running = False

# Check interval in seconds
SCHEDULER_CHECK_INTERVAL = 60

# Max concurrent prompt executions
_execution_semaphore = asyncio.Semaphore(5)


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


def get_webui_base_url(app) -> Optional[str]:
    """
    Get configured public WebUI URL from app config.
    Returns a normalized URL without trailing slash, or None if unavailable.
    """
    config = getattr(getattr(app, "state", None), "config", None)
    raw_url = getattr(config, "WEBUI_URL", "") if config else ""
    base_url = str(raw_url or "").strip().rstrip("/")

    if not base_url:
        log.debug(
            "[Scheduler] WEBUI_URL is empty; skipping deep-link generation for scheduled prompt notifications"
        )
        return None

    return base_url


def build_webui_url(app, path: str) -> Optional[str]:
    """Build an absolute WebUI URL for an app-relative path."""
    base_url = get_webui_base_url(app)
    if not base_url:
        return None

    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base_url}{normalized_path}"


def get_chat_completions_api_url(app) -> str:
    """Get the API URL for chat completions, preferring configured WEBUI_URL when available."""
    configured_api_url = build_webui_url(app, "/api/chat/completions")
    if configured_api_url:
        return configured_api_url

    port = os.environ.get("PORT", "8080")
    return f"http://127.0.0.1:{port}/api/chat/completions"


def truncate_text_for_notification(text: str, max_length: int = 500) -> str:
    """Truncate text for notification display while preserving readability."""
    cleaned = (text or "").strip()
    if len(cleaned) <= max_length:
        return cleaned

    return f"{cleaned[:max_length].rstrip()}..."


def is_notes_tool_enabled(action_tools: list[str]) -> bool:
    """Return True when either notes_manager or note_manager tool id is enabled."""
    return any(
        isinstance(tool_id, str)
        and ("notes_manager" in tool_id.lower() or "note_manager" in tool_id.lower())
        for tool_id in (action_tools or [])
    )


def source_matches_note_function(source_name: str, function_name: str) -> bool:
    """Match note tool source names regardless of tool id aliasing."""
    normalized = str(source_name or "").lower()
    target = function_name.lower()
    return normalized == target or normalized.endswith(f"/{target}")


def extract_note_attachments_from_sources(sources: list) -> list[dict]:
    """Extract notes_manager/get_note payloads from citation sources."""
    attachments = []

    for source in sources or []:
        source_name = str(source.get("source", {}).get("name", ""))
        if not source_matches_note_function(source_name, "get_note"):
            continue

        documents = source.get("document") or []
        metadata = source.get("metadata") or []

        for idx, document in enumerate(documents):
            if not isinstance(document, str) or not document.strip():
                continue

            metadata_item = metadata[idx] if idx < len(metadata) and isinstance(metadata[idx], dict) else {}
            parameters = metadata_item.get("parameters", {}) if isinstance(metadata_item, dict) else {}
            note_id = parameters.get("note_id") if isinstance(parameters, dict) else None

            attachments.append(
                {
                    "note_id": note_id,
                    "content": document.strip(),
                }
            )

    return attachments


def extract_note_ids_from_list_sources(sources: list) -> list[str]:
    """Extract note IDs from note listing/search citation documents."""
    note_ids: list[str] = []
    uuid_pattern = re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    )

    for source in sources or []:
        source_name = str(source.get("source", {}).get("name", ""))
        if not (
            source_matches_note_function(source_name, "list_my_notes")
            or source_matches_note_function(source_name, "search_notes")
        ):
            continue

        for document in source.get("document") or []:
            if not isinstance(document, str):
                continue

            for match in uuid_pattern.findall(document):
                if match not in note_ids:
                    note_ids.append(match)

    return note_ids


def extract_get_note_ids_and_failures(sources: list) -> tuple[list[str], bool]:
    """Extract note_id parameters used in get_note calls and detect explicit lookup failures."""
    used_note_ids: list[str] = []
    has_not_found_error = False

    for source in sources or []:
        source_name = str(source.get("source", {}).get("name", ""))
        if not source_matches_note_function(source_name, "get_note"):
            continue

        for document in source.get("document") or []:
            if isinstance(document, str) and "note not found" in document.lower():
                has_not_found_error = True

        metadata = source.get("metadata") or []
        for metadata_item in metadata:
            if not isinstance(metadata_item, dict):
                continue
            parameters = metadata_item.get("parameters", {})
            if not isinstance(parameters, dict):
                continue
            note_id = parameters.get("note_id")
            if isinstance(note_id, str) and note_id.strip():
                used_note_ids.append(note_id.strip())

    return used_note_ids, has_not_found_error


def sanitize_tool_chatter_text(content: str, action_tools: list[str]) -> str:
    """Remove malformed tool-call chatter prefixes while preserving final user-facing output."""
    if not isinstance(content, str) or not content.strip():
        return content

    lowered = content.lower()
    tool_mentions = [tool_id.lower() for tool_id in (action_tools or [])]
    if "to=" not in lowered or not any(tool in lowered for tool in tool_mentions):
        return content

    blocks = [block.strip() for block in re.split(r"\n{2,}", content) if block.strip()]
    if len(blocks) > 1:
        for block in reversed(blocks):
            block_lower = block.lower()
            if "to=" in block_lower and any(tool in block_lower for tool in tool_mentions):
                continue
            if "need proper json" in block_lower or "commentary" in block_lower:
                continue
            return block

    cleaned = re.sub(
        r"(?:\bto=[^\s]+(?:\s+commentary)?(?:\s+[^\s]{1,30})?\s*){2,}",
        "",
        content,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned or content


async def execute_scheduled_prompt(app, prompt: ScheduledPromptModel) -> dict:
    """
    Execute a single scheduled prompt.
    
    Args:
        app: FastAPI application instance (for accessing models and config)
        prompt: The scheduled prompt to execute
    
    Returns:
        dict with execution result including chat_id
    """
    log.info(f"[Scheduler] Executing scheduled prompt: {prompt.id} - {prompt.name}")
    user = None
    
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

        function_calling_mode = getattr(prompt, "function_calling_mode", "default") or "default"
        if function_calling_mode in ["default", "native"]:
            payload["params"] = {
                "function_calling": function_calling_mode,
            }
        else:
            # "auto" defers to model/open-webui defaults.
            function_calling_mode = "auto"

        log.info(
            f"[Scheduler] Function calling mode for prompt {prompt.id}: {function_calling_mode}"
        )
        
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
        
        # Exclude prompt_scheduler from execution tools to avoid recursive scheduling calls.
        action_tools = [t for t in (tool_ids or []) if "prompt_scheduler" not in t.lower()]

        if tool_ids:
            if action_tools:
                payload["tool_ids"] = action_tools
                log.info(f"[Scheduler] Prompt will use tools: {action_tools}")
            else:
                log.info(
                    "[Scheduler] Only prompt_scheduler tool was configured; skipping tool execution for this run"
                )
            
            # Build tool instruction from executable tools only.
            
            if action_tools:
                tool_instruction = f"\n\nIMPORTANT: This is an automated scheduled reminder. You have access to these tools: {', '.join(action_tools)}. Use them to help the user with their request. For example, if this is about a todo list, use the notes_manager tool to fetch the actual current data."
            else:
                tool_instruction = "\n\nIMPORTANT: This is an automated scheduled reminder. Respond helpfully to the user's request."

            if "notes_manager" in action_tools:
                tool_instruction += (
                    "\n\nWhen using notes_manager for todos/notes: do not stop after list_my_notes "
                    "if the user asked for note contents. Use get_note on the relevant note ID "
                    "and summarize the actual items from the note content."
                )
            
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
            expires_delta=timedelta(seconds=600),
        )
        
        # Call the internal API. Prefer configured WEBUI_URL when available,
        # otherwise fall back to localhost for local/dev setups.
        api_url = get_chat_completions_api_url(app)
        
        log.info(f"[Scheduler] Calling API: {api_url}")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        async def _call_chat_completion(request_payload: dict) -> dict:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    headers=headers,
                    json=request_payload,
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text}")
                    return await response.json()

        response_data = await _call_chat_completion(payload)
        
        # Extract the assistant response
        response_message = response_data.get("choices", [{}])[0].get("message", {}) or {}
        assistant_content = (
            response_message.get("content")
            or response_message.get("reasoning_content")
            or ""
        )

        if not assistant_content and response_message.get("tool_calls"):
            log.warning(
                "[Scheduler] Completion returned tool_calls without final text content for prompt %s",
                prompt.id,
            )

            # Some model/tool modes may finish with tool_calls but no final assistant text.
            # Retry once in default mode so scheduler runs still produce a visible response.
            if function_calling_mode != "default":
                retry_payload = dict(payload)
                retry_params = dict(retry_payload.get("params", {}))
                retry_params["function_calling"] = "default"
                retry_payload["params"] = retry_params

                log.info(
                    "[Scheduler] Retrying prompt %s with function_calling=default for final text",
                    prompt.id,
                )

                response_data = await _call_chat_completion(retry_payload)
                response_message = (
                    response_data.get("choices", [{}])[0].get("message", {}) or {}
                )
                assistant_content = (
                    response_message.get("content")
                    or response_message.get("reasoning_content")
                    or ""
                )

            if not assistant_content:
                assistant_content = (
                    "Scheduled prompt completed, but the model returned only tool calls and no final text."
                )

        # If model returns a raw tool-call JSON string instead of a user-facing answer,
        # run one continuation turn to execute that requested tool call and produce
        # plain-language output.
        raw_tool_request = None
        if isinstance(assistant_content, str) and assistant_content.strip().startswith("{"):
            try:
                parsed_content = json.loads(assistant_content.strip())
                if isinstance(parsed_content, dict) and (
                    parsed_content.get("tool") or parsed_content.get("tool_calls")
                ):
                    raw_tool_request = parsed_content
            except Exception:
                raw_tool_request = None

        if raw_tool_request and action_tools:
            log.info(
                "[Scheduler] Detected raw tool-call JSON output for prompt %s; running continuation pass",
                prompt.id,
            )

            continuation_messages = [
                *messages,
                {"role": "assistant", "content": assistant_content},
                {
                    "role": "user",
                    "content": (
                        "Execute the requested tool call(s) above, then answer the original user request "
                        "in plain language. Do not return tool-call JSON."
                    ),
                },
            ]

            continuation_payload = {
                "model": model_id,
                "messages": continuation_messages,
                "stream": False,
                "tool_ids": action_tools,
                "params": {"function_calling": "default"},
            }

            continuation_response = await _call_chat_completion(continuation_payload)
            continuation_message = (
                continuation_response.get("choices", [{}])[0].get("message", {}) or {}
            )
            continuation_content = (
                continuation_message.get("content")
                or continuation_message.get("reasoning_content")
                or ""
            )

            if continuation_content:
                assistant_content = continuation_content
                response_data = continuation_response

        assistant_content_lower = (assistant_content or "").lower()
        chatter_markers = [
            "to=",
            "tool call",
            "tool_call",
            "arguments",
            "need proper json",
            "do not output json",
            "json",
        ]
        mentions_configured_tool = any(
            tool_id.lower() in assistant_content_lower for tool_id in action_tools
        )
        has_malformed_tool_chatter = (
            any(marker in assistant_content_lower for marker in chatter_markers)
            and mentions_configured_tool
        )

        if has_malformed_tool_chatter and action_tools:
            log.info(
                "[Scheduler] Detected malformed tool-call chatter for prompt %s; forcing generic continuation",
                prompt.id,
            )

            latest_sources = (
                response_data.get("sources", []) if isinstance(response_data, dict) else []
            )
            if not isinstance(latest_sources, list):
                latest_sources = []

            note_ids_from_list = (
                extract_note_ids_from_list_sources(latest_sources)
                if is_notes_tool_enabled(action_tools)
                else []
            )

            if note_ids_from_list:
                notes_hint = (
                    " Use get_note with parameter note_id and one of these IDs: "
                    f"{', '.join(note_ids_from_list[:5])}. "
                    "Do not call list_my_notes/search_notes again unless none of these IDs work."
                )
            else:
                notes_hint = ""

            forced_tool_messages = [
                *messages,
                {
                    "role": "user",
                    "content": (
                        "Your prior attempt produced malformed tool-call chatter. "
                        "Execute the intended tool call(s) using available tools, then answer the original "
                        "request in plain language with concrete results. "
                        "Do not include tool-call syntax, commentary, analysis text, or JSON."
                        f"{notes_hint}"
                    ),
                },
            ]

            forced_tool_payload = {
                "model": model_id,
                "messages": forced_tool_messages,
                "stream": False,
                "tool_ids": action_tools,
                "params": {"function_calling": "default"},
            }

            forced_tool_response = await _call_chat_completion(forced_tool_payload)
            forced_tool_message = (
                forced_tool_response.get("choices", [{}])[0].get("message", {}) or {}
            )
            forced_tool_content = (
                forced_tool_message.get("content")
                or forced_tool_message.get("reasoning_content")
                or ""
            )

            if forced_tool_content:
                assistant_content = forced_tool_content
                response_data = forced_tool_response

        if has_malformed_tool_chatter:
            assistant_content = sanitize_tool_chatter_text(assistant_content, action_tools)

        notes_followup_attempts = 0
        while is_notes_tool_enabled(action_tools) and notes_followup_attempts < 2:
            current_sources = response_data.get("sources", []) if isinstance(response_data, dict) else []
            if not isinstance(current_sources, list):
                current_sources = []

            has_list_notes_source = any(
                source_matches_note_function(source.get("source", {}).get("name", ""), "list_my_notes")
                or source_matches_note_function(source.get("source", {}).get("name", ""), "search_notes")
                for source in current_sources
            )
            has_get_note_source = any(
                source_matches_note_function(source.get("source", {}).get("name", ""), "get_note")
                for source in current_sources
            )

            note_ids_from_list = extract_note_ids_from_list_sources(current_sources)
            used_get_note_ids, has_not_found_get_note = extract_get_note_ids_and_failures(
                current_sources
            )

            used_expected_note_id = any(
                used_id in note_ids_from_list for used_id in used_get_note_ids
            )

            needs_notes_followup = has_list_notes_source and (
                not has_get_note_source
                or has_not_found_get_note
                or (note_ids_from_list and not used_expected_note_id)
            )

            # If we already have concrete note content (get_note), do not force another turn.
            if not needs_notes_followup:
                break

            if not note_ids_from_list:
                break

            notes_followup_attempts += 1
            note_id_candidates = ", ".join(note_ids_from_list[:5])
            log.info(
                "[Scheduler] Prompt %s returned note listing without successful get_note; forcing notes follow-up pass %s",
                prompt.id,
                notes_followup_attempts,
            )

            followup_messages = [
                *messages,
                {"role": "assistant", "content": assistant_content},
                {
                    "role": "user",
                    "content": (
                        "You MUST call get_note with parameter note_id using one of these IDs: "
                        f"{note_id_candidates}. "
                        "Use the exact UUID from the ID column, not the note title. "
                        "Do not call list_my_notes/search_notes again unless every provided ID fails. "
                        "After retrieving the note content, answer the original request in plain language."
                    ),
                },
            ]

            followup_payload = {
                "model": model_id,
                "messages": followup_messages,
                "stream": False,
                "tool_ids": action_tools,
                "params": {"function_calling": "default"},
            }

            followup_response = await _call_chat_completion(followup_payload)
            followup_message = (
                followup_response.get("choices", [{}])[0].get("message", {}) or {}
            )
            followup_content = (
                followup_message.get("content")
                or followup_message.get("reasoning_content")
                or ""
            )

            if followup_content:
                assistant_content = sanitize_tool_chatter_text(followup_content, action_tools)
                response_data = followup_response
            else:
                break
        
        response_sources = response_data.get("sources", []) if isinstance(response_data, dict) else []
        if not isinstance(response_sources, list):
            response_sources = []

        note_attachments = extract_note_attachments_from_sources(response_sources)

        timestamp = int(time.time())

        assistant_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": assistant_content,
            "timestamp": timestamp,
            "models": [model_id],
        }

        if response_sources:
            assistant_message["sources"] = response_sources
            # Keep both keys for compatibility with chat UIs that reference either.
            assistant_message["citations"] = response_sources

        if note_attachments:
            # Persist note payloads on the message without duplicating full note
            # content in the user-visible assistant text.
            assistant_message["note_attachments"] = note_attachments
        
        # Build chat messages (only user + assistant, system prompt is hidden context)
        chat_messages = [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": prompt.prompt,
                "timestamp": timestamp,
                "models": [model_id],
            },
            assistant_message,
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
            # Include executable tool_ids in chat data so UI can restore them.
            if action_tools:
                chat_data["tool_ids"] = action_tools
                log.info(f"[Scheduler] Saving chat with tool_ids: {action_tools}")
            
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
                # Include executable tool_ids in chat data so UI can restore them.
                if action_tools:
                    chat_data["tool_ids"] = action_tools
                    log.info(f"[Scheduler] Saving fallback chat with tool_ids: {action_tools}")
                
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
        
        scheduled_prompts_url = build_webui_url(app, "/workspace/scheduled-prompts")
        chat_url = build_webui_url(app, f"/c/{chat_id}") if chat_id else None

        # Fallback for local/dev setups where WEBUI_URL is not configured.
        if not scheduled_prompts_url:
            port = os.environ.get("PORT", "8080")
            scheduled_prompts_url = (
                f"http://127.0.0.1:{port}/workspace/scheduled-prompts"
            )
        if chat_id and not chat_url:
            port = os.environ.get("PORT", "8080")
            chat_url = f"http://127.0.0.1:{port}/c/{chat_id}"

        # Send notification to user via websocket
        notification_message = f"'{prompt.name}' ran successfully"
        if prompt.run_once:
            notification_message += " (one-off, now disabled)"

        output_preview = truncate_text_for_notification(assistant_content)
        ntfy_message = notification_message
        if output_preview:
            ntfy_message = f"{ntfy_message}\n\nOutput:\n{output_preview}"
        
        await send_user_notification(
            prompt.user_id,
            {
                "type": "scheduled_prompt",
                "status": "success",
                "title": f"Scheduled prompt completed",
                "message": notification_message,
                "chat_id": chat_id,
                "chat_url": chat_url,
                "scheduled_prompts_url": scheduled_prompts_url,
                "prompt_id": prompt.id,
            }
        )

        await send_ntfy_notification(
            user,
            {
                "status": "success",
                "title": "Scheduled prompt completed",
                "message": ntfy_message,
                "prompt_name": prompt.name,
                "prompt_id": prompt.id,
                "chat_id": chat_id,
                "chat_url": chat_url,
                "scheduled_prompts_url": scheduled_prompts_url,
            },
        )
        
        return {
            "success": True,
            "chat_id": chat_id,
            "response": assistant_content[:200] + "..." if len(assistant_content) > 200 else assistant_content,
        }
        
    except Exception as e:
        log.error(f"[Scheduler] Error executing prompt {prompt.id}: {e}")
        
        if prompt.run_once:
            # One-off prompts: disable on failure, don't retry forever
            ScheduledPrompts.update_execution_status(
                prompt.id,
                status="error",
                error=str(e),
                next_run_at=None,
            )
            ScheduledPrompts.update_scheduled_prompt_by_id(
                prompt.id,
                ScheduledPromptUpdateForm(enabled=False),
            )
            log.warning(f"[Scheduler] One-off prompt {prompt.id} failed and disabled")
        else:
            # Recurring prompts: schedule next run despite failure
            next_run_at = calculate_next_run(prompt.cron_expression, prompt.timezone)
            ScheduledPrompts.update_execution_status(
                prompt.id,
                status="error",
                error=str(e),
                next_run_at=next_run_at,
            )
        
        # Send error notification to user
        scheduled_prompts_url = build_webui_url(app, "/workspace/scheduled-prompts")
        if not scheduled_prompts_url:
            port = os.environ.get("PORT", "8080")
            scheduled_prompts_url = (
                f"http://127.0.0.1:{port}/workspace/scheduled-prompts"
            )

        await send_user_notification(
            prompt.user_id,
            {
                "type": "scheduled_prompt",
                "status": "error",
                "title": "Scheduled prompt failed",
                "message": f"'{prompt.name}' failed: {str(e)[:200]}",
                "prompt_id": prompt.id,
                "scheduled_prompts_url": scheduled_prompts_url,
            }
        )

        await send_ntfy_notification(
            user,
            {
                "status": "error",
                "title": "Scheduled prompt failed",
                "message": f"'{prompt.name}' failed: {str(e)[:200]}",
                "prompt_name": prompt.name,
                "prompt_id": prompt.id,
                "scheduled_prompts_url": scheduled_prompts_url,
            },
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
            
            # Execute prompts concurrently with a semaphore to limit parallelism
            async def _run_with_semaphore(p):
                async with _execution_semaphore:
                    await execute_scheduled_prompt(app, p)
            
            tasks = [asyncio.create_task(_run_with_semaphore(p)) for p in due_prompts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for prompt, result in zip(due_prompts, results):
                if isinstance(result, Exception):
                    log.error(f"[Scheduler] Failed to execute prompt {prompt.id}: {result}")
            
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
        
        # Emit notification to all active sessions so every tab gets it
        for sid in session_ids:
            await sio.emit(
                "notification",
                data,
                to=sid,
            )
        
        log.debug(f"[Scheduler] Sent notification to user {user_id} ({len(session_ids)} session(s)): {data.get('title')}")
        
    except Exception as e:
        log.warning(f"[Scheduler] Failed to send notification: {e}")


async def send_ntfy_notification(user, data: dict):
    """
    Send scheduled prompt notification to ntfy.sh (or compatible self-hosted ntfy server).

    Expected user settings path:
      user.settings.ui.notifications.ntfy = {
          enabled: bool,
          server_url: str,
          topic: str,
          token: str (optional)
      }
    """
    try:
        if not user or not getattr(user, "settings", None):
            return

        settings_dict = (
            user.settings.model_dump() if hasattr(user.settings, "model_dump") else {}
        )
        notifications = settings_dict.get("ui", {}).get("notifications", {})
        ntfy = notifications.get("ntfy", {}) or {}

        if not ntfy.get("enabled"):
            return

        server_url = (ntfy.get("server_url") or "https://ntfy.sh").rstrip("/")
        topic = (ntfy.get("topic") or "").strip().strip("/")
        token = (ntfy.get("token") or "").strip()

        if not topic:
            log.debug("[Scheduler] ntfy enabled but topic is empty; skipping")
            return

        url = f"{server_url}/{topic}"
        status = data.get("status", "info")
        title = data.get("title") or "Scheduled prompt notification"
        message = data.get("message") or "Scheduled prompt update"
        click_url = data.get("chat_url") or data.get("scheduled_prompts_url") or data.get("url")

        headers = {
            "Title": title,
            "Tags": "calendar" if status == "success" else "warning",
            "Priority": "default" if status == "success" else "high",
        }
        if click_url:
            headers["Click"] = click_url

        actions = []
        if data.get("chat_url"):
            actions.append(f"view, Open Chat, {data.get('chat_url')}")
        if data.get("scheduled_prompts_url"):
            actions.append(
                f"view, Scheduled Prompts, {data.get('scheduled_prompts_url')}"
            )
        if actions:
            headers["Actions"] = "; ".join(actions)
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                data=message.encode("utf-8"),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.warning(
                        f"[Scheduler] ntfy notification failed ({response.status}): {error_text}"
                    )
                    return

        log.debug(
            f"[Scheduler] Sent ntfy notification for user {user.id}: {data.get('title')}"
        )
    except Exception as e:
        log.warning(f"[Scheduler] Failed to send ntfy notification: {e}")
