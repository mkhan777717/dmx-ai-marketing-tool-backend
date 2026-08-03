import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import SnapshotType
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.repositories.analytics import analytics_snapshot_repo
from app.services.analytics.dashboard import DashboardService


class AnalyticsService:
    @staticmethod
    async def generate_snapshot(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        snapshot_date: date,
        snapshot_type: SnapshotType,
    ) -> AnalyticsSnapshot:
        """
        Generates a new snapshot for a given workspace by orchestrating the sub-services.
        If a snapshot for the same date and type already exists, it updates it.
        """
        dashboard_data = await DashboardService.get_dashboard_overview(db, workspace_id)

        existing = await analytics_snapshot_repo.get_by_date_and_type(
            db, workspace_id, snapshot_date, snapshot_type
        )

        obj_in = {
            "workspace_id": workspace_id,
            "snapshot_type": snapshot_type,
            "snapshot_date": snapshot_date,
            "campaign_metrics": dashboard_data["campaign_metrics"],
            "ai_metrics": dashboard_data["ai_metrics"],
            "publishing_metrics": dashboard_data["publishing_metrics"],
            "workspace_metrics": dashboard_data["workspace_metrics"],
        }

        if existing:
            return await analytics_snapshot_repo.update(
                db, db_obj=existing, obj_in=obj_in
            )
        else:
            return await analytics_snapshot_repo.create(db, obj_in=obj_in)

    @staticmethod
    async def get_latest_snapshot(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        snapshot_type: SnapshotType = SnapshotType.DAILY,
    ) -> AnalyticsSnapshot:
        """
        Fetches the latest snapshot or generates a new one for today if none exists.
        """
        snapshot = await analytics_snapshot_repo.get_latest_snapshot(
            db, workspace_id, snapshot_type
        )
        if not snapshot or snapshot.snapshot_date != date.today():
            snapshot = await AnalyticsService.generate_snapshot(
                db, workspace_id, date.today(), snapshot_type
            )
        return snapshot
