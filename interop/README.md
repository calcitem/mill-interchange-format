# MIF 1.0 interoperability harness

This directory contains a non-normative test protocol for comparing independent
MIF 1.0 implementations. It does not add a MIF wire format and is not a
conformance target.

- `adapter-protocol-v1.md` defines the NDJSON process contract and operations.
- `schema/` validates adapter messages, harness configuration and case sources.
- `cases/smoke-v1.json` is the 17-case candidate-2 cross-process smoke set,
  including a portable MIFPOS case that exposes UTF-16 key-order and binary64
  JCS differences through `documentDigest`.
- `cases/deterministic-v1.json` is the 58-case candidate-4 M3 set. It maps
  every currently executable candidate corpus behavior into the adapter
  protocol and adds MFEN/MPK byte canonicalization, state and claim boundaries,
  replay identities, logical-turn and legal-action projections, and complete
  MSTATE/decision D4 matrices. It is engineering evidence, not a Suite corpus.
  Candidate-4 adds execute and legal-action boundaries for an active player
  whose reserve is empty while the opponent still has reserve material.
- `evidence/mif-1.0-candidate-4-m3.json` binds the completed M3 result to all
  three tested commits, the seven fixed inputs, Sanmill's raw 58/58 report and
  its companion evidence manifest.
- `differential-v1.md` defines the M4 PRNG, consensus selection, replay,
  first-difference, coverage, limit and deterministic report algorithms.
- `differential-candidate-4-v1.json` fixes seven scenarios, ten seeds and five
  mutation families. Its raw SHA-256 is
  `560ef369fde248bd96d3468a4336442db1d970ede04f488821509e69925fd48e`.
- `cases/differential-negative-v1.json` supplies the four protocol-level
  mutations; the zero-turn launch scenario supplies the resource-limit probe.
- `evidence/mif-1.0-candidate-4-m4-reference-baseline.json` is the byte-stable
  10/10 run and 5/5 mutation two-reference baseline.
- `evidence/mif-1.0-candidate-4-m4.json` binds both independent two-party
  reports, the final three-project report, all tested and evidence commits,
  and MIF's byte-identical independent reruns. It closes M4 only for the fixed
  Candidate-4 launch domain.
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

python -B tools/compare_mif_1_0_adapters.py \
  --config interop/adapters.reference-loopback.json \
  --cases interop/cases/deterministic-v1.json
```

## M4 differential launch

Reproduce the fixed two-reference baseline without creating or changing a file:

```text
python -B tools/run_mif_1_0_differential.py --config interop/adapters.reference-loopback.json --launch interop/differential-candidate-4-v1.json --expect-report interop/evidence/mif-1.0-candidate-4-m4-reference-baseline.json
```

For the three-project run, keep the launch file byte-identical, substitute the
three adapter commands in an `MIF-INTEROP-CONFIG/1` file and write a new report:

```text
python -B tools/run_mif_1_0_differential.py --config <three-project-config.json> --launch interop/differential-candidate-4-v1.json --report <three-project-report.json>
```

The report must then be bound to the exact MIF, Sanmill and NMM_LLM commits in a
separate evidence manifest. Do not edit the launch file or regenerate seeds in
a product repository.

The loopback result proves only that the process protocol and comparator are
deterministic. Use independent Sanmill and NMM_LLM entries for
cross-implementation evidence. The current candidate-2 smoke has zero
differences across the reference, Sanmill and NMM_LLM adapters, but it remains
candidate evidence rather than MIF Suite 1.0 conformance. The 58-case
candidate-4 set passes reference loopback and the three independent adapters.
The commit-bound [`M3 evidence record`](evidence/mif-1.0-candidate-4-m3.json)
fixes all three tested commits, seven input hashes, the 58/58 report and
Sanmill's companion binding. M3 is complete as Candidate evidence. The fixed
M4 launch now passes 10/10 seeded runs and 5/5 mutation families for each
independent product adapter and the three-project comparison. The commit-bound
[`M4 evidence record`](evidence/mif-1.0-candidate-4-m4.json) records two
byte-identical MIF reruns and closes the differential milestone with verdict
`exact-for-tested-domain`. No result in this directory claims Suite
conformance.

Adapter authors may use the specification, schemas, registries and corpus, but
must not import or copy gameplay implementation code from `reference/`.
