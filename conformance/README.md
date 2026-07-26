# MIF Community Working Draft 0.4 conformance corpus

This directory is the normative machine-readable corpus for
`MIF Community Working Draft 0.4`. It does not register the provisional
ruleset names used by its fixtures.

## Runner contract

A runner shall:

1. decode JSON files as UTF-8 I-JSON without discarding duplicate object
   member names;
2. resolve a relative path against the directory containing the JSON file in
   which that path occurs;
3. apply every vector relevant to the conformance classes and profiles it
   claims;
4. require the canonical output, parsed model, replay checkpoint, JCS bytes
   or digest stated by a positive vector;
5. reject a negative vector with its `category` and `code`, or with a
   documented implementation code mapped to both values; and
6. treat all array indices in mutation paths as zero-based.

A mutation path uses `.` between object member names and `[n]` for an array
element. Applying a mutation replaces the value at the complete path; it
does not merge objects.

For every positive MSTATE replay vector, `preOriginClaims` is the claim-audit
seed at the origin boundary and `claims` is the expected final audit. A runner
shall not derive one from the other.

## Files

- `mif-0.4.abnf` is the standalone RFC 5234/RFC 7405 grammar.
- `manifests/` contains self-contained private MRS fixtures, including
  claim-mode, stalemate `change-player` and `one-per-new-line` cases.
- `examples/` contains a complete MSTATE envelope.
- `vectors/mfen.json` covers MFEN parsing, canonicalization and rejection,
  including independent automatic-terminal inconsistency.
- `vectors/mpk.json` covers eligibility, key-profile normalization and the
  ban on non-semantic private MPK extensions.
- `vectors/mstate.json` covers replay, independent `preOriginClaims` seeds,
  pending removals, phase synchronization, dynamic removal capacity,
  origin automatic/claimable terminals, simultaneous minimum material and
  rejection.
- `vectors/json-jcs.json` covers I-JSON, JCS and manifest hashing.
- `vectors/transforms.json` gives all point and line permutations and
  MPK-associated line-ID transform examples.
- `vectors/implementation-mappings.json` pins the observed external
  implementation mappings.
- `index.json` identifies the exact raw bytes of the delivered corpus.

The SHA-256 values for ruleset references are hashes of RFC 8785 JCS manifest
bytes. The SHA-256 values in `index.json` are hashes of the raw delivered file
bytes. These digest domains are intentionally different.

## Fixture resolution

The fixture ID and version select a file name of the form:

```text
<id>@<version>.json
```

The runner shall compute the manifest's JCS SHA-256 and compare it with every
`rh` or envelope digest before semantic validation. It shall not retrieve a
missing fixture from a network.

## Corpus integrity

`index.json` lists every normative corpus file except itself, avoiding a
circular digest. A distributor may sign an outer package or index digest;
such a signature is outside this working draft.

Run `python tools/verify_conformance.py` from the repository root to verify
I-JSON parsing, the raw-file index, fixture JCS digests, ruleset references,
the two ABNF copies, transform bijections/topology, required 0.4 replay cases
and the Annex E mapping digest. Use `--update-index` only after intentional
corpus edits.
