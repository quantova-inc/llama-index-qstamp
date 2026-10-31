# Copyright 2026 Quantova Inc
# SPDX-License-Identifier: Apache-2.0 OR MIT

import asyncio
from typing import Any, Optional, Set

from llama_index.core.instrumentation.event_handlers.base import BaseEventHandler
from llama_index.core.instrumentation.events.base import BaseEvent

from ._recorder import QstampEventRecorder

# Live references to scheduled anchoring tasks, so a fire and forget task started
# from a synchronous handler is not garbage collected before it finishes.
_BACKGROUND_TASKS: Set[asyncio.Task] = set()


def _run_detached(coro) -> None:
    """Drive a coroutine to completion without blocking or raising.

    When a loop is already running the anchor is scheduled on it, so the pipeline
    is never blocked. Otherwise the coroutine is run to completion. Any error that
    the recorder did not already route to on_error is swallowed here, because an
    audit layer must never break the pipeline it observes.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        task = loop.create_task(coro)
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(lambda t: (_BACKGROUND_TASKS.discard(t), t.cancelled() or t.exception()))
        return

    try:
        asyncio.run(coro)
    except BaseException:  # noqa: BLE001
        pass


class QstampEventHandler(BaseEventHandler):
    """A LlamaIndex event handler that anchors instrumentation events on chain.

    It watches the dispatcher for the events named in event_names, fingerprints
    each one through the recorder, and anchors only the digest. The event payload
    stays in the process. By default it anchors the completion events, the ones
    whose class name ends in EndEvent, which mark a finished retrieval, rerank,
    synthesis, query, or model call.

    Anchoring never breaks a pipeline. A failure is routed to the recorder
    on_error callback when one is given and is otherwise swallowed.
    """

    recorder: QstampEventRecorder
    event_names: Optional[Set[str]] = None

    @classmethod
    def class_name(cls) -> str:
        return "QstampEventHandler"

    def _should_anchor(self, event: BaseEvent) -> bool:
        name = event.class_name()
        if self.event_names is not None:
            return name in self.event_names
        return name.endswith("EndEvent")

    def _payload(self, event: BaseEvent) -> dict:
        return event.model_dump(mode="json")

    def handle(self, event: BaseEvent, **kwargs: Any) -> Any:
        if not self._should_anchor(event):
            return None
        _run_detached(self.recorder.record(self._payload(event), event.class_name()))
        return None

    async def ahandle(self, event: BaseEvent, **kwargs: Any) -> Any:
        if not self._should_anchor(event):
            return None
        await self.recorder.record(self._payload(event), event.class_name())
        return None
