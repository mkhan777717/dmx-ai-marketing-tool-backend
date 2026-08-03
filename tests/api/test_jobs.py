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
