# Copyright 2026 Quantova Inc
# SPDX-License-Identifier: Apache-2.0 OR MIT

import hashlib
import inspect
import json
from typing import Any, Awaitable, Callable, Optional, Union

# An anchor takes the record digests for one event and the record kind, and
# returns the receipts. It may be synchronous or return an awaitable, so a caller
# can wire it to an in process client or to a network call.
Anchor = Callable[..., Union[list, Awaitable[list]]]

# A projection chooses what of an event is committed. The default commits the
# whole canonical event payload.
Projection = Callable[[dict], Any]


def _default_projection(event: dict) -> Any:
    return event


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


class QstampEventRecorder:
    """Fingerprints an instrumentation event and anchors it as a Qstamp receipt.

    The recorder is framework free so it can be tested on its own and reused by
    the event handler. It computes a SHA3 digest of a canonical projection of the
    event and hands the digest to the supplied anchor. Only the digest leaves, so
    the event payload stays with the caller while the proof that the event
    occurred in one exact form is anchored on chain.

    Anchoring never breaks a pipeline. A failure is routed to on_error when one is
    given, and otherwise raised for the caller to decide.
    """

    def __init__(
        self,
        anchor: Anchor,
        *,
        kind: str = "0",
        alg: str = "sha3-256",
        project: Optional[Projection] = None,
        on_receipt: Optional[Callable[[Any, str], None]] = None,
        on_error: Optional[Callable[[BaseException, str], None]] = None,
    ):
        if not callable(anchor):
            raise ValueError("an anchor callable is required")
        if alg not in ("sha3-256", "sha256"):
            raise ValueError("alg must be sha3-256 or sha256")
        self._anchor = anchor
        self._kind = str(kind)
        self._alg = alg
        self._project = project or _default_projection
        self._on_receipt = on_receipt
        self._on_error = on_error

    def digest(self, event: dict) -> bytes:
        canonical = _canonical_json(self._project(event))
        data = canonical.encode("utf-8")
        if self._alg == "sha256":
            return hashlib.sha256(data).digest()
        return hashlib.sha3_256(data).digest()

    async def record(self, event: dict, name: str = "") -> Optional[Any]:
        try:
            d = self.digest(event)
            outcome = self._anchor([d], self._kind)
            if inspect.isawaitable(outcome):
                outcome = await outcome
            receipt = outcome[0] if outcome else None
            if receipt is not None and self._on_receipt is not None:
                self._on_receipt(receipt, name)
            return receipt
        except BaseException as error:  # noqa: BLE001
            if self._on_error is not None:
                self._on_error(error, name)
                return None
            raise
