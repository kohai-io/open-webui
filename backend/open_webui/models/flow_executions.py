import logging
import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Index
from sqlalchemy import or_, func, select

####################
# FlowExecution DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class FlowExecution(Base):
    __tablename__ = "flow_execution"

    id = Column(String, primary_key=True)
    flow_id = Column(String)
    user_id = Column(String)
    
    status = Column(String)  # success, error, aborted
    inputs = Column(JSON, nullable=True)
    outputs = Column(JSON, nullable=True)
    node_results = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    
    execution_time = Column(BigInteger)  # milliseconds
    created_at = Column(BigInteger)
    
    meta = Column(JSON, server_default="{}")

    __table_args__ = (
        # Performance indexes for common queries
        Index("flow_execution_flow_id_created_at_idx", "flow_id", "created_at"),
        Index("flow_execution_user_id_created_at_idx", "user_id", "created_at"),
        Index("flow_execution_flow_id_status_idx", "flow_id", "status"),
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
    
    execution_time: int  # milliseconds
    created_at: int  # timestamp in epoch
    
    meta: dict = {}


####################
# Forms
####################


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
    def insert_new_execution(
        self, user_id: str, form_data: FlowExecutionForm
    ) -> Optional[FlowExecutionModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            
            execution = FlowExecutionModel(
                **{
                    "id": id,
                    "flow_id": form_data.flow_id,
                    "user_id": user_id,
                    "status": form_data.status,
                    "inputs": form_data.inputs,
                    "outputs": form_data.outputs,
                    "node_results": form_data.node_results,
                    "errors": form_data.errors,
                    "execution_time": form_data.execution_time,
                    "created_at": int(time.time()),
                    "meta": {},
                }
            )

            result = FlowExecution(**execution.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return FlowExecutionModel.model_validate(result) if result else None

    def get_executions_by_flow_id(
        self, flow_id: str, skip: int = 0, limit: int = 60
    ) -> list[FlowExecutionModel]:
        with get_db() as db:
            executions = (
                db.query(FlowExecution)
                .filter(FlowExecution.flow_id == flow_id)
                .order_by(FlowExecution.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [FlowExecutionModel.model_validate(execution) for execution in executions]

    def get_executions_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 60
    ) -> list[FlowExecutionModel]:
        with get_db() as db:
            executions = (
                db.query(FlowExecution)
                .filter(FlowExecution.user_id == user_id)
                .order_by(FlowExecution.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [FlowExecutionModel.model_validate(execution) for execution in executions]

    def get_execution_by_id(self, id: str) -> Optional[FlowExecutionModel]:
        with get_db() as db:
            execution = db.query(FlowExecution).filter(FlowExecution.id == id).first()
            return FlowExecutionModel.model_validate(execution) if execution else None

    def get_execution_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[FlowExecutionModel]:
        with get_db() as db:
            execution = (
                db.query(FlowExecution)
                .filter(FlowExecution.id == id, FlowExecution.user_id == user_id)
                .first()
            )
            return FlowExecutionModel.model_validate(execution) if execution else None

    def get_execution_stats_by_flow_id(
        self, flow_id: str
    ) -> FlowExecutionStatsResponse:
        with get_db() as db:
            total = (
                db.query(func.count(FlowExecution.id))
                .filter(FlowExecution.flow_id == flow_id)
                .scalar()
            )
            
            success_count = (
                db.query(func.count(FlowExecution.id))
                .filter(FlowExecution.flow_id == flow_id, FlowExecution.status == "success")
                .scalar()
            )
            
            error_count = (
                db.query(func.count(FlowExecution.id))
                .filter(FlowExecution.flow_id == flow_id, FlowExecution.status == "error")
                .scalar()
            )
            
            aborted_count = (
                db.query(func.count(FlowExecution.id))
                .filter(FlowExecution.flow_id == flow_id, FlowExecution.status == "aborted")
                .scalar()
            )
            
            avg_time = (
                db.query(func.avg(FlowExecution.execution_time))
                .filter(FlowExecution.flow_id == flow_id)
                .scalar()
            ) or 0.0
            
            last_execution = (
                db.query(FlowExecution)
                .filter(FlowExecution.flow_id == flow_id)
                .order_by(FlowExecution.created_at.desc())
                .first()
            )
            
            return FlowExecutionStatsResponse(
                total_executions=total or 0,
                success_count=success_count or 0,
                error_count=error_count or 0,
                aborted_count=aborted_count or 0,
                avg_execution_time=float(avg_time),
                last_execution_at=last_execution.created_at if last_execution else None
            )

    def delete_execution_by_id(self, id: str) -> bool:
        with get_db() as db:
            execution = db.query(FlowExecution).filter(FlowExecution.id == id).first()
            
            if not execution:
                return False

            db.delete(execution)
            db.commit()
            return True

    def delete_executions_by_flow_id(self, flow_id: str) -> bool:
        with get_db() as db:
            db.query(FlowExecution).filter(FlowExecution.flow_id == flow_id).delete()
            db.commit()
            return True

    def delete_executions_by_user_id(self, user_id: str) -> bool:
        with get_db() as db:
            db.query(FlowExecution).filter(FlowExecution.user_id == user_id).delete()
            db.commit()
            return True

    def delete_old_executions_by_flow_id(
        self, flow_id: str, keep_count: int = 50
    ) -> bool:
        """Keep only the most recent N executions for a flow"""
        with get_db() as db:
            # Get the timestamp of the Nth most recent execution
            subquery = (
                db.query(FlowExecution.created_at)
                .filter(FlowExecution.flow_id == flow_id)
                .order_by(FlowExecution.created_at.desc())
                .offset(keep_count)
                .limit(1)
                .scalar()
            )
            
            if subquery:
                # Delete all executions older than that timestamp
                db.query(FlowExecution).filter(
                    FlowExecution.flow_id == flow_id,
                    FlowExecution.created_at < subquery
                ).delete()
                db.commit()
            
            return True


FlowExecutions = FlowExecutionTable()
