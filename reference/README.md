# MIF 1.0 candidate Python reference runner

This package is an executable reading of the frozen MIF 1.0 Candidate Wire
Contract. It implements the finite-rules state machine, MSTATE replay,
claim/repetition processing, decision and resumption identities, full-state D4
coordinate transforms, invariance gating, logical-turn projection, the
non-normative `legal-actions-v1` comparison projection and extension-free
`structural-d4-v1` MPK canonicalization for its declared rulesets.

Canonical JSON and digest inputs use the shared dependency-free RFC 8785
implementation in `jcs.py`. The candidate-3 runner retains the executable
corpus's 24
finite Appendix B number samples, UTF-16 member ordering, invalid I-JSON
rejection and the MRS annotation/document-identity boundary.

Run the repository corpus from the repository root:

```text
python -B tools/run_mif_1_0_reference.py
```

Replay one portable MSTATE document:

```text
python -B tools/run_mif_1_0_reference.py replay path/to/state.json
```

For a reference-mode MSTATE, provide the exact local manifest explicitly:

```text
python -B tools/run_mif_1_0_reference.py replay path/to/state.json --manifest path/to/ruleset.json
```

The same implementation is exposed as a line-oriented interoperability adapter:

```text
python -B tools/mif_1_0_reference_adapter.py
```

Run two isolated instances to verify the adapter framing and comparator:

```text
python -B tools/compare_mif_1_0_adapters.py --config interop/adapters.reference-loopback.json --cases interop/cases/smoke-v1.json

python -B tools/compare_mif_1_0_adapters.py --config interop/adapters.reference-loopback.json --cases interop/cases/deterministic-v1.json
```

The adapter surface is defined by
[`../interop/adapter-protocol-v1.md`](../interop/adapter-protocol-v1.md). Two
processes running this same Python implementation are loopback evidence only;
they do not satisfy the independent-implementation release gate.

The implementation resolves no network resources. Unknown semantic extensions
fail closed. It intentionally implements only `mif-finite-rules-v3` and the
profiles frozen by the candidate contract.

A standalone decision identity with a non-null repetition root is transformed
only when its complete active repetition history is materialized and rebuilds
the supplied root; otherwise the runner returns `insufficient-transform-history`.
The machine-readable support boundary is declared in
`artifacts/mif-1.0/corpus/instances/mifcap.json` and is bound to the executable
corpus digest.

Passing this runner demonstrates one implementation's agreement with the
candidate executable corpus. It is not a published MIF Suite 1.0 target and is
not cross-implementation conformance. Sanmill and NMM_LLM now have independent
adapters, and the candidate-2 17-case smoke has zero differences across all
three implementations. The 55-case deterministic reference loopback also
passes; its current three-project run passes 44 cases and exposes 11 adapter
gaps, including the new legal-action projection. Those differences,
differential tests and the remaining release gates must be closed before a
suite manifest can be released.
