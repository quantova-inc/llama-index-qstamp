# Copyright 2026 Quantova Inc
# SPDX-License-Identifier: Apache-2.0 OR MIT

import hashlib
import json

import pytest

from llama_index_qstamp import QstampEventRecorder


def _fake_receipt():
    return {"anchor": {"tx": "0xabc", "height": 7}}


class RecordingAnchor:
    def __init__(self):
        self.calls = []

    def __call__(self, digests, kind):
        self.calls.append((digests, kind))
        return [_fake_receipt()]


async def test_record_anchors_once_and_returns_receipt():
    anchor = RecordingAnchor()
    rec = QstampEventRecorder(anchor, kind="1201")
    receipt = await rec.record({"class_name": "RetrievalEndEvent", "id_": "x"})
    assert receipt == _fake_receipt()
    assert len(anchor.calls) == 1
    digests, kind = anchor.calls[0]
    assert kind == "1201"
    assert isinstance(digests[0], bytes)


async def test_digest_matches_canonical_sha3():
    anchor = RecordingAnchor()
    rec = QstampEventRecorder(anchor)
    event = {"b": 2, "a": 1}
    canonical = json.dumps({"a": 1, "b": 2}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert rec.digest(event) == hashlib.sha3_256(canonical.encode("utf-8")).digest()


async def test_projection_controls_the_commitment():
    anchor = RecordingAnchor()
    rec = QstampEventRecorder(anchor, project=lambda e: {"only": e["class_name"]})
    await rec.record({"class_name": "LLMChatEndEvent", "payload": "secret"})
    canonical = json.dumps({"only": "LLMChatEndEvent"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert anchor.calls[0][0][0] == hashlib.sha3_256(canonical.encode("utf-8")).digest()


async def test_async_anchor_is_awaited():
    async def anchor(digests, kind):
        return [_fake_receipt()]

    rec = QstampEventRecorder(anchor)
    assert await rec.record({"class_name": "QueryEndEvent"}) == _fake_receipt()


async def test_on_error_catches_failure_and_does_not_raise():
    seen = []

    def anchor(digests, kind):
        raise RuntimeError("rpc down")

    rec = QstampEventRecorder(anchor, on_error=lambda e, name: seen.append((str(e), name)))
    assert await rec.record({"class_name": "RetrievalEndEvent"}, "RetrievalEndEvent") is None
    assert seen and "rpc down" in seen[0][0]


async def test_failure_raises_when_no_on_error():
    def anchor(digests, kind):
        raise RuntimeError("rpc down")

    rec = QstampEventRecorder(anchor)
    with pytest.raises(RuntimeError):
        await rec.record({"class_name": "RetrievalEndEvent"})


def test_invalid_alg_and_anchor_rejected():
    with pytest.raises(ValueError):
        QstampEventRecorder(lambda d, k: [], alg="md5")
    with pytest.raises(ValueError):
        QstampEventRecorder(None)
