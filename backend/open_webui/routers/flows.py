from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from open_webui.models.flows import (
    FlowForm,
    FlowUpdateForm,
    FlowResponse,
    FlowListResponse,
    FlowModel,
    Flows,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user

router = APIRouter()

############################
# GetFlows
############################


@router.get("/", response_model=list[FlowListResponse])
async def get_flows(user=Depends(get_verified_user)):
    """
    Get all flows for the current user
    """
    flows = Flows.get_flows_by_user_id(user.id)
    
    # Return simplified list response
    return [
        FlowListResponse(
            id=flow.id,
            name=flow.name,
            description=flow.description,
            nodes=flow.nodes,
            edges=flow.edges,
            created_at=flow.created_at,
            updated_at=flow.updated_at,
            meta=flow.meta,
        )
        for flow in flows
    ]


############################
# CreateNewFlow
############################


@router.post("/create", response_model=Optional[FlowResponse])
async def create_new_flow(
    request: Request, form_data: FlowForm, user=Depends(get_verified_user)
):
    """
    Create a new flow
    """
    try:
        flow = Flows.insert_new_flow(user.id, form_data)

        if flow:
            return FlowResponse(
                id=flow.id,
                user_id=flow.user_id,
                name=flow.name,
                description=flow.description,
                nodes=flow.nodes,
                edges=flow.edges,
                created_at=flow.created_at,
                updated_at=flow.updated_at,
                meta=flow.meta,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


############################
# GetFlowById
############################


@router.get("/{id}", response_model=Optional[FlowResponse])
async def get_flow_by_id(id: str, user=Depends(get_verified_user)):
    """
    Get a specific flow by ID
    """
    flow = Flows.get_flow_by_id(id)

    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check if user owns the flow or is admin
    if flow.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return FlowResponse(
        id=flow.id,
        user_id=flow.user_id,
        name=flow.name,
        description=flow.description,
        nodes=flow.nodes,
        edges=flow.edges,
        created_at=flow.created_at,
        updated_at=flow.updated_at,
        meta=flow.meta,
    )


############################
# UpdateFlowById
############################


@router.post("/{id}", response_model=Optional[FlowResponse])
async def update_flow_by_id(
    id: str,
    form_data: FlowUpdateForm,
    user=Depends(get_verified_user),
):
    """
    Update a flow by ID
    """
    flow = Flows.get_flow_by_id(id)
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check if user owns the flow or is admin
    if flow.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    updated_flow = Flows.update_flow_by_id(id, form_data)
    
    if updated_flow:
        return FlowResponse(
            id=updated_flow.id,
            user_id=updated_flow.user_id,
            name=updated_flow.name,
            description=updated_flow.description,
            nodes=updated_flow.nodes,
            edges=updated_flow.edges,
            created_at=updated_flow.created_at,
            updated_at=updated_flow.updated_at,
            meta=updated_flow.meta,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# DuplicateFlowById
############################


@router.post("/{id}/duplicate", response_model=Optional[FlowResponse])
async def duplicate_flow_by_id(
    id: str,
    user=Depends(get_verified_user),
):
    """
    Duplicate a flow by ID
    """
    flow = Flows.get_flow_by_id(id)
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check if user owns the flow or is admin
    if flow.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    duplicated_flow = Flows.duplicate_flow_by_id(id, user.id)
    
    if duplicated_flow:
        return FlowResponse(
            id=duplicated_flow.id,
            user_id=duplicated_flow.user_id,
            name=duplicated_flow.name,
            description=duplicated_flow.description,
            nodes=duplicated_flow.nodes,
            edges=duplicated_flow.edges,
            created_at=duplicated_flow.created_at,
            updated_at=duplicated_flow.updated_at,
            meta=duplicated_flow.meta,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# DeleteFlowById
############################


@router.delete("/{id}", response_model=bool)
async def delete_flow_by_id(id: str, user=Depends(get_verified_user)):
    """
    Delete a flow by ID
    """
    flow = Flows.get_flow_by_id(id)
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check if user owns the flow or is admin
    if flow.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Flows.delete_flow_by_id(id)
    return result


############################
# ExportFlowById
############################


@router.get("/{id}/export")
async def export_flow_by_id(id: str, user=Depends(get_verified_user)):
    """
    Export a flow as JSON
    """
    flow = Flows.get_flow_by_id(id)
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check if user owns the flow or is admin
    if flow.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return {
        "version": "1.0",
        "flow": {
            "name": flow.name,
            "description": flow.description,
            "nodes": flow.nodes,
            "edges": flow.edges,
            "meta": flow.meta,
        },
        "exportedAt": flow.updated_at,
    }


############################
# ImportFlow
############################


@router.post("/import", response_model=Optional[FlowResponse])
async def import_flow(
    request: Request,
    flow_data: dict,
    user=Depends(get_verified_user),
):
    """
    Import a flow from JSON
    """
    try:
        # Extract flow data from import format
        if "flow" in flow_data:
            flow_content = flow_data["flow"]
        else:
            flow_content = flow_data

        form_data = FlowForm(
            name=flow_content.get("name", "Imported Flow"),
            description=flow_content.get("description"),
            nodes=flow_content.get("nodes", []),
            edges=flow_content.get("edges", []),
        )

        flow = Flows.insert_new_flow(user.id, form_data)

        if flow:
            return FlowResponse(
                id=flow.id,
                user_id=flow.user_id,
                name=flow.name,
                description=flow.description,
                nodes=flow.nodes,
                edges=flow.edges,
                created_at=flow.created_at,
                updated_at=flow.updated_at,
                meta=flow.meta,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import failed: {str(e)}",
        )


############################
# ExecuteFlow (Optional - for server-side execution)
############################


@router.post("/{id}/execute")
async def execute_flow_by_id(
    id: str,
    inputs: dict,
    user=Depends(get_verified_user),
):
    """
    Execute a flow (placeholder for future server-side execution)
    Currently, flows are executed client-side
    """
    flow = Flows.get_flow_by_id(id)
    
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check if user owns the flow or is admin
    if flow.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # For now, return a message that execution happens client-side
    return {
        "message": "Flow execution is handled client-side",
        "flowId": id,
        "status": "delegated_to_client",
    }
