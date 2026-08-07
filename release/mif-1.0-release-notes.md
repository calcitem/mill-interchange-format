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

Verify the downloaded assets with:

```text
gh attestation verify mif-suite-1.0.json -R calcitem/mill-interchange-format
gh attestation verify mif-1.0-release-manifest.json -R calcitem/mill-interchange-format
```

Then recompute the suite digest over RFC 8785 JCS bytes and compare it with
`mif-suite-1.0.sha256`.
