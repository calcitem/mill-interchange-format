# Mill Interchange Format (MIF)

Community working draft for Mill-game interchange formats: positions
(**MFEN**), structural analysis keys (**MPK**), resumable game states
(**MSTATE**), and finite ruleset manifests (**MRS**).

## Current status

This repository contains the byte-frozen historical **MIF Community Working
Draft 0.4** and the frozen **MIF 1.0 Candidate Wire Contract**.

The 1.0 wire meanings are frozen, but MIF Suite 1.0 is not yet a conformance
target. Candidate standalone ABNF, JSON Schemas, registries and an initial
structural, identity and executable corpus are available under
[`artifacts/mif-1.0/`](artifacts/mif-1.0/). A candidate Python reference
runner is available under [`reference/`](reference/). The non-normative
three-project adapter protocol, smoke cases and comparator are under
[`interop/`](interop/), with the collaboration plan in
[`docs/zh-CN/mif-1.0-three-project-interop-plan.md`](docs/zh-CN/mif-1.0-three-project-interop-plan.md).
Two agreeing independent product adapters and release governance still have to
be delivered and bound by `mif-suite-1.0.json`. Neither edition is an ISO, IEC,
CEN, WMD or tournament-federation standard and shall not be cited as one.

The immutable baselines are WD 0.2 at `4346b24` and WD 0.3 at
`3f1ffc30`. MIF/0.4 at
`9ecc134853628dc29d3037727a566702505fda1f` is also frozen: it is a
historical working draft and migration-test input, and its specification text
and corpus receive no further protocol corrections.

## MIF 1.0 Candidate Wire Contract

The Sanmill maintainer review of the `9ecc134` baseline is accepted with
refinements. Its wire decisions are implemented by the standalone bilingual
contracts:

- [`mif-1.0.md`](mif-1.0.md), the normative English Candidate Wire Contract;
- [`docs/zh-CN/mif-1.0.md`](docs/zh-CN/mif-1.0.md), its token- and
  section-aligned Chinese translation.

The design basis is retained for decision history:

- [`mif-1.0-design.md`](mif-1.0-design.md), the English design baseline; and
- [`docs/zh-CN/mif-1.0-design.md`](docs/zh-CN/mif-1.0-design.md), its Chinese
  translation.

The contracts freeze wire syntax, closed JSON members, algorithms and inline
ABNF. The candidate machine artifacts are derived from that contract and are
integrity-checked. The separate candidate reference runner executes gameplay,
replay, identities, MPK canonicalization, transforms, logical-turn projection
and the non-normative legal-action comparison projection, but one implementation
does not publish a suite. Until the release gates and
`mif-suite-1.0.json` are complete, this repository has no MIF Suite 1.0
conformance target.

The candidate-2 reference/harness baseline uses one RFC 8785 implementation for
all digest and canonical NDJSON paths and adds executable UTF-16 ordering,
binary64 and annotation-identity vectors. This is a tooling/artifact correction:
the frozen wire contract and its bilingual raw-file identities are unchanged.

The candidate-3 M3 engineering baseline adds reference MPK canonicalization,
the 55-case deterministic comparison set and the non-normative
`legal-actions-v1` adapter projection. It changes harness and artifact-index
identities, not frozen MIF wire semantics.

The candidate-4 reference/harness baseline synchronizes an ongoing origin's
phase and action from the active player's reserve before stable-boundary
processing. It adds asymmetric-reserve origin regression coverage and expands
the deterministic comparison set to 58 cases. This corrects reference,
corpus and artifact-index identities; the frozen wire semantics and bilingual
contract hashes remain unchanged.

Raw-file identities of the frozen bilingual contracts are:

```text
mif-1.0.md sha256:330e65145ceb26fe582e58b89405d87bd73e8be200b476aef82c0ee27731d995
docs/zh-CN/mif-1.0.md sha256:9cc06abb57425e2bc2e26432b6da53abe503e9b5415ea0b4f854f19f68722cc1
```

These hashes identify documentation bytes, not a suite or conformance result.

NMM_LLM and Sanmill target MIF Suite 1.0 directly; neither needs to implement
MIF/0.4 first. The only continuing 0.4 work is explicit 0.4-to-1.0 conversion
and rejection coverage. Ambiguous 0.4 data shall never be silently upgraded.

## MIF 1.0 candidate machine artifacts

[`artifacts/mif-1.0/`](artifacts/mif-1.0/) contains the generated standalone
ABNF, JSON Schema Draft 2020-12 entry points, closed candidate registries and
the first positive/negative wire corpus. Its `index.json` binds every
delivered artifact to the frozen bilingual contract hashes.

Run:

```text
python tools/verify_mif_1_0_artifacts.py
```

This check proves artifact, Schema, registry and deterministic vector integrity
only. Run the distinct executable candidate corpus with:

```text
python -B tools/run_mif_1_0_reference.py
```

The runner covers finite-rules transitions, MSTATE replay, claim and repetition
lifecycles, derived identities, full-state transforms, invariance gating,
logical-turn projection and explicit 0.4 migration/rejection cases. Its passing
result is evidence from one implementation only, not cross-implementation MIF
conformance.

## Three-project interoperability

Sanmill and NMM_LLM implement independent adapters against
[`interop/adapter-protocol-v1.md`](interop/adapter-protocol-v1.md). The MIF
repository supplies the protocol Schema, deterministic case source and
comparison process; it does not supply either product's gameplay logic.

Verify the fixed collaboration package and its two-process reference loopback:

```text
python -B tools/verify_mif_1_0_interop.py
```

Run the comparator directly when substituting product adapter commands:

```text
python -B tools/compare_mif_1_0_adapters.py --config interop/adapters.reference-loopback.json --cases interop/cases/smoke-v1.json

python -B tools/compare_mif_1_0_adapters.py --config interop/adapters.reference-loopback.json --cases interop/cases/deterministic-v1.json
```

A passing loopback proves process framing, Schema validation, case expansion
and comparison behavior only. Replace the two command arrays in the adapter
configuration with the Sanmill and NMM_LLM executables for independent
byte-, state- and replay-level evidence. It is still not a published-suite
conformance result. The 58-case candidate-4 deterministic reference loopback
passes. Sanmill and NMM_LLM subsequently published their candidate-4 pins and
commit-bound evidence; the resulting
[`M3 evidence record`](interop/evidence/mif-1.0-candidate-4-m3.json) closes the
deterministic milestone with 58/58 and advances collaboration to M4
differential testing. This remains Candidate evidence, not MIF Suite 1.0
conformance.

M4 now has a fixed, versioned differential launch package. Its
[`harness contract`](interop/differential-v1.md),
[`launch document`](interop/differential-candidate-4-v1.json) and
[`two-reference baseline`](interop/evidence/mif-1.0-candidate-4-m4-reference-baseline.json)
define SplitMix64 test vectors, ten seeded trajectories, stable-boundary
execute/replay comparison, five negative mutation families and explicit
process limits. Reproduce the baseline without writing a report:

```text
python -B tools/run_mif_1_0_differential.py --config interop/adapters.reference-loopback.json --launch interop/differential-candidate-4-v1.json --expect-report interop/evidence/mif-1.0-candidate-4-m4-reference-baseline.json
```

Sanmill and NMM_LLM should use the same launch file with a three-project
adapter config and `--report <path>`, then bind the raw report to all three
tested commits. A passing reference baseline validates the launch machinery;
it is not independent implementation evidence.

## Sources and implementation artifacts

| Artifact | Role |
|---|---|
| [`mif-1.0.md`](mif-1.0.md) | Frozen normative English Candidate Wire Contract |
| [`docs/zh-CN/mif-1.0.md`](docs/zh-CN/mif-1.0.md) | Complete aligned Chinese translation |
| [`docs/zh-CN/mif-1.0-three-project-interop-plan.md`](docs/zh-CN/mif-1.0-three-project-interop-plan.md) | Sanmill, NMM_LLM and MIF collaboration plan |
| [`artifacts/mif-1.0/`](artifacts/mif-1.0/) | Derived candidate machine artifacts; not a published suite |
| [`reference/`](reference/) | Candidate Python reference runner; single-implementation evidence only |
| [`interop/`](interop/) | Non-normative adapter protocol, Schema, cases and loopback configuration |
| [`mif-0.4.md`](mif-0.4.md) | Frozen English historical working draft |
| [`conformance/`](conformance/) | Frozen 0.4 corpus and migration-test input |
| [`conformance/mif-0.4.abnf`](conformance/mif-0.4.abnf) | Standalone ABNF |
| [`docs/zh-CN/mif-0.4.md`](docs/zh-CN/mif-0.4.md) | Complete Chinese translation (informative) |
| [`docs/zh-CN/mif-0.4-guide.md`](docs/zh-CN/mif-0.4-guide.md) | Chinese reader’s guide (informative) |

For 1.0 wire meaning, the English Candidate Wire Contract prevails over its
translation. For frozen 0.4 input, the English 0.4 draft and its conformance
corpus prevail.

## How to cite

Cite a specific git commit or release tag, for example:

```text
Mill Interchange Format, Community Working Draft 0.4,
https://github.com/calcitem/mill-interchange-format
commit <full-sha>
```

Do not present a Community Working Draft as a ratified international
standard.

## Frozen 0.4 corpus integrity

See [`conformance/README.md`](conformance/README.md) for the frozen 0.4
corpus contract.
`conformance/index.json` lists raw-file SHA-256 digests for the delivered
corpus (excluding itself).
Run `python tools/verify_corpus_integrity.py` to check the draft/corpus links,
canonical manifest digests, ABNF copies, transforms and raw-file index.

This check establishes corpus integrity only. It does not generally execute
the rules, transitions, transforms or complete MSTATE replays and is not an
implementation-conformance result. `tools/verify_conformance.py` remains as
a compatibility entry point with the same limited meaning.

## License

License terms are not yet declared in this repository. Until a LICENSE file
is added, default copyright rules apply; ask the maintainers before
redistributing.
