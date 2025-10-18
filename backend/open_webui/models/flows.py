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
# Flow DB Schema
####################

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class Flow(Base):
    __tablename__ = "flow"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    name = Column(Text)
    description = Column(Text, nullable=True)
    
    nodes = Column(JSON)
    edges = Column(JSON)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    
    meta = Column(JSON, server_default="{}")

    __table_args__ = (
        # Performance indexes for common queries
        Index("flow_user_id_idx", "user_id"),
        Index("flow_updated_at_idx", "updated_at"),
        Index("flow_user_id_updated_at_idx", "user_id", "updated_at"),
    )


class FlowModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    
    nodes: list
    edges: list
    
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    
    meta: dict = {}


####################
# Forms
####################


class FlowForm(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: list
    edges: list


class FlowUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[list] = None
    edges: Optional[list] = None


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


class FlowListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    nodes: list
    edges: list
    created_at: int
    updated_at: int
    meta: dict = {}


class FlowTable:
    def insert_new_flow(
        self, user_id: str, form_data: FlowForm
    ) -> Optional[FlowModel]:
        with get_db() as db:
            id = str(uuid.uuid4())
            
            flow = FlowModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "name": form_data.name,
                    "description": form_data.description,
                    "nodes": form_data.nodes,
                    "edges": form_data.edges,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "meta": {},
                }
            )

            result = Flow(**flow.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return FlowModel.model_validate(result) if result else None

    def get_flows(self) -> list[FlowModel]:
        with get_db() as db:
            flows = db.query(Flow).order_by(Flow.updated_at.desc()).all()
            return [FlowModel.model_validate(flow) for flow in flows]

    def get_flows_by_user_id(self, user_id: str) -> list[FlowModel]:
        with get_db() as db:
            flows = (
                db.query(Flow)
                .filter(Flow.user_id == user_id)
                .order_by(Flow.updated_at.desc())
                .all()
            )
            return [FlowModel.model_validate(flow) for flow in flows]

    def get_flow_by_id(self, id: str) -> Optional[FlowModel]:
        with get_db() as db:
            flow = db.query(Flow).filter(Flow.id == id).first()
            return FlowModel.model_validate(flow) if flow else None

    def get_flow_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[FlowModel]:
        with get_db() as db:
            flow = (
                db.query(Flow)
                .filter(Flow.id == id, Flow.user_id == user_id)
                .first()
            )
            return FlowModel.model_validate(flow) if flow else None

    def update_flow_by_id(
        self, id: str, form_data: FlowUpdateForm
    ) -> Optional[FlowModel]:
        with get_db() as db:
            flow = db.query(Flow).filter(Flow.id == id).first()
            
            if not flow:
                return None

            # Update fields if provided
            if form_data.name is not None:
                flow.name = form_data.name
            if form_data.description is not None:
                flow.description = form_data.description
            if form_data.nodes is not None:
                flow.nodes = form_data.nodes
            if form_data.edges is not None:
                flow.edges = form_data.edges
                
            flow.updated_at = int(time.time())

            db.commit()
            db.refresh(flow)
            return FlowModel.model_validate(flow)

    def duplicate_flow_by_id(
        self, id: str, user_id: str, name: Optional[str] = None
    ) -> Optional[FlowModel]:
        with get_db() as db:
            original_flow = db.query(Flow).filter(Flow.id == id).first()
            
            if not original_flow:
                return None

            new_id = str(uuid.uuid4())
            new_name = name if name else f"{original_flow.name} (Copy)"
            
            new_flow = FlowModel(
                **{
                    "id": new_id,
                    "user_id": user_id,
                    "name": new_name,
                    "description": original_flow.description,
                    "nodes": original_flow.nodes,
                    "edges": original_flow.edges,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "meta": original_flow.meta,
                }
            )

            result = Flow(**new_flow.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return FlowModel.model_validate(result) if result else None

    def delete_flow_by_id(self, id: str) -> bool:
        with get_db() as db:
            flow = db.query(Flow).filter(Flow.id == id).first()
            
            if not flow:
                return False

            db.delete(flow)
            db.commit()
            return True

    def delete_flows_by_user_id(self, user_id: str) -> bool:
        with get_db() as db:
            db.query(Flow).filter(Flow.user_id == user_id).delete()
            db.commit()
            return True


Flows = FlowTable()
