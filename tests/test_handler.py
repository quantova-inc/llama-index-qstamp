# Copyright 2026 Quantova Inc
# SPDX-License-Identifier: Apache-2.0 OR MIT

import pytest

from llama_index_qstamp import QstampEventHandler, QstampEventRecorder

# These tests need llama-index-core for the event base class.
instrumentation = pytest.importorskip("llama_index.core.instrumentation.events.base")
BaseEvent = instrumentation.BaseEvent


class RetrievalEndEvent(BaseEvent):
    @classmethod
    def class_name(cls) -> str:
        return "RetrievalEndEvent"


class RetrievalStartEvent(BaseEvent):
    @classmethod
    def class_name(cls) -> str:
        return "RetrievalStartEvent"


class _Anchor:
    def __init__(self):
        self.calls = []

    def __call__(self, digests, kind):
        self.calls.append((digests, kind))
        return [{"anchor": {"tx": "0xabc"}}]


async def test_ahandle_anchors_end_events_by_default():
    anchor = _Anchor()
    handler = QstampEventHandler(recorder=QstampEventRecorder(anchor))
    await handler.ahandle(RetrievalEndEvent())
    assert len(anchor.calls) == 1


async def test_ahandle_ignores_non_end_events_by_default():
    anchor = _Anchor()
    handler = QstampEventHandler(recorder=QstampEventRecorder(anchor))
    await handler.ahandle(RetrievalStartEvent())
    assert anchor.calls == []


async def test_event_names_filter_is_respected():
    anchor = _Anchor()
    handler = QstampEventHandler(
        recorder=QstampEventRecorder(anchor),
        event_names={"RetrievalStartEvent"},
    )
    await handler.ahandle(RetrievalStartEvent())
    await handler.ahandle(RetrievalEndEvent())
    assert len(anchor.calls) == 1
