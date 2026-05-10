import logging
import time
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Index, JSON, String, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, get_async_db_context

log = logging.getLogger(__name__)


class FlowExecution(Base):
    __tablename__ = 'flow_execution'

    id = Column(String, primary_key=True)
    flow_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    inputs = Column(JSON, nullable=True)
    outputs = Column(JSON, nullable=True)
    node_results = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    execution_time = Column(BigInteger, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    meta = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index('flow_execution_flow_id_created_at_idx', 'flow_id', 'created_at'),
        Index('flow_execution_user_id_created_at_idx', 'user_id', 'created_at'),
        Index('flow_execution_flow_id_status_idx', 'flow_id', 'status'),
        Index('flow_execution_status_idx', 'status'),
    )


class FlowExecutionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    flow_id: str
    user_id: str
    status: str
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    node_results: Optional[dict] = None
    errors: Optional[dict] = None
    execution_time: int
    created_at: int
    meta: dict = {}


class FlowExecutionForm(BaseModel):
    flow_id: str
    status: str
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    node_results: Optional[dict] = None
    errors: Optional[dict] = None
    execution_time: int


class FlowExecutionResponse(BaseModel):
    id: str
    flow_id: str
    user_id: str
    status: str
    inputs: Optional[dict] = None
    outputs: Optional[dict] = None
    node_results: Optional[dict] = None
    errors: Optional[dict] = None
    execution_time: int
    created_at: int
    meta: dict = {}


class FlowExecutionListResponse(BaseModel):
    id: str
    flow_id: str
    status: str
    execution_time: int
    created_at: int


class FlowExecutionStatsResponse(BaseModel):
    total_executions: int
    success_count: int
    error_count: int
    aborted_count: int
    avg_execution_time: float
    last_execution_at: Optional[int] = None


class FlowExecutionTable:
    async def insert_new_execution(
        self, user_id: str, form_data: FlowExecutionForm, db: Optional[AsyncSession] = None
    ) -> Optional[FlowExecutionModel]:
        async with get_async_db_context(db) as db:
            try:
                result = FlowExecution(
                    id=str(uuid4()),
                    flow_id=form_data.flow_id,
                    user_id=user_id,
                    status=form_data.status,
                    inputs=form_data.inputs,
                    outputs=form_data.outputs,
                    node_results=form_data.node_results,
                    errors=form_data.errors,
                    execution_time=form_data.execution_time,
                    created_at=int(time.time()),
                    meta={},
                )
                db.add(result)
                await db.commit()
                await db.refresh(result)
                return FlowExecutionModel.model_validate(result)
            except Exception as e:
                log.exception(f'Error creating flow execution: {e}')
                return None

    async def get_executions_by_flow_id(
        self, flow_id: str, skip: int = 0, limit: int = 60, db: Optional[AsyncSession] = None
    ) -> list[FlowExecutionModel]:
        async with get_async_db_context(db) as db:
            stmt = select(FlowExecution).where(FlowExecution.flow_id == flow_id).order_by(FlowExecution.created_at.desc())
            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)
            result = await db.execute(stmt)
            return [FlowExecutionModel.model_validate(execution) for execution in result.scalars().all()]

    async def get_executions_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 60, db: Optional[AsyncSession] = None
    ) -> list[FlowExecutionModel]:
        async with get_async_db_context(db) as db:
            stmt = select(FlowExecution).where(FlowExecution.user_id == user_id).order_by(FlowExecution.created_at.desc())
            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)
            result = await db.execute(stmt)
            return [FlowExecutionModel.model_validate(execution) for execution in result.scalars().all()]

    async def get_execution_by_id(
        self, id: str, db: Optional[AsyncSession] = None
    ) -> Optional[FlowExecutionModel]:
        async with get_async_db_context(db) as db:
            execution = await db.get(FlowExecution, id)
            return FlowExecutionModel.model_validate(execution) if execution else None

    async def get_execution_stats_by_flow_id(
        self, flow_id: str, db: Optional[AsyncSession] = None
    ) -> FlowExecutionStatsResponse:
        async with get_async_db_context(db) as db:
            total = await db.scalar(select(func.count(FlowExecution.id)).where(FlowExecution.flow_id == flow_id))
            success_count = await db.scalar(
                select(func.count(FlowExecution.id)).where(
                    FlowExecution.flow_id == flow_id,
                    FlowExecution.status == 'success',
                )
            )
            error_count = await db.scalar(
                select(func.count(FlowExecution.id)).where(
                    FlowExecution.flow_id == flow_id,
                    FlowExecution.status == 'error',
                )
            )
            aborted_count = await db.scalar(
                select(func.count(FlowExecution.id)).where(
                    FlowExecution.flow_id == flow_id,
                    FlowExecution.status == 'aborted',
                )
            )
            avg_time = await db.scalar(select(func.avg(FlowExecution.execution_time)).where(FlowExecution.flow_id == flow_id))
            last_execution = await db.scalar(
                select(FlowExecution).where(FlowExecution.flow_id == flow_id).order_by(FlowExecution.created_at.desc()).limit(1)
            )
            return FlowExecutionStatsResponse(
                total_executions=total or 0,
                success_count=success_count or 0,
                error_count=error_count or 0,
                aborted_count=aborted_count or 0,
                avg_execution_time=float(avg_time or 0.0),
                last_execution_at=last_execution.created_at if last_execution else None,
            )

    async def delete_execution_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(delete(FlowExecution).where(FlowExecution.id == id))
            await db.commit()
            return result.rowcount > 0

    async def delete_executions_by_flow_id(self, flow_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            await db.execute(delete(FlowExecution).where(FlowExecution.flow_id == flow_id))
            await db.commit()
            return True

    async def delete_executions_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            await db.execute(delete(FlowExecution).where(FlowExecution.user_id == user_id))
            await db.commit()
            return True


FlowExecutions = FlowExecutionTable()
