# MIF governance

This policy governs the canonical MIF repository at
<https://github.com/calcitem/mill-interchange-format> and every registry and
suite release published from it.

## Roles and authority

Repository administrators are the MIF maintainers and registry change
controllers. A maintainer may appoint a release manager for a specific
release. The release manager executes the mechanical release procedure but
cannot waive a normative gate.

The canonical Git history, not mirrors or downstream copies, is the source of
governance authority. A release is authentic only when its tag belongs to the
canonical repository and its release manifest passes the signature policy
documented in `release/README.md`.

## Decisions

Changes are proposed through a pull request or an equivalently reviewable
commit series. The proposal must state whether it changes wire semantics,
registries, tests, reference behaviour, publication metadata or governance.
At least one maintainer approves and merges a change. A maintainer with a
material conflict of interest discloses it before approval.

Normative wire meaning follows the 1.x/2.0 lifecycle in `mif-1.0.md`:

- editorial and publication-only changes must not change semantic identity;
- an additive value requires the profile, schema, vector and suite treatment
  prescribed by the frozen contract;
- an existing signature, token, canonical form or digest projection is never
  reinterpreted in place; and
- an incompatible semantic change requires MIF 2.0.

## Registry policy

Registry identifiers are first-come only after review, not by repository
upload or runtime discovery. Accepted unprefixed identifiers are immutable.
Their meaning may be clarified without changing valid behaviour, but cannot
be repurposed or deleted. A superseded entry remains readable and identifies
its successor.

An unprefixed registry addition requires:

1. a stable definition and named change controller;
2. closed syntax or a versioned extension profile;
3. positive, negative and canonicalization vectors;
4. fail-closed handling by consumers that do not implement it; and
5. inclusion in a later suite when conformance is claimed.

`x-` identifiers are private or provisional. They do not reserve an
unprefixed name and are never silently promoted. Registries are resolved from
explicitly pinned local resources; governance does not authorize automatic
network resolution.

## Suite releases

Published suite bytes and their digest are immutable. Corrections are issued
as a new suite identifier and tag; a tag is never moved or reused. A suite
release requires all gates in `release/README.md`, including two independent
adapter results bound to the exact suite digest. Evidence may establish only
the domain it actually tests and must not be relabelled as a broader proof.

The release manager records every specification, machine artifact, adapter,
ruleset digest, policy, license and evidence input in the release manifest.
GitHub's Sigstore-backed artifact attestation is the release signature
mechanism for MIF Suite 1.0.

## Security and errata

Parser, resource-exhaustion or signature-verification vulnerabilities should
be reported privately to the canonical repository maintainers when disclosure
would create avoidable risk. An erratum may describe an implementation defect
or ambiguous prose, but cannot change frozen bytes or wire meaning. A semantic
correction follows the lifecycle rules above.

## Licensing and contributions

The repository is licensed as a single work under Apache License 2.0. Unless
explicitly marked "Not a Contribution", an intentionally submitted
contribution is provided under the same terms as stated in section 5 of that
license. No governance decision grants rights to third-party material that a
contributor was not authorized to submit.
