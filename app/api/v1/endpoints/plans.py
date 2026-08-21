import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanResponse, PlanUpdate
from app.schemas.responses import ApiResponse
from app.services.plan import plan_service


router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[list[PlanResponse]],
)
async def get_plans(
    active_only: bool = Query(
        True,
        description="Return only active plans",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    plans = await plan_service.get_plans(
        db,
        skip=skip,
        limit=limit,
        active_only=active_only,
    )

    return ApiResponse(
        success=True,
        message="Plans retrieved successfully",
        data=[PlanResponse.model_validate(plan) for plan in plans],
    )


@router.get(
    "/{plan_id}",
    response_model=ApiResponse[PlanResponse],
)
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    plan = await plan_service.get_plan(
        db,
        plan_id,
    )

    return ApiResponse(
        success=True,
        message="Plan retrieved successfully",
        data=PlanResponse.model_validate(plan),
    )


@router.post(
    "",
    response_model=ApiResponse[PlanResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_plan(
    data: PlanCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    plan = await plan_service.create_plan(
        db,
        data,
    )

    await db.commit()
    await db.refresh(plan)

    return ApiResponse(
        success=True,
        message="Plan created successfully",
        data=PlanResponse.model_validate(plan),
    )


@router.patch(
    "/{plan_id}",
    response_model=ApiResponse[PlanResponse],
)
async def update_plan(
    plan_id: uuid.UUID,
    data: PlanUpdate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    plan = await plan_service.get_plan(
        db,
        plan_id,
    )

    updated_plan = await plan_service.update_plan(
        db,
        plan,
        data,
    )

    await db.commit()
    await db.refresh(updated_plan)

    return ApiResponse(
        success=True,
        message="Plan updated successfully",
        data=PlanResponse.model_validate(updated_plan),
    )


@router.delete(
    "/{plan_id}",
    response_model=ApiResponse[None],
)
async def delete_plan(
    plan_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    plan = await plan_service.get_plan(
        db,
        plan_id,
    )

    await plan_service.delete_plan(
        db,
        plan,
    )

    await db.commit()

    return ApiResponse(
        success=True,
        message="Plan deactivated successfully",
        data=None,
    )
