import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.repositories.plan import plan_repo
from app.schemas.plan import PlanCreate, PlanUpdate


class PlanService:
    @staticmethod
    async def get_plans(
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> list[Plan]:
        filters = {}

        if active_only:
            filters["is_active"] = True

        plans = await plan_repo.get_all(
            db,
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by="monthly_price",
            sort_desc=False,
        )

        return list(plans)

    @staticmethod
    async def get_plan(
        db: AsyncSession,
        plan_id: uuid.UUID,
    ) -> Plan:
        plan = await plan_repo.get_by_id(db, plan_id)

        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )

        return plan

    @staticmethod
    async def create_plan(
        db: AsyncSession,
        data: PlanCreate,
    ) -> Plan:
        existing_name = await plan_repo.get_by_slug(db, data.slug)

        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan slug already exists.",
            )

        existing_plans = await plan_repo.get_all(
            db,
            filters={"name": data.name},
            limit=1,
        )

        if existing_plans:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan name already exists.",
            )

        plan = await plan_repo.create(
            db,
            obj_in=data.model_dump(),
        )

        return plan

    @staticmethod
    async def update_plan(
        db: AsyncSession,
        plan: Plan,
        data: PlanUpdate,
    ) -> Plan:
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return plan

        if "slug" in update_data and update_data["slug"] != plan.slug:
            existing = await plan_repo.get_by_slug(
                db,
                update_data["slug"],
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Plan slug already exists.",
                )

        if "name" in update_data and update_data["name"] != plan.name:
            existing_plans = await plan_repo.get_all(
                db,
                filters={"name": update_data["name"]},
                limit=1,
            )

            if existing_plans:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Plan name already exists.",
                )

        updated_plan = await plan_repo.update(
            db,
            db_obj=plan,
            obj_in=update_data,
        )

        return updated_plan

    @staticmethod
    async def delete_plan(
        db: AsyncSession,
        plan: Plan,
    ) -> None:
        # Plans do not have deleted_at, so we deactivate them
        # instead of physically deleting them.
        if not plan.is_active:
            return

        await plan_repo.update(
            db,
            db_obj=plan,
            obj_in={"is_active": False},
        )


plan_service = PlanService()
