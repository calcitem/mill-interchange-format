# MIF 1.0 candidate machine artifacts

This directory contains machine-readable artifacts generated from the frozen
MIF 1.0 Candidate Wire Contract:

- `abnf/mif-1.0.abnf`: standalone MFEN/1.0 and MPK/1.0 grammar;
- `schema/`: JSON Schema Draft 2020-12 entry points and shared definitions;
- `registry/`: candidate format, profile, topology, token and diagnostic
  registries; and
- `corpus/`: deterministic structural, identity and executable vectors.

These artifacts are candidates for the future MIF Suite 1.0 release. Their
presence, including the candidate executable corpus, does not establish
independent implementation agreement, registry governance or publisher trust.
No `MIFSUITE/1.0` object is published here.

`index.json` records raw-file SHA-256 for every delivered file below this
directory except itself and binds the English and Chinese wire-contract
hashes. The checker requires Python 3 with `jsonschema` 4.x and its
`referencing` dependency. Run:

```text
python tools/verify_mif_1_0_artifacts.py
```

That command checks artifact integrity, JSON/ABNF linkage, registry coverage,
Schema references and deterministic precomputed vectors. Execute the distinct
candidate reference corpus with:

```text
python -B tools/run_mif_1_0_reference.py
```

The latter executes finite-rules transitions, full MSTATE replay, state
identities, transforms and logical-turn projection. It remains a single Python
implementation and therefore is not a MIF Suite conformance claim.

The byte-frozen MIF/0.4 specification and `conformance/` corpus remain
separate migration inputs and are not modified by these artifacts.
