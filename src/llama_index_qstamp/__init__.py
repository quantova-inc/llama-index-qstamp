# Copyright 2026 Quantova Inc
# SPDX-License-Identifier: Apache-2.0 OR MIT

from typing import Any, Callable, Optional, Set

from ._recorder import Anchor, Projection, QstampEventRecorder
from .handler import QstampEventHandler

__all__ = [
    "Anchor",
    "Projection",
    "QstampEventRecorder",
    "QstampEventHandler",
    "install",
]


def install(
    anchor: Anchor,
    *,
    dispatcher: Any = None,
    event_names: Optional[Set[str]] = None,
    kind: str = "0",
    alg: str = "sha3-256",
    project: Optional[Projection] = None,
    on_receipt: Optional[Callable[[Any, str], None]] = None,
    on_error: Optional[Callable[[BaseException, str], None]] = None,
) -> QstampEventHandler:
    """Build a QstampEventHandler and register it on a LlamaIndex dispatcher.

    Pass the anchor that turns a list of record digests and a kind into receipts.
    With no dispatcher the handler is added to the root dispatcher, so it sees
    events from the whole process. The handler is returned so a caller can remove
    it later or inspect it.
    """
    recorder = QstampEventRecorder(
        anchor,
        kind=kind,
        alg=alg,
        project=project,
        on_receipt=on_receipt,
        on_error=on_error,
    )
    handler = QstampEventHandler(recorder=recorder, event_names=event_names)

    target = dispatcher
    if target is None:
        from llama_index.core.instrumentation import get_dispatcher

        target = get_dispatcher()
    target.add_event_handler(handler)
    return handler
