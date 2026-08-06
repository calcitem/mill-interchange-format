# MIF 1.0 interoperability harness

This directory contains a non-normative test protocol for comparing independent
MIF 1.0 implementations. It does not add a MIF wire format and is not a
conformance target.

- `adapter-protocol-v1.md` defines the NDJSON process contract and operations.
- `schema/` validates adapter messages, harness configuration and case sources.
- `cases/smoke-v1.json` is the 17-case candidate-2 cross-process smoke set,
  including a portable MIFPOS case that exposes UTF-16 key-order and binary64
  JCS differences through `documentDigest`.
- `adapters.reference-loopback.json` starts two isolated instances of the
  candidate Python reference adapter to test the harness itself.

From the repository root, verify the fixed launch package:

```text
python -B tools/verify_mif_1_0_interop.py
```

Invoke the comparator directly with a chosen adapter configuration:

```text
python -B tools/compare_mif_1_0_adapters.py \
  --config interop/adapters.reference-loopback.json \
  --cases interop/cases/smoke-v1.json
```

The loopback result proves only that the process protocol and comparator are
deterministic. Use independent Sanmill and NMM_LLM entries for
cross-implementation evidence. The current candidate-2 smoke has zero
differences across the reference, Sanmill and NMM_LLM adapters, but it remains
candidate evidence rather than MIF Suite 1.0 conformance.

Adapter authors may use the specification, schemas, registries and corpus, but
must not import or copy gameplay implementation code from `reference/`.
