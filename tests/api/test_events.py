import pytest

from app.events.base import BaseEvent
from app.events.dispatcher import EventDispatcher
from app.events.interfaces import BaseEventHandler
from app.events.registry import event_registry


class DummyEvent(BaseEvent):
    event_name: str = "DummyEvent"
    data: str


class WorkingHandler(BaseEventHandler):
    def __init__(self):
        self.called = False

    async def handle(self, event: BaseEvent) -> None:
        self.called = True


class FailingHandler(BaseEventHandler):
    def __init__(self):
        self.called = False

    async def handle(self, event: BaseEvent) -> None:
        self.called = True
        raise ValueError("Intentional Failure")


@pytest.fixture(autouse=True)
def clear_registry():
    # Clear registry before each test
    event_registry._handlers.clear()
    yield


@pytest.mark.asyncio
async def test_event_dispatch_success():
    handler = WorkingHandler()
    event_registry.register_handler("DummyEvent", handler)

    event = DummyEvent(data="test")
    await EventDispatcher.dispatch(event)

    assert handler.called is True


@pytest.mark.asyncio
async def test_event_dispatch_isolation():
    # Test that a failing handler doesn't prevent a working handler from running
    failing_handler = FailingHandler()
    working_handler = WorkingHandler()

    event_registry.register_handler("DummyEvent", failing_handler)
    event_registry.register_handler("DummyEvent", working_handler)

    event = DummyEvent(data="test isolation")
    # This should not raise an exception
    await EventDispatcher.dispatch(event)

    assert failing_handler.called is True
    assert working_handler.called is True
