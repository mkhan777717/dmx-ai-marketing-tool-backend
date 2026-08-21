from unittest.mock import patch, MagicMock

import pytest

from app.jobs.adapters.celery import CeleryAdapter


@pytest.mark.asyncio
async def test_celery_adapter_enqueue():
    adapter = CeleryAdapter()

    with patch("app.jobs.adapters.celery.celery_app.send_task") as mock_send_task:
        mock_result = MagicMock()
        mock_result.id = "fake-broker-id"
        mock_send_task.return_value = mock_result

        job_name = "test.job"
        payload = {"data": "value"}
        queue = "default"
        countdown = 10

        task_id = await adapter.enqueue(
            job_name=job_name,
            payload=payload,
            queue=queue,
            countdown=countdown,
        )

        assert task_id == "fake-broker-id"
        mock_send_task.assert_called_once_with(
            job_name,
            kwargs=payload,
            queue=queue,
            countdown=countdown,
        )


@pytest.mark.asyncio
async def test_celery_adapter_revoke():
    adapter = CeleryAdapter()

    with patch("app.jobs.adapters.celery.celery_app.control.revoke") as mock_revoke:
        broker_task_id = "fake-broker-id"

        result = await adapter.revoke(broker_task_id=broker_task_id)

        assert result is True
        mock_revoke.assert_called_once_with(
            broker_task_id,
            terminate=True,
        )
