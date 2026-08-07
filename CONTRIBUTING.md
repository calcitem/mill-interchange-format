# Contributing to MIF

Propose changes as a reviewable pull request or commit series against the
canonical repository. Describe the affected wire signatures, profiles,
registries and conformance classes, and add deterministic positive and
negative vectors when behaviour is involved.

Before submitting, run:

```text
python -B tools/verify_wire_contract.py
python -B tools/verify_mif_1_0_artifacts.py
python -B tools/run_mif_1_0_reference.py
python -B tools/verify_mif_1_0_interop.py
python -B tools/verify_corpus_integrity.py
```

Registry and release changes additionally follow `GOVERNANCE.md` and
`release/README.md`. Do not edit the frozen MIF/0.4 documents or corpus except
to verify their recorded bytes.

By intentionally submitting a contribution for inclusion, you agree that it
is provided under Apache License 2.0 unless you conspicuously mark it
"Not a Contribution". Confirm that you have the right to submit every added
or modified work.
