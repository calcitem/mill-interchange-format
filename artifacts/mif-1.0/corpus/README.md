# MIF 1.0 candidate conformance corpus

This corpus supplies deterministic structural and identity vectors for the
frozen MIF 1.0 Candidate Wire Contract.

- `fixtures/` contains complete reusable ruleset documents.
- `instances/` contains complete JSON wire or derived-identity objects.
- `vectors/schema-cases.json` maps instances to entry schemas and defines
  isolated negative mutations using JSON Pointer.
- `vectors/jcs-rfc8785.json` covers the 24 finite RFC 8785 Appendix B
  binary64 samples, UTF-16 member ordering, MIF I-JSON rejection and
  annotation-only document identity.
- `executable/reference-cases.json` binds replay, boundary, claim, transform,
  turn-projection and historical migration cases to exact resources and
  expected results.
- the remaining vector groups cover text formats, digest domains, state
  identities, transition boundaries, transforms and 0.4 migration policy.

The artifact-integrity checker validates every positive and negative Schema
case, recomputes the deterministic JCS/SHA-256 and sparse-Merkle expectations,
checks executable-resource bindings and verifies the raw-file index. It does
not execute the complete gameplay state machine or MSTATE replay. Fields named
`runnerRequired` identify vectors whose assertions require execution rather
than Schema validation alone.

Run those executable assertions with:

```text
python -B tools/run_mif_1_0_reference.py
```

The origin-stabilization MIFTURN instance is bound to a real MSTATE replay and
its exact `resumptionDigest`. The runner also records two contradictory frozen
0.4 checkpoints as source rejections, so they cannot be silently upgraded.

`instances/mifcap.json` names the candidate-2 Python implementation and binds
its tested classes to the raw SHA-256 of `executable/reference-cases.json`. It
claims no suite, general conversion, MPK support, invariance or resource limit.

Passing these vectors is single-implementation evidence. No file in this
directory is a published MIF Suite 1.0 conformance claim.
