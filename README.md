# Mill Interchange Format (MIF)

Community working draft for Mill-game interchange formats: positions
(**MFEN**), structural analysis keys (**MPK**), resumable game states
(**MSTATE**), and finite ruleset manifests (**MRS**).

## Current status

This repository publishes **MIF Community Working Draft 0.4**.

The `0.x` wire signatures are experimental. They may change incompatibly
after implementation and working-group review. This draft is **not** an ISO,
IEC, CEN, WMD or tournament-federation standard and shall not be cited as
one.

The immutable baselines are WD 0.2 at `4346b24` and WD 0.3 at
`3f1ffc30`. State-machine and corpus corrections now land in WD 0.4.

## Normative sources

| Artifact | Role |
|---|---|
| [`mif-0.4.md`](mif-0.4.md) | English normative working draft |
| [`conformance/`](conformance/) | Normative machine-readable corpus |
| [`conformance/mif-0.4.abnf`](conformance/mif-0.4.abnf) | Standalone ABNF |
| [`docs/zh-CN/mif-0.4-guide.md`](docs/zh-CN/mif-0.4-guide.md) | Chinese reader’s guide (informative) |

If the English draft and the Chinese guide disagree, the English draft and
the conformance corpus prevail.

## How to cite

Cite a specific git commit or release tag, for example:

```text
Mill Interchange Format, Community Working Draft 0.4,
https://github.com/calcitem/mill-interchange-format
commit <full-sha>
```

Do not present a Community Working Draft as a ratified international
standard.

## Conformance

See [`conformance/README.md`](conformance/README.md) for the runner contract.
`conformance/index.json` lists raw-file SHA-256 digests for the delivered
corpus (excluding itself).
Run `python tools/verify_conformance.py` to check the draft/corpus links,
canonical manifest digests, ABNF copies, transforms and raw-file index.

## License

License terms are not yet declared in this repository. Until a LICENSE file
is added, default copyright rules apply; ask the maintainers before
redistributing.
