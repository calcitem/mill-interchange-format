# MIF Suite 1.0 release policy

This directory defines the publication layer around the frozen MIF 1.0 wire
contract. It does not change any MIF wire signature or profile.

Until the canonical `mif-suite-1.0` tag exists and the release manifest has a
valid GitHub artifact attestation, `mif-suite-1.0.json` is a release candidate
whose exact digest is available for final independent-adapter pinning. It is
not yet a released conformance target.

## Compatibility policy

`mif-1x-strict-v1` applies the lifecycle in MIF 1.0 clause 16.4 and the
governance policy in `GOVERNANCE.md`. Unknown semantic content fails closed.
Published suite bytes and identifiers are immutable. Metadata-only ruleset
changes may preserve semantic identity; gameplay changes require a new
ruleset version and semantic digest; reinterpretation of an existing wire
value requires 2.0.

## Transport media types

MIF Suite 1.0 deliberately reuses registered general-purpose media types. It
does not claim an unregistered MIF-specific IANA assignment.

| Format | Media type | Recommended extension |
|---|---|---|
| `MFEN/1.0` | `text/plain; charset=us-ascii` | `.mfen` |
| `MPK/1.0` | `text/plain; charset=us-ascii` | `.mpk` |
| `MIFPOS/1.0` | `application/json` | `.mifpos.json` |
| `MSTATE/1.0` | `application/json` | `.mstate.json` |
| `MRS/1.0` | `application/json` | `.mrs.json` |
| `MIFDIAG/1.0` | `application/json` | `.mifdiag.json` |
| `MIFCAP/1.0` | `application/json` | `.mifcap.json` |
| `MIFCONV/1.0` | `application/json` | `.mifconv.json` |
| `MIFINV/1.0` | `application/json` | `.mifinv.json` |
| `MIFTURN/1.0` | `application/json` | `.mifturn.json` |
| `MIFSUITE/1.0` | `application/json` | `.mifsuite.json` |

The embedded format signature remains authoritative. A media type or file
extension alone never supplies a missing ruleset identity or semantic digest.

## Signature policy

The signed subject is `release/mif-1.0-release-manifest.json`; the suite JSON
is separately attested. The canonical tag workflow uses `actions/attest@v4`
with GitHub OIDC and Sigstore. For this public repository, the attestation is
associated with the canonical repository and public transparency service.

Verify both subjects after release:

```text
gh attestation verify release/mif-1.0-release-manifest.json -R calcitem/mill-interchange-format
gh attestation verify mif-suite-1.0.json -R calcitem/mill-interchange-format
```

Verification must also confirm that the workflow identity is
`.github/workflows/release.yml` at `refs/tags/mif-suite-1.0`, that the tag has
not moved, and that the suite JCS SHA-256 equals `mif-suite-1.0.sha256` and the
release-manifest value. A signature proves publisher identity and integrity;
it does not expand the conformance evidence's tested domain.

## Release gates

The release manager shall complete these gates in order:

1. Apache-2.0, NOTICE and registry governance are present.
2. Every local wire, artifact, reference, interoperability and frozen-0.4
   check passes from a clean worktree.
3. The suite JCS bytes and digest are frozen without placeholders.
4. Sanmill and NMM_LLM pin the exact suite digest and ruleset semantic
   digests, rerun the required deterministic corpus and publish independent
   results with no unexplained byte/state/replay difference.
5. The release manifest binds those results and changes from
   `awaiting-adapter-suite-pin` to `ready-for-tag`.
6. An annotated `mif-suite-1.0` tag is pushed without moving any earlier tag.
7. The tag workflow validates the package, creates both attestations and
   publishes the immutable release assets.

If any gate fails, no tag or conformance claim is published. Fixes that alter
suite bytes require both adapters to pin and test the new digest again.

## Training gate

Engineering smoke runs may use the candidate suite when they record its exact
digest. Long-running or archival NMM_LLM training starts only after the signed
tag exists and NMM_LLM has pinned that released suite digest plus every
ruleset `semanticDigest` and its separate experiment configuration digest.
