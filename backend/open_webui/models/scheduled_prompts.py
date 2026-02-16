import logging
import time
import uuid
from typing import Optional, List, Literal

from open_webui.internal.db import Base, get_db, JSONField
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, Integer, Index

####################
# ScheduledPrompt DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class ScheduledPrompt(Base):
    __tablename__ = "scheduled_prompt"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    name = Column(Text, nullable=False)
    
    # Schedule configuration
    cron_expression = Column(String, nullable=False)  # e.g., "0 9 * * 1-5"
    timezone = Column(String, default="UTC")
    enabled = Column(Boolean, default=True)
    
    # Prompt configuration
    model_id = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=True)  # Optional system message
    prompt = Column(Text, nullable=False)  # User prompt to send
    
    # Chat linking
    chat_id = Column(String, nullable=True)  # Link to existing chat (updated after first run)
    create_new_chat = Column(Boolean, default=True)  # Create new chat each time vs append
    run_once = Column(Boolean, default=False)  # If True, disable after first successful run
    
    # Tools
    tool_ids = Column(JSONField, nullable=True)  # List of tool IDs to enable for this prompt
    function_calling_mode = Column(
        String,
        nullable=False,
        default="default",
        server_default="default",
    )  # default | native | auto
    
    # Execution tracking
    last_run_at = Column(BigInteger, nullable=True)
    next_run_at = Column(BigInteger, nullable=True)
    last_status = Column(String, nullable=True)  # "success", "error", "running"
    last_error = Column(Text, nullable=True)
    run_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        Index("scheduled_prompt_user_id_idx", "user_id"),
        Index("scheduled_prompt_enabled_next_run_idx", "enabled", "next_run_at"),
        Index("scheduled_prompt_user_id_enabled_idx", "user_id", "enabled"),
    )


class ScheduledPromptModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    
    cron_expression: str
    timezone: str = "UTC"
    enabled: bool = True
    
    model_id: str
    system_prompt: Optional[str] = None
    prompt: str
    
    chat_id: Optional[str] = None
    create_new_chat: bool = True
    run_once: bool = False
    tool_ids: Optional[List[str]] = None
    function_calling_mode: Literal["default", "native", "auto"] = "default"
    
    last_run_at: Optional[int] = None
    next_run_at: Optional[int] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    run_count: int = 0
    
    created_at: int
    updated_at: int


####################
# Forms
####################


class ScheduledPromptForm(BaseModel):
    name: str
    cron_expression: str
    timezone: str = "UTC"
    enabled: bool = True
    model_id: str
    system_prompt: Optional[str] = None
    prompt: str
    create_new_chat: bool = True
    run_once: bool = False
    tool_ids: Optional[List[str]] = None
    function_calling_mode: Literal["default", "native", "auto"] = "default"


class ScheduledPromptUpdateForm(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    enabled: Optional[bool] = None
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None
    prompt: Optional[str] = None
    create_new_chat: Optional[bool] = None
    run_once: Optional[bool] = None
    tool_ids: Optional[List[str]] = None
    function_calling_mode: Optional[Literal["default", "native", "auto"]] = None


class ScheduledPromptResponse(BaseModel):
    id: str
    user_id: str
    name: str
    cron_expression: str
    timezone: str
    enabled: bool
    model_id: str
    system_prompt: Optional[str] = None
    prompt: str
    chat_id: Optional[str] = None
    create_new_chat: bool = True
    run_once: bool = False
    tool_ids: Optional[List[str]] = None
    function_calling_mode: Literal["default", "native", "auto"] = "default"
    last_run_at: Optional[int] = None
    next_run_at: Optional[int] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    run_count: int
    created_at: int
    updated_at: int


class ScheduledPromptUserResponse(ScheduledPromptModel):
    """ScheduledPrompt model with user information for list responses"""
    user: Optional[UserResponse] = None


####################
# Table Operations
####################


class ScheduledPromptTable:
    def insert_new_scheduled_prompt(
        self, user_id: str, form_data: ScheduledPromptForm, next_run_at: Optional[int] = None
    ) -> Optional[ScheduledPromptModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            
            scheduled_prompt = ScheduledPromptModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "name": form_data.name,
                    "cron_expression": form_data.cron_expression,
                    "timezone": form_data.timezone,
                    "enabled": form_data.enabled,
                    "model_id": form_data.model_id,
                    "system_prompt": form_data.system_prompt,
                    "prompt": form_data.prompt,
                    "create_new_chat": form_data.create_new_chat,
                    "run_once": form_data.run_once,
                    "tool_ids": form_data.tool_ids,
                    "function_calling_mode": form_data.function_calling_mode,
                    "next_run_at": next_run_at,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            result = ScheduledPrompt(**scheduled_prompt.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return ScheduledPromptModel.model_validate(result) if result else None

    def get_scheduled_prompts(self) -> list[ScheduledPromptUserResponse]:
        """Get all scheduled prompts with user information"""
        with get_db() as db:
            all_prompts = db.query(ScheduledPrompt).order_by(ScheduledPrompt.updated_at.desc()).all()

            user_ids = list(set(prompt.user_id for prompt in all_prompts))
            users = Users.get_users_by_user_ids(user_ids) if user_ids else []
            users_dict = {user.id: user for user in users}

            prompts = []
            for prompt in all_prompts:
                user = users_dict.get(prompt.user_id)
                prompts.append(
                    ScheduledPromptUserResponse.model_validate(
                        {
                            **ScheduledPromptModel.model_validate(prompt).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return prompts

    def get_scheduled_prompts_by_user_id(self, user_id: str) -> list[ScheduledPromptModel]:
        """Get all scheduled prompts for a specific user"""
        with get_db() as db:
            prompts = (
                db.query(ScheduledPrompt)
                .filter(ScheduledPrompt.user_id == user_id)
                .order_by(ScheduledPrompt.updated_at.desc())
                .all()
            )
            return [ScheduledPromptModel.model_validate(p) for p in prompts]

    def get_enabled_scheduled_prompts(self) -> list[ScheduledPromptModel]:
        """Get all enabled scheduled prompts (for scheduler)"""
        with get_db() as db:
            prompts = (
                db.query(ScheduledPrompt)
                .filter(ScheduledPrompt.enabled == True)
                .order_by(ScheduledPrompt.next_run_at.asc())
                .all()
            )
            return [ScheduledPromptModel.model_validate(p) for p in prompts]

    def get_due_scheduled_prompts(self, current_time: int) -> list[ScheduledPromptModel]:
        """Get all enabled prompts that are due to run"""
        with get_db() as db:
            prompts = (
                db.query(ScheduledPrompt)
                .filter(
                    ScheduledPrompt.enabled == True,
                    ScheduledPrompt.next_run_at <= current_time,
                    ScheduledPrompt.next_run_at != None,
                )
                .order_by(ScheduledPrompt.next_run_at.asc())
                .all()
            )
            return [ScheduledPromptModel.model_validate(p) for p in prompts]

    def get_scheduled_prompt_by_id(self, id: str) -> Optional[ScheduledPromptModel]:
        with get_db() as db:
            prompt = db.query(ScheduledPrompt).filter(ScheduledPrompt.id == id).first()
            return ScheduledPromptModel.model_validate(prompt) if prompt else None

    def get_scheduled_prompt_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[ScheduledPromptModel]:
        with get_db() as db:
            prompt = (
                db.query(ScheduledPrompt)
                .filter(ScheduledPrompt.id == id, ScheduledPrompt.user_id == user_id)
                .first()
            )
            return ScheduledPromptModel.model_validate(prompt) if prompt else None

    def update_scheduled_prompt_by_id(
        self, id: str, form_data: ScheduledPromptUpdateForm, next_run_at: Optional[int] = None
    ) -> Optional[ScheduledPromptModel]:
        with get_db() as db:
            prompt = db.query(ScheduledPrompt).filter(ScheduledPrompt.id == id).first()
            
            if not prompt:
                return None

            # Update fields if provided
            if form_data.name is not None:
                prompt.name = form_data.name
            if form_data.cron_expression is not None:
                prompt.cron_expression = form_data.cron_expression
            if form_data.timezone is not None:
                prompt.timezone = form_data.timezone
            if form_data.enabled is not None:
                prompt.enabled = form_data.enabled
            if form_data.model_id is not None:
                prompt.model_id = form_data.model_id
            if form_data.system_prompt is not None:
                prompt.system_prompt = form_data.system_prompt
            if form_data.prompt is not None:
                prompt.prompt = form_data.prompt
            if form_data.create_new_chat is not None:
                prompt.create_new_chat = form_data.create_new_chat
            if form_data.run_once is not None:
                prompt.run_once = form_data.run_once
            if form_data.tool_ids is not None:
                prompt.tool_ids = form_data.tool_ids
            if form_data.function_calling_mode is not None:
                prompt.function_calling_mode = form_data.function_calling_mode
            if next_run_at is not None:
                prompt.next_run_at = next_run_at
                
            prompt.updated_at = int(time.time())

            db.commit()
            db.refresh(prompt)
            return ScheduledPromptModel.model_validate(prompt)

    def update_execution_status(
        self,
        id: str,
        status: str,
        error: Optional[str] = None,
        chat_id: Optional[str] = None,
        next_run_at: Optional[int] = None,
    ) -> Optional[ScheduledPromptModel]:
        """Update execution status after a run"""
        with get_db() as db:
            prompt = db.query(ScheduledPrompt).filter(ScheduledPrompt.id == id).first()
            
            if not prompt:
                return None

            prompt.last_run_at = int(time.time())
            prompt.last_status = status
            prompt.last_error = error
            prompt.run_count = (prompt.run_count or 0) + 1
            
            if chat_id is not None:
                prompt.chat_id = chat_id
            if next_run_at is not None:
                prompt.next_run_at = next_run_at
                
            prompt.updated_at = int(time.time())

            db.commit()
            db.refresh(prompt)
            return ScheduledPromptModel.model_validate(prompt)

    def set_next_run_at(self, id: str, next_run_at: int) -> Optional[ScheduledPromptModel]:
        """Update the next run time for a scheduled prompt"""
        with get_db() as db:
            prompt = db.query(ScheduledPrompt).filter(ScheduledPrompt.id == id).first()
            
            if not prompt:
                return None

            prompt.next_run_at = next_run_at
            prompt.updated_at = int(time.time())

            db.commit()
            db.refresh(prompt)
            return ScheduledPromptModel.model_validate(prompt)

    def delete_scheduled_prompt_by_id(self, id: str) -> bool:
        with get_db() as db:
            prompt = db.query(ScheduledPrompt).filter(ScheduledPrompt.id == id).first()
            
            if not prompt:
                return False

            db.delete(prompt)
            db.commit()
            return True

    def delete_scheduled_prompts_by_user_id(self, user_id: str) -> bool:
        with get_db() as db:
            db.query(ScheduledPrompt).filter(ScheduledPrompt.user_id == user_id).delete()
            db.commit()
            return True

    def count_scheduled_prompts_by_user_id(self, user_id: str) -> int:
        """Count scheduled prompts for a user (for rate limiting)"""
        with get_db() as db:
            return (
                db.query(ScheduledPrompt)
                .filter(ScheduledPrompt.user_id == user_id)
                .count()
            )


ScheduledPrompts = ScheduledPromptTable()
