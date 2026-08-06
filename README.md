# Mill Interchange Format (MIF)

Community working draft for Mill-game interchange formats: positions
(**MFEN**), structural analysis keys (**MPK**), resumable game states
(**MSTATE**), and finite ruleset manifests (**MRS**).

## Current status

This repository contains the byte-frozen historical **MIF Community Working
Draft 0.4** and the frozen **MIF 1.0 Candidate Wire Contract**.

The 1.0 wire meanings are frozen, but MIF Suite 1.0 is not yet a conformance
target. Standalone ABNF, JSON Schemas, registries, a 1.0 conformance corpus,
an executable reference runner and two agreeing independent adapters still
have to be delivered and bound by `mif-suite-1.0.json`. Neither edition is an
ISO, IEC, CEN, WMD or tournament-federation standard and shall not be cited
as one.

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
ABNF. They do not publish the next-stage machine artifacts. Until the release
gates and `mif-suite-1.0.json` are complete, this repository has no MIF
Suite 1.0 conformance target.

Raw-file identities of the frozen bilingual contracts are:

```text
mif-1.0.md sha256:330e65145ceb26fe582e58b89405d87bd73e8be200b476aef82c0ee27731d995
docs/zh-CN/mif-1.0.md sha256:9cc06abb57425e2bc2e26432b6da53abe503e9b5415ea0b4f854f19f68722cc1
```

These hashes identify documentation bytes, not a suite or conformance result.

NMM_LLM and Sanmill target MIF Suite 1.0 directly; neither needs to implement
MIF/0.4 first. The only continuing 0.4 work is explicit 0.4-to-1.0 conversion
and rejection coverage. Ambiguous 0.4 data shall never be silently upgraded.

## Normative sources

| Artifact | Role |
|---|---|
| [`mif-1.0.md`](mif-1.0.md) | Frozen normative English Candidate Wire Contract |
| [`docs/zh-CN/mif-1.0.md`](docs/zh-CN/mif-1.0.md) | Complete aligned Chinese translation |
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
