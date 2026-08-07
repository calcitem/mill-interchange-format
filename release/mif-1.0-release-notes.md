# MIF Suite 1.0

This release publishes the first immutable MIF 1.0 suite manifest for the
frozen MIF 1.0 wire contract.

- Suite JCS SHA-256:
  `sha256:81a5feabc281bfc4f830addabc2c6846d1f191bbbcf04e548f04b35dd358ae6f`
- Normative wire commit:
  `7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978`
- Compatibility policy: `mif-1x-strict-v1`
- License: Apache-2.0

The signed release manifest binds the specifications, registries, schemas,
ABNF, corpora, runners, independent adapters and suite-bound evidence. Claims
remain limited to the conformance classes and tested domain recorded there.

Independent Suite-bound implementations:

- NMM_LLM implementation `a7e7dbd5461cc2d8d8c0a09317d6091598202214`,
  evidence publication `b599e0d45a660a020b45860e60c9409b503c454d`;
- Sanmill implementation `7e86de7e8156a7d7f46a6a6179a8878051699505`,
  evidence publication `57f41c1d0dae90e6f614c6aa9b2c177e9df4ffc0`.

The final MIF-controlled three-adapter rerun passed 58/58 deterministic cases,
10/10 seeded trajectories and 5/5 mutation families with zero unexplained
differences. Both reports were reproduced byte-for-byte. The aggregate final
evidence SHA-256 is
`sha256:2c23983281858386bc66e3adfce52f365c712d9e63a31c53f6a68bd6b2de08e1`.
The verdict is `exact-for-tested-domain` for `identity`, `key`, `position`,
`replay`, `ruleset` and `transform`; it is not a `full` or conversion claim.

Verify the downloaded assets with:

```text
gh attestation verify mif-suite-1.0.json -R calcitem/mill-interchange-format
gh attestation verify mif-1.0-release-manifest.json -R calcitem/mill-interchange-format
```

Then recompute the suite digest over RFC 8785 JCS bytes and compare it with
`mif-suite-1.0.sha256`.
