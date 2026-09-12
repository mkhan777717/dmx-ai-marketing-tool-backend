import uuid
from unittest.mock import patch

import pytest

from app.jobs.adapters.celery import CeleryAdapter
from app.jobs.queue import QueueService
from app.jobs.worker import WorkerBase


# A simple task for testing
async def dummy_task(job_execution_id: str, should_fail: bool = False) -> dict:
    if should_fail:
        raise ValueError("Task intentionally failed")
    return {"status": "success", "processed": True}


@pytest.fixture
def test_job_payload():
    return {"should_fail": False}


@pytest.mark.asyncio
async def test_worker_success(test_job_payload):
    with (
        patch("app.jobs.worker.JobExecutionService.mark_started") as mock_start,
        patch("app.jobs.worker.JobExecutionService.mark_completed") as mock_complete,
    ):

        class MockJob:
            id = uuid.uuid4()
            job_name = "test_job"

        mock_start.return_value = MockJob()

        job_id = str(uuid.uuid4())
        result = await WorkerBase.execute_job(
            job_id, dummy_task, job_execution_id=job_id, should_fail=False
        )

        assert result["status"] == "success"
        mock_start.assert_called_once()
        mock_complete.assert_called_once()


@pytest.mark.asyncio
async def test_worker_failure(test_job_payload):
    with (
        patch("app.jobs.worker.JobExecutionService.mark_started") as mock_start,
        patch("app.jobs.worker.JobExecutionService.mark_failed") as mock_fail,
    ):

        class MockJob:
            id = uuid.uuid4()
            job_name = "test_job"

        mock_start.return_value = MockJob()

        job_id = str(uuid.uuid4())

        from app.jobs.exceptions import JobExecutionError

        with pytest.raises(JobExecutionError):
            await WorkerBase.execute_job(
                job_id, dummy_task, job_execution_id=job_id, should_fail=True
            )

        mock_start.assert_called_once()
        mock_fail.assert_called_once()


@pytest.mark.asyncio
async def test_queue_service_enqueue():
    # Test that QueueService correctly serializes and uses the adapter
    adapter = CeleryAdapter()
    service = QueueService(adapter)

    with (
        patch("app.jobs.queue.JobExecutionService.create_job") as mock_create,
        patch.object(adapter, "enqueue") as mock_enqueue,
    ):

        class MockJob:
            id = uuid.uuid4()

        mock_job = MockJob()
        mock_create.return_value = mock_job
        mock_enqueue.return_value = "celery-id-123"

        job_id = await service.enqueue(job_name="test.job", payload={"data": "value"})

        assert job_id == mock_job.id
        mock_enqueue.assert_called_once()
        # Ensure job_execution_id was injected into the payload
        call_args = mock_enqueue.call_args[1]
        assert call_args["payload"]["job_execution_id"] == str(mock_job.id)


@pytest.mark.asyncio
async def test_list_admin_jobs_endpoint():
    from datetime import datetime, timezone

    from httpx import ASGITransport, AsyncClient

    from app.constants.enums import JobPriority, JobStatus
    from app.jobs.models import JobExecution
    from app.main import app

    mock_job = JobExecution(
        id=uuid.uuid4(),
        job_name="integration.sync",
        queue="default",
        status=JobStatus.QUEUED,
        priority=JobPriority.HIGH,
        attempts=0,
        max_attempts=3,
        payload={"provider": "whatsapp", "sync_type": "full"},
        result=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        failed_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.operations.admin.service.AdminOperationsService.get_system_jobs"
    ) as mock_get_jobs:
        mock_get_jobs.return_value = [mock_job]

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            res = await client.get("/admin/jobs?limit=50&offset=0")
            assert res.status_code == 200
            data = res.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["id"] == str(mock_job.id)
            assert data[0]["job_name"] == "integration.sync"
            assert data[0]["status"] == "QUEUED"
            assert data[0]["payload"]["provider"] == "whatsapp"
