import logging
import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import Users, UserResponse
from open_webui.models.groups import Groups
from open_webui.utils.access_control import has_access

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

    access_control = Column(JSON, nullable=True)  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }

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
    access_control: Optional[dict] = None


####################
# Forms
####################


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
    """Flow model with user information for list responses"""
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
                    "access_control": form_data.access_control,
                }
            )

            result = Flow(**flow.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return FlowModel.model_validate(result) if result else None

    def get_flows(self) -> list[FlowUserResponse]:
        """Get all flows with user information"""
        with get_db() as db:
            all_flows = db.query(Flow).order_by(Flow.updated_at.desc()).all()

            user_ids = list(set(flow.user_id for flow in all_flows))
            users = Users.get_users_by_user_ids(user_ids) if user_ids else []
            users_dict = {user.id: user for user in users}

            flows = []
            for flow in all_flows:
                user = users_dict.get(flow.user_id)
                flows.append(
                    FlowUserResponse.model_validate(
                        {
                            **FlowModel.model_validate(flow).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return flows

    def get_flows_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[FlowUserResponse]:
        """
        Get flows accessible by user based on permission level.
        Returns flows the user owns OR has access to via access_control.
        """
        flows = self.get_flows()
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user_id)}

        return [
            flow
            for flow in flows
            if flow.user_id == user_id
            or has_access(user_id, permission, flow.access_control, user_group_ids)
        ]

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
            if form_data.access_control is not None:
                flow.access_control = form_data.access_control
                
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
                    "access_control": None,  # Duplicated flows start as private
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
