from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_async_session
from open_webui.models.flow_executions import (
    FlowExecutionForm,
    FlowExecutionListResponse,
    FlowExecutionResponse,
    FlowExecutionStatsResponse,
    FlowExecutions,
)
from open_webui.models.flows import (
    FlowForm,
    FlowListResponse,
    FlowModel,
    FlowResponse,
    FlowUpdateForm,
    Flows,
)
from open_webui.models.groups import Groups
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_verified_user

router = APIRouter()


class FlowDuplicateForm(BaseModel):
    name: Optional[str] = None


def _legacy_access_grants(access_control: Optional[dict], permission: str) -> tuple[set[str], set[str], bool]:
    if access_control is None:
        return set(), {'*'}, True
    if not access_control:
        return set(), set(), False

    permission_data = access_control.get(permission, {}) if isinstance(access_control, dict) else {}
    group_ids = set(permission_data.get('group_ids') or [])
    user_ids = set(permission_data.get('user_ids') or [])
    return group_ids, user_ids, '*' in user_ids


async def has_flow_access(
    user_id: str,
    user_role: str,
    flow: FlowModel,
    permission: str = 'read',
    db: Optional[AsyncSession] = None,
) -> bool:
    if user_role == 'admin':
        return True
    if flow.user_id == user_id:
        return True

    group_ids, user_ids, is_public = _legacy_access_grants(flow.access_control, permission)
    if is_public or user_id in user_ids:
        return True
    if not group_ids:
        return False

    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user_id, db=db)}
    return bool(group_ids.intersection(user_group_ids))


def flow_to_response(flow: FlowModel) -> FlowResponse:
    return FlowResponse(**flow.model_dump())


def flow_to_list_response(flow: FlowModel) -> FlowListResponse:
    return FlowListResponse(**flow.model_dump(exclude={'user_id', 'user'}))


def execution_to_response(execution) -> FlowExecutionResponse:
    return FlowExecutionResponse(**execution.model_dump())


@router.get('/', response_model=list[FlowListResponse])
async def get_flows(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'workspace.flows', request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)

    flows = await Flows.get_flows(db=db)
    accessible = [flow for flow in flows if await has_flow_access(user.id, user.role, flow, 'write', db=db)]
    return [flow_to_list_response(flow) for flow in accessible]


@router.get('/accessible', response_model=list[FlowListResponse])
async def get_accessible_flows(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'workspace.flows', request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)

    flows = await Flows.get_flows(db=db)
    accessible = [flow for flow in flows if await has_flow_access(user.id, user.role, flow, 'read', db=db)]
    return [flow_to_list_response(flow) for flow in accessible]


@router.post('/create', response_model=Optional[FlowResponse])
async def create_new_flow(
    request: Request,
    form_data: FlowForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'workspace.flows', request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)

    flow = await Flows.insert_new_flow(user.id, form_data, db=db)
    if flow:
        return flow_to_response(flow)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.get('/{id}', response_model=Optional[FlowResponse])
async def get_flow_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    flow = await Flows.get_flow_by_id(id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'read', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    return flow_to_response(flow)


@router.post('/{id}', response_model=Optional[FlowResponse])
async def update_flow_by_id(
    id: str,
    form_data: FlowUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    flow = await Flows.get_flow_by_id(id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'write', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    updated_flow = await Flows.update_flow_by_id(id, form_data, db=db)
    if updated_flow:
        return flow_to_response(updated_flow)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.post('/{id}/duplicate', response_model=Optional[FlowResponse])
async def duplicate_flow_by_id(
    id: str,
    form_data: FlowDuplicateForm = FlowDuplicateForm(),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    flow = await Flows.get_flow_by_id(id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'read', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    duplicated_flow = await Flows.duplicate_flow_by_id(id, user.id, form_data.name, db=db)
    if duplicated_flow:
        return flow_to_response(duplicated_flow)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.delete('/{id}', response_model=bool)
async def delete_flow_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    flow = await Flows.get_flow_by_id(id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if user.role != 'admin' and flow.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    await FlowExecutions.delete_executions_by_flow_id(id, db=db)
    return await Flows.delete_flow_by_id(id, db=db)


@router.post('/{id}/execute')
async def execute_flow(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    flow = await Flows.get_flow_by_id(id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'read', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    return {'message': 'Flow execution is handled client-side', 'flowId': id, 'status': 'delegated_to_client'}


@router.post('/{flow_id}/executions', response_model=Optional[FlowExecutionResponse])
async def create_flow_execution(
    flow_id: str,
    form_data: FlowExecutionForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    flow = await Flows.get_flow_by_id(flow_id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if form_data.flow_id != flow_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT('flow_id mismatch'))
    if not await has_flow_access(user.id, user.role, flow, 'read', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    execution = await FlowExecutions.insert_new_execution(user.id, form_data, db=db)
    if execution:
        return execution_to_response(execution)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.get('/{flow_id}/executions', response_model=list[FlowExecutionListResponse])
async def get_flow_executions(
    flow_id: str,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    flow = await Flows.get_flow_by_id(flow_id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'read', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    limit = 60
    skip = (max(page or 1, 1) - 1) * limit
    executions = await FlowExecutions.get_executions_by_flow_id(flow_id, skip=skip, limit=limit, db=db)
    return [FlowExecutionListResponse(**execution.model_dump()) for execution in executions]


@router.get('/{flow_id}/executions/stats', response_model=FlowExecutionStatsResponse)
async def get_flow_execution_stats(
    flow_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    flow = await Flows.get_flow_by_id(flow_id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'read', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    return await FlowExecutions.get_execution_stats_by_flow_id(flow_id, db=db)


@router.get('/{flow_id}/executions/{execution_id}', response_model=Optional[FlowExecutionResponse])
async def get_flow_execution_by_id(
    flow_id: str,
    execution_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    flow = await Flows.get_flow_by_id(flow_id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'read', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    execution = await FlowExecutions.get_execution_by_id(execution_id, db=db)
    if not execution or execution.flow_id != flow_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Execution not found')
    return execution_to_response(execution)


@router.delete('/{flow_id}/executions/{execution_id}', response_model=bool)
async def delete_flow_execution(
    flow_id: str,
    execution_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    flow = await Flows.get_flow_by_id(flow_id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'write', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    execution = await FlowExecutions.get_execution_by_id(execution_id, db=db)
    if not execution or execution.flow_id != flow_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Execution not found')
    return await FlowExecutions.delete_execution_by_id(execution_id, db=db)


@router.delete('/{flow_id}/executions', response_model=bool)
async def delete_all_flow_executions(
    flow_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    flow = await Flows.get_flow_by_id(flow_id, db=db)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not await has_flow_access(user.id, user.role, flow, 'write', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    return await FlowExecutions.delete_executions_by_flow_id(flow_id, db=db)
