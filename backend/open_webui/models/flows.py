import logging
import time
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Index, JSON, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.users import UserResponse, Users

log = logging.getLogger(__name__)


class Flow(Base):
    __tablename__ = 'flow'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    nodes = Column(JSON, nullable=False)
    edges = Column(JSON, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    meta = Column(JSON, nullable=False, default=dict)
    access_control = Column(JSON, nullable=True)

    __table_args__ = (
        Index('flow_user_id_idx', 'user_id'),
        Index('flow_updated_at_idx', 'updated_at'),
        Index('flow_user_id_updated_at_idx', 'user_id', 'updated_at'),
    )


class FlowModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    nodes: list
    edges: list
    created_at: int
    updated_at: int
    meta: dict = {}
    access_control: Optional[dict] = None


class FlowForm(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: list
    edges: list
    access_control: Optional[dict] = None


class FlowUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[list] = None
    edges: Optional[list] = None
    access_control: Optional[dict] = None


class FlowResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    nodes: list
    edges: list
    created_at: int
    updated_at: int
    meta: dict = {}
    access_control: Optional[dict] = None


class FlowUserResponse(FlowModel):
    user: Optional[UserResponse] = None


class FlowListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    nodes: list
    edges: list
    created_at: int
    updated_at: int
    meta: dict = {}
    access_control: Optional[dict] = None


class FlowTable:
    async def insert_new_flow(
        self, user_id: str, form_data: FlowForm, db: Optional[AsyncSession] = None
    ) -> Optional[FlowModel]:
        async with get_async_db_context(db) as db:
            try:
                current_time = int(time.time())
                result = Flow(
                    id=str(uuid4()),
                    user_id=user_id,
                    name=form_data.name,
                    description=form_data.description,
                    nodes=form_data.nodes,
                    edges=form_data.edges,
                    created_at=current_time,
                    updated_at=current_time,
                    meta={},
                    access_control=form_data.access_control,
                )
                db.add(result)
                await db.commit()
                await db.refresh(result)
                return FlowModel.model_validate(result)
            except Exception as e:
                log.exception(f'Error creating flow: {e}')
                return None

    async def get_flows(self, db: Optional[AsyncSession] = None) -> list[FlowUserResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Flow).order_by(Flow.updated_at.desc()))
            all_flows = result.scalars().all()
            user_ids = list({flow.user_id for flow in all_flows})
            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            flows = []
            for flow in all_flows:
                user = users_dict.get(flow.user_id)
                flows.append(
                    FlowUserResponse.model_validate(
                        {
                            **FlowModel.model_validate(flow).model_dump(),
                            'user': user.model_dump() if user else None,
                        }
                    )
                )
            return flows

    async def get_flow_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[FlowModel]:
        try:
            async with get_async_db_context(db) as db:
                flow = await db.get(Flow, id)
                return FlowModel.model_validate(flow) if flow else None
        except Exception:
            return None

    async def update_flow_by_id(
        self, id: str, form_data: FlowUpdateForm, db: Optional[AsyncSession] = None
    ) -> Optional[FlowModel]:
        try:
            async with get_async_db_context(db) as db:
                values = form_data.model_dump(exclude_unset=True)
                if not values:
                    flow = await db.get(Flow, id)
                    return FlowModel.model_validate(flow) if flow else None

                values['updated_at'] = int(time.time())
                await db.execute(update(Flow).where(Flow.id == id).values(**values))
                await db.commit()
                flow = await db.get(Flow, id)
                if flow:
                    await db.refresh(flow)
                return FlowModel.model_validate(flow) if flow else None
        except Exception as e:
            log.exception(f'Error updating flow {id}: {e}')
            return None

    async def duplicate_flow_by_id(
        self, id: str, user_id: str, name: Optional[str] = None, db: Optional[AsyncSession] = None
    ) -> Optional[FlowModel]:
        async with get_async_db_context(db) as db:
            original_flow = await db.get(Flow, id)
            if not original_flow:
                return None

            current_time = int(time.time())
            result = Flow(
                id=str(uuid4()),
                user_id=user_id,
                name=name if name else f'{original_flow.name} (Copy)',
                description=original_flow.description,
                nodes=original_flow.nodes,
                edges=original_flow.edges,
                created_at=current_time,
                updated_at=current_time,
                meta=original_flow.meta or {},
                access_control=None,
            )
            db.add(result)
            await db.commit()
            await db.refresh(result)
            return FlowModel.model_validate(result)

    async def delete_flow_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(delete(Flow).where(Flow.id == id))
            await db.commit()
            return result.rowcount > 0

    async def delete_flows_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            await db.execute(delete(Flow).where(Flow.user_id == user_id))
            await db.commit()
            return True


Flows = FlowTable()
