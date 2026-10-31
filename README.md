# llama-index-qstamp

Post quantum on chain provenance for LlamaIndex pipeline and agent events.

This package registers a LlamaIndex event handler that anchors instrumentation events into a Qstamp receipt any party can verify. It hashes a canonical form of each event locally with SHA3-256, hands only the digest to an anchor you supply, and the anchor returns a receipt. The event payload never leaves the process. What leaves is a commitment that the event happened in one exact form at a point in time, anchored on the Quantova network and verifiable offline with no account and no key.

By default it anchors the completion events, the ones whose class name ends in EndEvent, so a finished retrieval, rerank, synthesis, query, or model call each leave a receipt.

## Why

A production RAG or agent pipeline leaves no durable evidence of which retriever ran, what was ranked, or what the model produced. A local log can be edited after the fact. Qstamp turns each instrumentation event into a tamper evident receipt a third party can check without trusting the operator and without seeing the underlying prompt, documents, or output.

## Install

```bash
pip install llama-index-qstamp
```

## Use

You supply an `anchor`. It takes a list of record digests and a kind, and returns the receipts. Wire it to your Qstamp client or to a network call.

```python
from llama_index_qstamp import install

def anchor(digests, kind):
    # hand the digests to your Qstamp signer or RPC and return the receipts
    return my_qstamp_client.stamp(digests, kind=kind)

install(
    anchor,
    kind="0",
    on_receipt=lambda receipt, name: print("anchored", name, receipt["anchor"]["tx"]),
)

# Build and run your pipeline as usual. Completed events are now anchored.
```

The anchor may be synchronous or asynchronous. In a synchronous handler an asynchronous anchor is scheduled on the running loop so the pipeline is never blocked.

## Choosing what is anchored

- `event_names` restricts anchoring to a set of event class names, for example `{"RetrievalEndEvent", "LLMChatEndEvent"}`. With no set the default is every event whose class name ends in EndEvent.
- `project` maps the event payload to the value that gets digested, for redaction or for a narrower claim. The default commits the whole canonical event.
- `kind` sets the Qstamp record kind.
- `alg` is `sha3-256` by default or `sha256`.
- `on_receipt` is called with the receipt and the event name once an event is anchored.
- `on_error` is called when anchoring fails, so the failure stays observable without breaking the pipeline.

## Verify a receipt

A receipt can be checked by any party with the pure verifiers, with no account and no key.

- JavaScript and TypeScript, `@quantovainc/qstamp`
- Go, `github.com/quantova-inc/qstamp-go`
- Python, the `qstamp` verifier package

## License

Apache-2.0 OR MIT.
